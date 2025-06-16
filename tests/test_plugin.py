from unittest.mock import Mock

from portal.plugins.av_lta.plugin import (
    AVLTAURLPlugin,
    AVLTAJavascriptPlugin,
    AVLTAItemGearboxMenuPlugin,
    AVLTASearchPlugin,
    AVLTAMediaBinDropdown,
)
from portal.utils.test_case import PortalBaseTestCase


class TestAVLTAURLPlugin(PortalBaseTestCase):
    def test_init(self):
        plugin = AVLTAURLPlugin()
        self.assertEqual(plugin.name, "AVLTAURLPlugin")
        self.assertEqual(plugin.urls, "portal.plugins.av_lta.urls")
        self.assertEqual(plugin.urlpattern, r"^av_lta/")
        self.assertEqual(plugin.namespace, r"av_lta")
        self.assertEqual(plugin.plugin_guid, "a202cfc0-2a1e-44b1-9e1c-1e3586a1ba2a")


class TestAVLTAJavascriptPlugin(PortalBaseTestCase):
    def test_init(self):
        plugin = AVLTAJavascriptPlugin()
        self.assertEqual(plugin.name, "header_css_js")
        self.assertEqual(plugin.plugin_guid, "e07e494f-be01-4eaf-91c0-0712b495eb00")

    def test_return_string(self):
        plugin = AVLTAJavascriptPlugin()
        result = plugin.return_string("tagname")
        self.assertEqual(
            result,
            {
                "guid": "e07e494f-be01-4eaf-91c0-0712b495eb00",
                "template": "av_lta/av_lta_javascript.html",
            },
        )


class TestAVLTAItemGearboxMenuPlugin(PortalBaseTestCase):
    def test_init(self):
        plugin = AVLTAItemGearboxMenuPlugin()
        self.assertEqual(plugin.name, "MediaViewDropdown")
        self.assertEqual(plugin.plugin_guid, "3c3b2049-3529-47b5-b638-aa4e324af447")

    def test_return_string(self):
        plugin = AVLTAItemGearboxMenuPlugin()

        mock_item = Mock()
        mock_item.getId.return_value = "TEST-1"

        context = {"item": mock_item}

        result = plugin.return_string("tagname", None, context)

        self.assertEqual(
            result,
            {
                "guid": "3c3b2049-3529-47b5-b638-aa4e324af447",
                "context": {"item_ids": "TEST-1"},
                "template": "av_lta/av_lta_menu_item.html",
            },
        )


class TestAVLTASearchPlugin(PortalBaseTestCase):
    def test_init(self):
        plugin = AVLTASearchPlugin()
        self.assertEqual(plugin.name, "vs_collection_view_dropdown")
        self.assertEqual(plugin.plugin_guid, "01474b54-bbdf-443e-a431-be10504142f3")

    def test_return_string(self):
        plugin = AVLTASearchPlugin()
        result = plugin.return_string("tagname")
        self.assertEqual(
            result,
            {
                "guid": "01474b54-bbdf-443e-a431-be10504142f3",
                "template": "av_lta/av_lta_menu_search.html",
            },
        )


class TestAVLTAMediaBinDropdown(PortalBaseTestCase):
    def test_init(self):
        plugin = AVLTAMediaBinDropdown()
        self.assertEqual(plugin.name, "MediaBinDropdown")
        self.assertEqual(plugin.plugin_guid, "a176885b-e7bd-4532-85b7-aa0d1ceedd53")

    def test_return_string(self):
        plugin = AVLTAMediaBinDropdown()
        result = plugin.return_string("tagname")
        self.assertEqual(
            result,
            {
                "guid": "a176885b-e7bd-4532-85b7-aa0d1ceedd53",
                "template": "av_lta/av_lta_menu_media_bin.html",
            },
        )
