import logging
from dataclasses import dataclass, asdict
from urllib.parse import urlencode

import VidiRest.schemas.xmlSchema as VSXMLSchema
from django.conf import settings
from django.core.exceptions import BadRequest
from django.shortcuts import redirect
from django.urls import reverse
from rest_framework.exceptions import NotFound
from rest_framework.parsers import BaseParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from portal.generic.baseviews import CView
from portal.utils.general import get_site_domain
from portal.vidispine.iexception import NotFoundError
from portal.vidispine.iitem import ItemHelper
from .lta_types import LaunchTemplate, Data, Endpoints, Endpoint, Settings, HttpEndpoint
from .transform import transform_items_to_lta_assets, get_filename
from .utils import clean_nones
from .vs_helpers import import_shape_raw
from ...externals.VidiRest.objects.item import VSItem
from ...externals.VidiRest.objects.shape import VSShape, VSSubtitleComponent, VSBinaryComponent

log = logging.getLogger(__name__)


# TODO: Move this to db
@dataclass
class PluginSettings(object):
    launch_url: str
    license_key: str
    force_site_domain: bool
    shape_tag: str


plugin_settings = PluginSettings(
    license_key="73E3F4EDC1CB113CA1FFA9B0EB348EFAU6A491CA3DA6078640802A68E16B2421C",
    force_site_domain=True,
    shape_tag="av-subtitle",
    launch_url="https://av.localhost/launch/"
    # launch_url="https://apps.accurate.video/launch/"
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

    @staticmethod
    def __get_content():
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
                        http=HttpEndpoint(
                            url=f"{get_site_domain()}{reverse('av_lta:publish')}?itemIds={','.join(item_ids)}",
                            method="POST"
                        )
                    )
                ),
                settings=Settings(
                    licenseKey=plugin_settings.license_key
                )
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
            file_id: str = request.query_params.get("fileId", "")
            shape_id, component_id = file_id.split("_")
            item_ids = request.query_params.get("itemIds").split(",")
            raw_ttml_contents = request.data
            item_helper = ItemHelper(runas=request.user)
            items: list[VSItem] = item_helper.getItems(item_ids=item_ids, content={
                "content": ["shape"],
            })
            item_and_shape_or_none = self.__find_item_and_shape(items=items, shape_id=shape_id)
            if item_and_shape_or_none is None:
                raise NotFound("Item and shape could not be found")
            item, shape = item_and_shape_or_none
            component = (self.__find_subtitle_component(shape=shape, component_id=component_id)
                         or self.__find_binary_component(shape=shape, component_id=component_id))

            self.export_to_new_shape_on_item(
                item=item,
                shape=shape,
                component=component,
                data=raw_ttml_contents,
                item_helper=item_helper
            )

            return Response()
        except Exception:
            log.exception("Failed to publish ttml")
            raise BadRequest("Failed to publish ttml")

    def export_to_new_shape_on_item(self, item: VSItem, shape: VSShape,
                                    component: VSSubtitleComponent | VSBinaryComponent, data: str,
                                    item_helper: ItemHelper):
        item_id = item.json_object["id"]
        filename = get_filename(shape.getAllFiles()) if component is None else get_filename(component.getFiles())
        self._create_shape_if_needed(shape_tag=plugin_settings.shape_tag, item_helper=item_helper)
        import_shape_raw(item_id=item_id, data=data, filename=filename, tag=plugin_settings.shape_tag)

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
