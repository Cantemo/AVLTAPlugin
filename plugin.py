import logging

from portal.generic.plugin_interfaces import (IPluginURL, IPluginBlock)
from portal.pluginbase.core import Plugin, implements

log = logging.getLogger(__name__)


class AVLTAURLPlugin(Plugin):
    implements(IPluginURL)

    def __init__(self):
        self.name = self.__class__.__name__
        self.urls = 'portal.plugins.av_lta.urls'
        self.urlpattern = r'^av_lta/'
        self.namespace = r'av_lta'
        self.plugin_guid = 'a202cfc0-2a1e-44b1-9e1c-1e3586a1ba2a'
        log.debug(f"Initiated {self.name}")


AVLTAURLPlugin()


class AVLTAJavascriptPlugin(Plugin):
    implements(IPluginBlock)

    def __init__(self):
        self.name = "header_css_js"
        self.plugin_guid = "e07e494f-be01-4eaf-91c0-0712b495eb00"

    def return_string(self, tagname, *args):
        return {"guid": self.plugin_guid, "template": "av_lta/av_lta_javascript.html"}


AVLTAJavascriptPlugin()


class AVLTAItemGearboxMenuPlugin(Plugin):
    implements(IPluginBlock)

    def __init__(self):
        self.name = "MediaViewDropdown"
        self.plugin_guid = "3c3b2049-3529-47b5-b638-aa4e324af447"

    def return_string(self, tagname, *args):
        _context = args[1]
        item = _context["item"]
        # TODO: Only show link if correct media type
        # if item.getItemType() in ["video", "audio", "document"]:
        item_ids = [item.getId()]
        return {
            "guid": self.plugin_guid,
            "context": dict(
                item_ids=",".join(item_ids)
            ),
            "template": "av_lta/av_lta_menu_item.html"
        }


AVLTAItemGearboxMenuPlugin()


class AVLTASearchPlugin(Plugin):
    implements(IPluginBlock)

    def __init__(self):
        self.name = "vs_collection_view_dropdown"
        self.plugin_guid = "01474b54-bbdf-443e-a431-be10504142f3"

    def return_string(self, tagname, *args):
        return {"guid": self.plugin_guid, "template": "av_lta/av_lta_menu_search.html"}


AVLTASearchPlugin()


class AVLTAMediaBinDropdown(Plugin):
    implements(IPluginBlock)

    def __init__(self):
        self.name = "MediaBinDropdown"
        self.plugin_guid = "a176885b-e7bd-4532-85b7-aa0d1ceedd53"

    def return_string(self, tagname, *args):
        return {"guid": self.plugin_guid, "template": "av_lta/av_lta_menu_media_bin.html"}


AVLTAMediaBinDropdown()
