import os
from unittest.mock import MagicMock
from unittest.mock import call
from unittest.mock import patch

from portal.pluginbase.core import PluginError
from portal.plugins.av_lta.apps import AVLTAConfig
from portal.utils.test_case import PortalBaseTestCase


class TestAVLTAConfig(PortalBaseTestCase):
    @patch("portal.plugins.av_lta.permissions.create_or_update_roles")
    def test_ready_method_invokes_create_or_update_roles(self, mock_create_roles):
        mock_module = MagicMock()
        mock_module.__path__ = [os.path.dirname(os.path.dirname(__file__))]

        app_config = AVLTAConfig("portal.plugins.av_lta", mock_module)

        try:
            app_config.ready()
        except PluginError:
            self.fail("ready method raised PluginError unexpectedly.")

        self.assertEqual(mock_create_roles.mock_calls, [call()])
