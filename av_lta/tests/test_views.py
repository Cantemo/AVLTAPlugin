from unittest.mock import MagicMock
from unittest.mock import patch
from urllib.parse import quote_plus

from django.core.exceptions import BadRequest
from django.urls import reverse
from portal.plugins.av_lta.forms import SettingsForm
from portal.plugins.av_lta.views import AdminIndexView
from portal.plugins.av_lta.views import SubtitlePublishView
from portal.utils.test_case import PortalBaseTestCase
from portal.vidispine.iexception import NotFoundError
from requests import HTTPError
from rest_framework.exceptions import NotFound


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
        self.assertIn("licenseKey", response.data["settings"][0])
        self.assertIn("timeline", response.data["settings"][0])
        self.assertIn("waveforms", response.data["settings"][0]["timeline"])
        self.assertIn("vidispine", response.data["settings"][0]["timeline"]["waveforms"])
        self.assertIn("apiBaseUrl", response.data["settings"][0]["timeline"]["waveforms"]["vidispine"])
        self.assertEquals("/AVAPI/", response.data["settings"][0]["timeline"]["waveforms"]["vidispine"]["apiBaseUrl"])
        self.assertEquals("vidispine", response.data["settings"][0]["timeline"]["waveforms"]["active"])
        self.assertLess(
            100,
            response.data["settings"][0]["timeline"]["waveforms"]["requestDebounceTimeMs"],
            "The request debounce time is not recommended to be below 100ms",
        )

    @patch("portal.plugins.av_lta.views.ItemHelper")
    @patch("portal.plugins.av_lta.views.transform_items_to_lta_assets")
    @patch("portal.plugins.av_lta.views.plugin_settings")
    def test_extra_settings_loaded_from_plugin_settings(self, mock_plugin_settings, mock_transform, mock_item_helper):
        mock_items = [MagicMock()]
        mock_instance = MagicMock()
        mock_instance.getItems.return_value = mock_items
        mock_item_helper.return_value = mock_instance

        mock_transform.return_value = [{"id": "TEST-1", "name": "Test Item"}]

        extra_settings_json = '{"licenseKey": "test-license-key", "timeline": {"waveforms": {"active": "test"}}}'
        mock_plugin_settings.AV_LTA_EXTRA_SETTINGS = extra_settings_json

        self.login_client_as_admin()
        response = self.client.get(f"{self.url}?item_ids=TEST-1")

        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.data["settings"]), 2)

        self.assertEqual(response.data["settings"][1]["licenseKey"], "test-license-key")
        self.assertEqual(response.data["settings"][1]["timeline"]["waveforms"]["active"], "test")

    @patch("portal.plugins.av_lta.views.ItemHelper")
    @patch("portal.plugins.av_lta.views.transform_items_to_lta_assets")
    @patch("portal.plugins.av_lta.views.plugin_settings")
    @patch("portal.plugins.av_lta.views.log")
    def test_extra_settings_with_invalid_json(self, mock_log, mock_plugin_settings, mock_transform, mock_item_helper):
        mock_items = [MagicMock()]
        mock_instance = MagicMock()
        mock_instance.getItems.return_value = mock_items
        mock_item_helper.return_value = mock_instance

        mock_transform.return_value = [{"id": "TEST-1", "name": "Test Item"}]

        mock_plugin_settings.AV_LTA_EXTRA_SETTINGS = (
            '{"licenseKey": "test-license-key", "timeline": {"waveforms": {"active": "test"'
        )

        self.login_client_as_admin()
        response = self.client.get(f"{self.url}?item_ids=TEST-1")

        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.data["settings"]), 1)

        mock_log.debug.assert_called_once_with("Failed to parse extra lta settings from plugin settings, invalid JSON")


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
        mock_import_shape_raw.assert_called_once_with(
            item_id="TEST-1", data="<ttml></ttml>", filename="test.ttml", tag="av-subtitle", runas="user"
        )


class TestAdminIndexView(PortalBaseTestCase):
    def setUp(self, mock_authenticate=True):
        super().setUp(mock_authenticate=mock_authenticate)
        self.url = reverse("av_lta:plugin_admin_index")
        self.view = AdminIndexView()

    def test_get_success_url(self):
        self.view.request = MagicMock()
        success_url = self.view.get_success_url()
        self.assertEqual(success_url, self.url)

    @patch("portal.plugins.av_lta.views.plugin_settings")
    def test_get_initial(self, mock_plugin_settings):
        mock_plugin_settings.AV_LTA_APPS_URL = "https://test.example.com"
        mock_plugin_settings.AV_LTA_PUBLISH_SHAPE_TAG = "test-tag"
        mock_plugin_settings.AV_LTA_FORCE_FULL_DOMAIN = True
        mock_plugin_settings.AV_LTA_EXTRA_SETTINGS = '{"test": "value"}'

        self.view.form_class = SettingsForm
        initial = self.view.get_initial()

        self.assertEqual(initial["AV_LTA_APPS_URL"], "https://test.example.com")
        self.assertEqual(initial["AV_LTA_PUBLISH_SHAPE_TAG"], "test-tag")
        self.assertEqual(initial["AV_LTA_FORCE_FULL_DOMAIN"], True)
        self.assertEqual(initial["AV_LTA_EXTRA_SETTINGS"], '{"test": "value"}')

    @patch("portal.plugins.av_lta.views.plugin_settings")
    @patch("portal.plugins.av_lta.views.messages")
    def test_form_valid(self, mock_messages, mock_plugin_settings):
        form = SettingsForm(
            data={
                "AV_LTA_APPS_URL": "https://new.example.com",
                "AV_LTA_PUBLISH_SHAPE_TAG": "new-tag",
                "AV_LTA_FORCE_FULL_DOMAIN": True,
                "AV_LTA_EXTRA_SETTINGS": '{"new": "value"}',
            }
        )
        form.is_valid()

        self.view.request = MagicMock()
        self.view.form_valid(form)

        for key, value in form.cleaned_data.items():
            self.assertTrue(hasattr(mock_plugin_settings, key))
            self.assertEqual(getattr(mock_plugin_settings, key), value)

        mock_messages.success.assert_called_once()

    @patch("portal.plugins.av_lta.views.plugin_settings")
    def test_get(self, mock_plugin_settings):
        mock_plugin_settings.AV_LTA_APPS_URL = "https://test.example.com"
        mock_plugin_settings.AV_LTA_PUBLISH_SHAPE_TAG = "test-tag"
        mock_plugin_settings.AV_LTA_FORCE_FULL_DOMAIN = True
        mock_plugin_settings.AV_LTA_EXTRA_SETTINGS = '{"test": "value"}'

        self.login_client_as_admin()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "av_lta/admin_index.html")
        self.assertIsInstance(response.context["form"], SettingsForm)

        form = response.context["form"]
        self.assertEqual(form.initial["AV_LTA_APPS_URL"], "https://test.example.com")
        self.assertEqual(form.initial["AV_LTA_PUBLISH_SHAPE_TAG"], "test-tag")
        self.assertEqual(form.initial["AV_LTA_FORCE_FULL_DOMAIN"], True)
        self.assertEqual(form.initial["AV_LTA_EXTRA_SETTINGS"], '{"test": "value"}')

    @patch("portal.plugins.av_lta.views.plugin_settings")
    @patch("portal.plugins.av_lta.views.messages")
    def test_post(self, mock_messages, mock_plugin_settings):
        self.login_client_as_admin()

        form_data = {
            "AV_LTA_APPS_URL": "https://new.example.com",
            "AV_LTA_PUBLISH_SHAPE_TAG": "new-tag",
            "AV_LTA_FORCE_FULL_DOMAIN": True,
            "AV_LTA_EXTRA_SETTINGS": '{"new": "value"}',
        }

        response = self.client.post(self.url, form_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)

        mock_messages.success.assert_called_once()
