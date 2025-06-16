from portal.utils.test_case import PortalBaseTestCase
from portal.plugins.av_lta.vs_helpers import get_vidispine_url, get_vidispine_auth, vidispine_request, import_shape_raw
from unittest.mock import patch, MagicMock
from requests import HTTPError


class TestGetVidispineUrl(PortalBaseTestCase):
    @patch("portal.plugins.av_lta.vs_helpers.settings")
    def test_get_vidispine_url_success(self, mock_settings):
        mock_settings.VIDISPINE_URL = "http://vidispine.test"
        mock_settings.VIDISPINE_PORT = "8080"
        path = "/some/path"

        result = get_vidispine_url(path)

        self.assertEqual(result, "http://vidispine.test:8080/API/some/path")

    @patch("portal.plugins.av_lta.vs_helpers.settings")
    def test_get_vidispine_url_empty_path(self, mock_settings):
        mock_settings.VIDISPINE_URL = "http://vidispine.test"
        mock_settings.VIDISPINE_PORT = "8080"
        path = ""

        result = get_vidispine_url(path)

        self.assertEqual(result, "http://vidispine.test:8080/API")

    @patch("portal.plugins.av_lta.vs_helpers.settings")
    def test_get_vidispine_url_with_trailing_slash_in_path(self, mock_settings):
        mock_settings.VIDISPINE_URL = "http://vidispine.test"
        mock_settings.VIDISPINE_PORT = "8080"
        path = "/some/path/"

        result = get_vidispine_url(path)

        self.assertEqual(result, "http://vidispine.test:8080/API/some/path/")


class TestGetVidispineAuth(PortalBaseTestCase):
    @patch("portal.plugins.av_lta.vs_helpers.settings")
    def test_get_vidispine_auth_success(self, mock_settings):
        mock_settings.VIDISPINE_USERNAME = "test_user"
        mock_settings.VIDISPINE_PASSWORD = "test_password"

        username, password = get_vidispine_auth()

        self.assertEqual(username, "test_user")
        self.assertEqual(password, "test_password")


class TestVidispineRequest(PortalBaseTestCase):
    @patch("portal.plugins.av_lta.vs_helpers.requests.request")
    @patch("portal.plugins.av_lta.vs_helpers.get_vidispine_url")
    @patch("portal.plugins.av_lta.vs_helpers.get_vidispine_auth")
    def test_vidispine_request_success(self, mock_get_auth, mock_get_url, mock_request):
        mock_get_auth.return_value = ("test_user", "test_password")
        mock_get_url.return_value = "http://vidispine.test:8080/API/some/path"
        mock_response = MagicMock()
        mock_request.return_value = mock_response

        result = vidispine_request("GET", "/some/path")

        mock_request.assert_called_once_with(
            "GET", 
            "http://vidispine.test:8080/API/some/path", 
            auth=("test_user", "test_password"), 
            headers={"Accept": "application/json"}
        )
        mock_response.raise_for_status.assert_called_once()
        self.assertEqual(result, mock_response)

    @patch("portal.plugins.av_lta.vs_helpers.requests.request")
    @patch("portal.plugins.av_lta.vs_helpers.get_vidispine_url")
    @patch("portal.plugins.av_lta.vs_helpers.get_vidispine_auth")
    def test_vidispine_request_with_runas(self, mock_get_auth, mock_get_url, mock_request):
        mock_get_auth.return_value = ("test_user", "test_password")
        mock_get_url.return_value = "http://vidispine.test:8080/API/some/path"
        mock_response = MagicMock()
        mock_request.return_value = mock_response

        result = vidispine_request("GET", "/some/path", runas="other_user")

        mock_request.assert_called_once_with(
            "GET", 
            "http://vidispine.test:8080/API/some/path", 
            auth=("test_user", "test_password"), 
            headers={"Accept": "application/json", "RunAs": "other_user"}
        )
        mock_response.raise_for_status.assert_called_once()
        self.assertEqual(result, mock_response)

    @patch("portal.plugins.av_lta.vs_helpers.requests.request")
    @patch("portal.plugins.av_lta.vs_helpers.get_vidispine_url")
    @patch("portal.plugins.av_lta.vs_helpers.get_vidispine_auth")
    def test_vidispine_request_with_custom_headers(self, mock_get_auth, mock_get_url, mock_request):
        mock_get_auth.return_value = ("test_user", "test_password")
        mock_get_url.return_value = "http://vidispine.test:8080/API/some/path"
        mock_response = MagicMock()
        mock_request.return_value = mock_response

        result = vidispine_request("GET", "/some/path", headers={"Custom-Header": "value"})

        mock_request.assert_called_once_with(
            "GET", 
            "http://vidispine.test:8080/API/some/path", 
            auth=("test_user", "test_password"), 
            headers={"Accept": "application/json", "Custom-Header": "value"}
        )
        mock_response.raise_for_status.assert_called_once()
        self.assertEqual(result, mock_response)

    @patch("portal.plugins.av_lta.vs_helpers.requests.request")
    @patch("portal.plugins.av_lta.vs_helpers.get_vidispine_url")
    @patch("portal.plugins.av_lta.vs_helpers.get_vidispine_auth")
    def test_vidispine_request_http_error(self, mock_get_auth, mock_get_url, mock_request):
        mock_get_auth.return_value = ("test_user", "test_password")
        mock_get_url.return_value = "http://vidispine.test:8080/API/some/path"
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = HTTPError("HTTP Error")
        mock_request.return_value = mock_response

        with self.assertRaises(HTTPError):
            vidispine_request("GET", "/some/path")

        mock_request.assert_called_once()
        mock_response.raise_for_status.assert_called_once()


class TestImportShapeRaw(PortalBaseTestCase):
    @patch("portal.plugins.av_lta.vs_helpers.vidispine_request")
    def test_import_shape_raw_minimal_params(self, mock_vidispine_request):
        mock_response = MagicMock()
        mock_vidispine_request.return_value = mock_response
        item_id = "TEST-1"
        data = "<ttml>Test subtitle</ttml>"

        result = import_shape_raw(item_id=item_id, data=data)

        mock_vidispine_request.assert_called_once_with(
            "POST", 
            f"/item/{item_id}/shape/raw", 
            params={
                'tag': None,
                'storageId': None,
                'filename': None,
                'transferPriority': None,
                'transferId': None,
                'notification': None,
                'notificationData': None,
                'priority': None,
                'jobmetadata': None,
            }, 
            data=data, 
            runas=None
        )
        self.assertEqual(result, mock_response)

    @patch("portal.plugins.av_lta.vs_helpers.vidispine_request")
    def test_import_shape_raw_all_params(self, mock_vidispine_request):
        mock_response = MagicMock()
        mock_vidispine_request.return_value = mock_response

        item_id = "TEST-1"
        data = "<ttml>Test subtitle</ttml>"
        tag = "av-subtitle"
        storage_id = "VX-1"
        filename = "test.ttml"
        transfer_priority = 1
        transfer_id = "transfer-1"
        notification = "http://example.com/notify"
        notification_data = "notification-data"
        priority = "HIGH"
        jobmetadata = ["key1=value1", "key2=value2"]
        runas = "admin"

        result = import_shape_raw(
            item_id=item_id,
            data=data,
            tag=tag,
            storage_id=storage_id,
            filename=filename,
            transfer_priority=transfer_priority,
            transfer_id=transfer_id,
            notification=notification,
            notification_data=notification_data,
            priority=priority,
            jobmetadata=jobmetadata,
            runas=runas
        )

        mock_vidispine_request.assert_called_once_with(
            "POST", 
            f"/item/{item_id}/shape/raw", 
            params={
                'tag': tag,
                'storageId': storage_id,
                'filename': filename,
                'transferPriority': transfer_priority,
                'transferId': transfer_id,
                'notification': notification,
                'notificationData': notification_data,
                'priority': priority,
                'jobmetadata': jobmetadata,
            }, 
            data=data, 
            runas=runas
        )
        self.assertEqual(result, mock_response)
