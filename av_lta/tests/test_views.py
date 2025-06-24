from unittest.mock import patch, MagicMock
from urllib.parse import quote_plus

from django.core.exceptions import BadRequest
from django.urls import reverse
from requests import HTTPError
from rest_framework.exceptions import NotFound

from portal.plugins.av_lta.views import SubtitlePublishView
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
        self.assertIn("http", response.data["endpoints"]["publish"])

        # Check settings section
        self.assertIn("licenseKey", response.data["settings"])
        self.assertIn("timeline", response.data["settings"])
        self.assertIn("waveforms", response.data["settings"]["timeline"])
        self.assertIn("vidispine", response.data["settings"]["timeline"]["waveforms"])
        self.assertIn("apiBaseUrl", response.data["settings"]["timeline"]["waveforms"]["vidispine"])
        self.assertEquals("/AVAPI/", response.data["settings"]["timeline"]["waveforms"]["vidispine"]["apiBaseUrl"])
        self.assertEquals("vidispine", response.data["settings"]["timeline"]["waveforms"]["active"])
        self.assertLess(100, response.data["settings"]["timeline"]["waveforms"]["requestDebounceTimeMs"],
                        "The request debounce time is not recommended to be below 100ms")


class TestSubtitlePublishView(PortalBaseTestCase):
    def setUp(self, mock_authenticate=True):
        super().setUp(mock_authenticate=mock_authenticate)
        self.url = reverse("av_lta:publish")

    @patch("portal.plugins.av_lta.views.ItemHelper")
    def test_post_with_http_error(self, mock_item_helper):
        mock_request = MagicMock()
        mock_request.query_params = {"fileId": "shape1_comp1", "itemIds": "TEST-1"}
        mock_request.data = "<ttml></ttml>"
        mock_request.user = "admin"
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        mock_http_error = HTTPError(response=mock_response)
        mock_instance = MagicMock()
        mock_instance.getItems.side_effect = mock_http_error
        mock_item_helper.return_value = mock_instance

        view = SubtitlePublishView()
        response = view.post(mock_request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {"error": "Bad request"})

    @patch("portal.plugins.av_lta.views.ItemHelper")
    def test_post_with_general_exception(self, mock_item_helper):
        mock_request = MagicMock()
        mock_request.query_params = {"fileId": "shape1_comp1", "itemIds": "TEST-1"}
        mock_request.data = "<ttml></ttml>"
        mock_request.user = "admin"
        mock_instance = MagicMock()
        mock_instance.getItems.side_effect = Exception("General error")
        mock_item_helper.return_value = mock_instance

        view = SubtitlePublishView()

        with self.assertRaises(BadRequest):
            view.post(mock_request)

    def test_post_missing_file_id(self):
        mock_request = MagicMock()
        mock_request.query_params = {"itemIds": "TEST-1"}  # No fileId
        mock_request.data = "<ttml></ttml>"
        mock_request.user = "admin"

        view = SubtitlePublishView()

        with self.assertRaises(NotFound):
            view.post(mock_request)

    def test_post_missing_item_ids(self):
        mock_request = MagicMock()
        mock_request.query_params = {"fileId": "shape1_comp1"}  # No fileId
        mock_request.data = "<ttml></ttml>"
        mock_request.user = "admin"

        view = SubtitlePublishView()

        with self.assertRaises(BadRequest):
            view.post(mock_request)

    @patch("portal.plugins.av_lta.views.ItemHelper")
    def test_post_with_item_not_found(self, mock_item_helper):
        mock_request = MagicMock()
        mock_request.query_params = {"fileId": "shape1_comp1", "itemIds": "TEST-1"}
        mock_request.data = "<ttml></ttml>"
        mock_request.user = "admin"
        mock_instance = MagicMock()
        mock_instance.getItems.return_value = []
        mock_item_helper.return_value = mock_instance

        view = SubtitlePublishView()

        with self.assertRaises(NotFound):
            view.post(mock_request)

    @patch("portal.plugins.av_lta.views.ItemHelper")
    @patch("portal.plugins.av_lta.views.import_shape_raw")
    @patch("portal.plugins.av_lta.views.get_filename")
    def test_post_with_valid_data(self, mock_get_filename, mock_import_shape_raw, mock_item_helper):
        mock_request = MagicMock()
        mock_request.query_params = {"fileId": "shape1_comp1", "itemIds": "TEST-1"}
        mock_request.data = "<ttml></ttml>"
        mock_request.user = "user"
        mock_shape = MagicMock()
        mock_component = MagicMock()
        mock_item = MagicMock()
        mock_item.json_object = {"id": "TEST-1"}
        mock_shape.getSubtitleComponents.return_value = [mock_component]
        mock_component.getId.return_value = "comp1"
        mock_component_files = [MagicMock()]
        mock_component.getFiles.return_value = mock_component_files
        mock_get_filename.return_value = "test.ttml"
        mock_instance = MagicMock()
        mock_instance.getItems.return_value = [mock_item]
        mock_item_helper.return_value = mock_instance
        mock_item.getShapeById.return_value = mock_shape

        view = SubtitlePublishView()
        response = view.post(mock_request)

        self.assertEqual(response.status_code, 200)
        mock_import_shape_raw.assert_called_once_with(item_id="TEST-1", data="<ttml></ttml>", filename="test.ttml",
                                                      tag="av-subtitle", runas="user")
