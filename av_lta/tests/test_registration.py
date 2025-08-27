from unittest.mock import patch

from portal.plugins.av_lta.registration import AVLTARegisterPlugin
from portal.utils.test_case import PortalBaseTestCase


class TestAVLTARegisterPlugin(PortalBaseTestCase):
    def test_init(self):
        plugin = AVLTARegisterPlugin()
        self.assertEqual(plugin.name, "AVLTARegisterPlugin")
        self.assertEqual(plugin.plugin_guid, "0e3124bc-1f37-49cc-adf5-ae2fc3b8bf42")

    @patch("portal.plugins.av_lta.registration.is_app_enabled")
    def test_call(self, mock_is_app_enabled):
        mock_is_app_enabled.return_value = True
        plugin = AVLTARegisterPlugin()
        result = plugin()
        self.assertEqual(result["name"], "Accurate.Video LTA Plugin")
        self.assertEqual(result["author"], "Codemill AB")
        self.assertEqual(result["author_url"], "www.codemill.se")
        self.assertEqual(result["notes"], "Copyright © 2022-2024. All rights reserved.")
        self.assertEqual(result["enabled"], True)
        self.assertEqual(result["app_id"], "se.codemill.portal.av_lta")
