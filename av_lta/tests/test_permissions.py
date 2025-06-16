import logging
from unittest.mock import patch, MagicMock

from portal.pluginbase.core import PluginError
from portal.plugins.av_lta.permissions import create_or_update_roles
from portal.utils.test_case import PortalBaseTestCase


class TestCreateOrUpdateRoles(PortalBaseTestCase):

    @patch('portal.plugins.av_lta.permissions.client.post')
    def test_create_roles_successful(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        try:
            create_or_update_roles()
        except PluginError:
            self.fail("create_or_update_roles raised PluginError unexpectedly.")

        mock_post.assert_called_once_with(
            user="admin",
            url="/API/v2/groups/roles/create/",
            json={
                "name": "av_lta_role",
                "label": "AV LTA Roles",
                "children": [
                    {
                        "name": "av_lta_role_subtitle",
                        "label": "Subtitle",
                        "children": [],
                    },
                ],
            }
        )

    @patch('portal.plugins.av_lta.permissions.client.post')
    def test_create_roles_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.content = "Internal Server Error"
        mock_post.return_value = mock_response

        with self.assertRaises(PluginError) as context:
            create_or_update_roles()

        self.assertIn("Failed to create role av_lta_role", str(context.exception))
        self.assertIn("500 - Internal Server Error", str(context.exception))

    @patch('portal.plugins.av_lta.permissions.client.post')
    def test_create_roles_logging(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        with self.assertLogs('portal.plugins.av_lta.permissions', level=logging.INFO) as log:
            create_or_update_roles()

        self.assertIn("INFO:portal.plugins.av_lta.permissions:Create/update role tree av_lta_role", log.output)
