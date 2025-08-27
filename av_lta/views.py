import json
import logging
import re
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.parse import urlparse

import requests
import VidiRest.schemas.xmlSchema as VSXMLSchema
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import BadRequest
from django.http import HttpResponse
from django.http import QueryDict
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic.edit import FormView
from portal.generic.baseviews import CView
from portal.utils.general import get_site_domain
from portal.vidispine.iexception import NotFoundError
from portal.vidispine.iitem import ItemHelper
from requests import HTTPError
from rest_framework.exceptions import NotFound
from rest_framework.parsers import BaseParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from ...externals.VidiRest.objects.item import VSItem  # type: ignore
from ...externals.VidiRest.objects.shape import VSBinaryComponent  # type: ignore
from ...externals.VidiRest.objects.shape import VSShape  # type: ignore
from ...externals.VidiRest.objects.shape import VSSubtitleComponent  # type: ignore
from .forms import SettingsForm
from .lta_types import Data
from .lta_types import Endpoint
from .lta_types import Endpoints
from .lta_types import HttpEndpoint
from .lta_types import LaunchTemplate
from .lta_types import Settings
from .lta_types import TimelineSettings
from .lta_types import WaveformSettingsVidispine
from .lta_types import WaveformsSettings
from .settings import plugin_settings
from .transform import get_filename
from .transform import transform_items_to_lta_assets
from .utils import clean_nones
from .vs_helpers import import_shape_raw

log = logging.getLogger(__name__)


class OpenApplicationView(CView):
    def get(self, request):
        application = request.query_params.get("application", "")
        item_ids = [item_id for item_id in request.query_params.get("item_ids", "").split(",") if item_id]

        if not application or len(item_ids) < 1:
            raise BadRequest("You need to specify an application and at least one item id.")

        launch_template_query_params = {
            "item_ids": ",".join(item_ids),
        }
        launch_template_url = reverse("av_lta:get_launch_template") + f"?{urlencode(launch_template_query_params)}"
        if plugin_settings.AV_LTA_FORCE_FULL_DOMAIN:
            launch_template_url = f"{get_site_domain()}{launch_template_url}"
        query_params = {
            "launchTemplate": launch_template_url,
        }
        if settings.DEBUG:
            query_params["manual"] = "true"
        launch_url = f"{reverse('av_lta:av_apps')}launch/"
        return redirect(f"{launch_url}{application}/?{urlencode(query_params)}")


class LaunchTemplateView(CView):
    renderer_classes = (JSONRenderer,)

    @staticmethod
    def __get_content():
        content = {
            "content": ["uri", "shape", "metadata", "thumbnail", "merged-access"],
            "include": ["type", "extradata"],
            "noauth-url": "true",
        }
        if settings.VIDISPINE_STORAGE_METHOD_TYPE:
            content["methodType"] = settings.VIDISPINE_STORAGE_METHOD_TYPE
        else:
            content["methodType"] = "AUTO"
        return content

    def get(self, request):
        item_ids = [item_id for item_id in request.query_params.get("item_ids", "").split(",") if item_id]
        if len(item_ids) < 1:
            raise NotFound()

        try:
            item_helper = ItemHelper(runas=request.user)
            items: list[VSItem] = item_helper.getItems(item_ids=item_ids, content=self.__get_content())
            publish_url = f"{reverse('av_lta:publish')}?itemIds={','.join(item_ids)}"
            force_full_domain = plugin_settings.AV_LTA_FORCE_FULL_DOMAIN
            if force_full_domain:
                publish_url = f"{get_site_domain()}{publish_url}"
            lta_settings: list[Settings] = [
                Settings(
                    licenseKey=settings.AP_LICENSE_KEY,
                    timeline=TimelineSettings(
                        waveforms=WaveformsSettings(
                            active="vidispine",
                            vidispine=WaveformSettingsVidispine(apiBaseUrl="/AVAPI/", sampleMin=-60, sampleMax=0),
                            requestDebounceTimeMs=250,
                        )
                    ),
                ),
            ]
            try:
                extra_settings = json.loads(plugin_settings.AV_LTA_EXTRA_SETTINGS)
                lta_settings.append(extra_settings)
            except ValueError:
                log.debug("Failed to parse extra lta settings from plugin settings, invalid JSON")
            launch_template = LaunchTemplate(
                data=Data(assets=transform_items_to_lta_assets(items=items, force_full_domain=force_full_domain)),
                endpoints=Endpoints(publish=Endpoint(http=HttpEndpoint(url=publish_url, method="POST"))),
                settings=lta_settings,
            )
        except NotFoundError:
            raise NotFound()

        return Response(data=clean_nones(asdict(launch_template)))


class TTMLPlainTextParser(BaseParser):
    media_type = "application/ttml+xml"

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read()


class SubtitlePublishView(CView):
    parser_classes = (TTMLPlainTextParser,)
    renderer_classes = (JSONRenderer,)

    def post(self, request):
        try:
            log.info("Publishing ttml")
            log.info(request.query_params)
            file_id: str = request.query_params.get("fileId", "")
            parts = file_id.split("_")
            shape_id = parts[0] if len(parts) > 0 else None
            component_id = parts[1] if len(parts) > 1 else None
            item_ids = list(filter(None, request.query_params.get("itemIds", "").split(",")))
            if len(item_ids) < 1:
                raise BadRequest("No items could be found")
            raw_ttml_contents = request.data
            item_helper = ItemHelper(runas=request.user)
            items: list[VSItem] = item_helper.getItems(
                item_ids=item_ids,
                content={
                    "content": ["shape"],
                },
            )
            item_and_shape_or_none = self.__find_item_and_shape(items=items, shape_id=shape_id)
            if item_and_shape_or_none is None:
                raise NotFound("Item and shape could not be found")
            item, shape = item_and_shape_or_none
            component = self.__find_subtitle_component(
                shape=shape, component_id=component_id
            ) or self.__find_binary_component(shape=shape, component_id=component_id)

            # Add more export variants here
            self.export_to_new_shape_on_item(
                item=item,
                shape=shape,
                component=component,
                data=raw_ttml_contents,
                item_helper=item_helper,
                runas=request.user,
            )

            return Response()
        except HTTPError as e:
            log.exception("Failed to publish ttml")
            vs_error = e.response.json()
            return Response(status=e.response.status_code, data=vs_error, exception=True)
        except NotFound as e:
            raise e
        except BadRequest as e:
            raise e
        except Exception:
            log.exception("Failed to publish ttml")
            raise BadRequest("Failed to publish ttml")

    def export_to_new_shape_on_item(
        self,
        item: VSItem,
        shape: VSShape,
        component: VSSubtitleComponent | VSBinaryComponent,
        data: str,
        item_helper: ItemHelper,
        runas: str,
    ):
        item_id = item.json_object["id"]
        filename = get_filename(shape.getAllFiles()) if component is None else get_filename(component.getFiles())
        self._create_shape_if_needed(shape_tag=plugin_settings.AV_LTA_PUBLISH_SHAPE_TAG, item_helper=item_helper)
        import_shape_raw(
            item_id=item_id, data=data, filename=filename, tag=plugin_settings.AV_LTA_PUBLISH_SHAPE_TAG, runas=runas
        )

    @staticmethod
    def _create_shape_if_needed(shape_tag: str, item_helper: ItemHelper) -> bool:
        try:
            item_helper.getShapeTag(shape_tag)
            return False
        except NotFoundError:
            pass
        item_helper.createOrModifyShapeTag(shape_tag, VSXMLSchema.TranscodePresetDocument(format=""))
        return True

    @staticmethod
    def __find_item_and_shape(items: list[VSItem], shape_id: str) -> tuple[VSItem, VSShape] | None:
        for item in items:
            shape: VSShape | None = item.getShapeById(shape_id=shape_id)
            if shape is not None:
                return item, shape
        return None

    @staticmethod
    def __find_subtitle_component(shape: VSShape, component_id: str) -> VSSubtitleComponent | None:
        for component in shape.getSubtitleComponents():
            if component_id == component.getId():
                return component
        return None

    @staticmethod
    def __find_binary_component(shape: VSShape, component_id: str) -> VSBinaryComponent | None:
        for component in shape.getBinaryComponents():
            if component_id == component.getId():
                return component
        return None


class ProxyLTAView(View):
    def get(self, request, path, requests_args=None):
        url = plugin_settings.AV_LTA_APPS_URL
        requests_args = (requests_args or {}).copy()
        headers = self.get_headers(request.META)
        params = request.GET.copy()

        if "headers" not in requests_args:
            requests_args["headers"] = {}
        if "data" not in requests_args:
            requests_args["data"] = request.body
        if "params" not in requests_args:
            requests_args["params"] = QueryDict("", mutable=True)

        headers.update(requests_args["headers"])
        params.update(requests_args["params"])

        for key in list(headers.keys()):
            if key.lower() == "content-length":
                del headers[key]

        requests_args["headers"] = headers
        requests_args["params"] = params

        if self.has_file_extension(path):
            # We only want to append the path for CSS, JS, and Fonts etc.
            # For other paths we just want to route them to the index page and let
            # the frontend router handle them.
            url = url + path
        response = requests.request(request.method, url, **requests_args)

        proxy_response = HttpResponse(response.content, status=response.status_code)

        if "text/html" in response.headers.get("content-type", ""):
            # We need to rewrite the base tag as we're not serving from root /
            soup = BeautifulSoup(response.content, "html.parser")
            base_tag = soup.find("head").find("base")
            base_tag.attrs.update(href=reverse("av_lta:av_apps"))
            proxy_response.content = str(soup)

        excluded_headers = {
            # Hop-by-hop headers
            # ------------------
            # Certain response headers should NOT be just tunneled through.  These
            # are they.  For more info, see:
            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.5.1
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "upgrade",
            # Although content-encoding is not listed among the hop-by-hop headers,
            # it can cause trouble as well. Just let the server set the value as
            # it should be.
            "content-encoding",
            # Since the remote server may or may not have sent the content in the
            # same encoding as Django will, let Django worry about what the length
            # should be.
            "content-length",
        }
        for key, value in response.headers.items():
            if key.lower() in excluded_headers:
                continue
            elif key.lower() == "location":
                # If the location is relative at all, we want it to be absolute to
                # the upstream server.
                proxy_response[key] = self.make_absolute_location(response.url, value)
            else:
                proxy_response[key] = value

        return proxy_response

    @staticmethod
    def has_file_extension(url):
        path = Path(urlparse(url).path)
        if path.suffix:
            return True
        return False

    @staticmethod
    def make_absolute_location(base_url, location):
        """
        Convert a location header into an absolute URL.
        """
        absolute_pattern = re.compile(r"^[a-zA-Z]+://.*$")
        if absolute_pattern.match(location):
            return location

        parsed_url = urlparse(base_url)

        if location.startswith("//"):
            # scheme relative
            return parsed_url.scheme + ":" + location

        elif location.startswith("/"):
            # host relative
            return parsed_url.scheme + "://" + parsed_url.netloc + location

        else:
            # path relative
            return parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path.rsplit("/", 1)[0] + "/" + location

    @staticmethod
    def get_headers(environ):
        """
        Retrieve the HTTP headers from a WSGI environment dictionary.  See
        https://docs.djangoproject.com/en/dev/ref/request-response/#django.http.HttpRequest.META
        """
        headers = {}
        for key, value in environ.items():
            # Sometimes, things don't like when you send the requesting host through.
            if key.startswith("HTTP_") and key != "HTTP_HOST":
                headers[key[5:].replace("_", "-")] = value
            elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                headers[key.replace("_", "-")] = value

        return headers


class AdminIndexView(FormView):
    template_name = "av_lta/admin_index.html"
    form_class = SettingsForm

    def get_initial(self):
        return {
            key: field.clean(getattr(plugin_settings, key)) for (key, field) in self.form_class.declared_fields.items()
        }

    def form_valid(self, form):
        for key, value in form.cleaned_data.items():
            setattr(plugin_settings, key, value)
        messages.success(self.request, _("Settings saved"))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("av_lta:plugin_admin_index")
