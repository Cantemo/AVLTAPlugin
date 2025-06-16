from unittest.mock import patch, MagicMock
from urllib.parse import quote_plus

from django.urls import reverse

from portal.utils.test_case import PortalBaseTestCase
from portal.vidispine.iexception import NotFoundError


class TestOpenApplicationView(PortalBaseTestCase):
    def setUp(self, mock_authenticate=True):
        super().setUp(mock_authenticate=mock_authenticate)
        self.url = reverse("av_lta:open")

    def test_get_without_params(self):
        self.login_client_as_admin()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 400)

    def test_get_with_application_param(self):
        self.login_client_as_admin()
        response = self.client.get(f"{self.url}?application=subtitle")

        self.assertEqual(response.status_code, 400)

    def test_get_with_item_ids_param(self):
        self.login_client_as_admin()
        response = self.client.get(f"{self.url}?item_ids=TEST-1,TEST-2")

        self.assertEqual(response.status_code, 400)

    def test_get_with_application_and_item_ids_param(self):
        self.login_client_as_admin()
        response = self.client.get(f"{self.url}?application=subtitle&item_ids=TEST-1,TEST-2")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/launch/subtitle", response.url)
        self.assertIn("TEST-1", response.url)
        self.assertIn("TEST-2", response.url)
        self.assertIn(quote_plus(reverse("av_lta:get_launch_template")), response.url)


class TestLaunchTemplateView(PortalBaseTestCase):
    def setUp(self, mock_authenticate=True):
        super().setUp(mock_authenticate=mock_authenticate)
        self.url = reverse("av_lta:get_launch_template")

    def test_get_without_item_ids(self):
        self.login_client_as_admin()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    @patch("portal.plugins.av_lta.views.ItemHelper")
    def test_get_with_nonexistent_item_id(self, mock_item_helper):
        # Mock the ItemHelper to raise NotFoundError
        mock_instance = MagicMock()
        mock_instance.getItems.side_effect = NotFoundError("Item not found")
        mock_item_helper.return_value = mock_instance

        self.login_client_as_admin()
        response = self.client.get(f"{self.url}?item_ids=NONEXISTENT")

        self.assertEqual(response.status_code, 404)

    @patch("portal.plugins.av_lta.views.ItemHelper")
    @patch("portal.plugins.av_lta.views.transform_items_to_lta_assets")
    def test_get_with_valid_item_id(self, mock_transform, mock_item_helper):
        mock_items = [MagicMock()]
        mock_instance = MagicMock()
        mock_instance.getItems.return_value = mock_items
        mock_item_helper.return_value = mock_instance

        mock_transform.return_value = [{"id": "TEST-1", "name": "Test Item"}]

        self.login_client_as_admin()
        response = self.client.get(f"{self.url}?item_ids=TEST-1")

        self.assertEqual(response.status_code, 200)

        # Check the response data
        self.assertIn("data", response.data)
        self.assertIn("endpoints", response.data)
        self.assertIn("settings", response.data)

        # Check data section
        self.assertIn("assets", response.data["data"])
        self.assertEqual(response.data["data"]["assets"], [{"id": "TEST-1", "name": "Test Item"}])

        # Check endpoints section
        self.assertIn("publish", response.data["endpoints"])
        self.assertIn("download", response.data["endpoints"]["publish"])
        self.assertTrue(response.data["endpoints"]["publish"]["download"])

        # Check settings section
        self.assertIn("licenseKey", response.data["settings"])
