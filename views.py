import logging
from dataclasses import dataclass, asdict
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import BadRequest
from django.shortcuts import redirect
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from portal.generic.baseviews import CView
from portal.utils.general import get_site_domain
from portal.vidispine.iexception import NotFoundError
from portal.vidispine.iitem import ItemHelper
from .lta_types import LaunchTemplate, Data, Endpoints, Endpoint, Settings
from .transform import transform_items_to_lta_assets
from .utils import clean_nones

log = logging.getLogger(__name__)


# TODO: Move this to db
@dataclass
class PluginSettings(object):
    launch_url: str
    license_key: str
    force_site_domain: bool


plugin_settings = PluginSettings(
    license_key="73E3F4EDC1CB113CA1FFA9B0EB348EFAU6A491CA3DA6078640802A68E16B2421C",
    force_site_domain=True,
    launch_url="https://apps.accurate.video/launch/"
)


class OpenApplicationView(CView):
    def get(self, request):
        application = request.query_params.get("application", "")
        item_ids = [item_id for item_id in request.query_params.get("item_ids", "").split(",") if item_id]

        if not application or len(item_ids) < 1:
            raise BadRequest("You need to specify an application and at least one item id.")

        launch_template_query_params = {
            "item_ids": ",".join(item_ids),
        }
        query_params = {
            "launchTemplate": get_site_domain() + reverse(
                "av_lta:get_launch_template"
            ) + f"?{urlencode(launch_template_query_params)}",
            "authMethod": "token",
            "authTokenPrefix": "Basic",
            "token": "YWRtaW46YWRtaW4K",
            "manual": "true"
        }
        return redirect(f"{plugin_settings.launch_url}{application}/?{urlencode(query_params)}")


class LaunchTemplateView(CView):
    renderer_classes = (JSONRenderer,)

    def __get_content(self):
        content = {
            "content": ["uri", "shape", "metadata", "thumbnail"],
            "include": ["type", "extradata"],
            "noauth-url": "true"
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
            items = item_helper.getItems(item_ids=item_ids, content=self.__get_content())
            launch_template = LaunchTemplate(
                data=Data(
                    assets=transform_items_to_lta_assets(
                        items=items,
                        force_site_domain=plugin_settings.force_site_domain
                    )),
                endpoints=Endpoints(
                    publish=Endpoint(
                        download=True
                    )
                ),
                settings=Settings(
                    licenseKey=plugin_settings.license_key
                )
            )
        except NotFoundError:
            raise NotFound()

        return Response(data=clean_nones(asdict(launch_template)))
