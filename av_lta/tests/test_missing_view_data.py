from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock
from unittest.mock import patch

from django.test import RequestFactory
from portal.externals.VidiRest.objects.item import VSItem
from portal.externals.VidiRest.objects.shape import VSShape
from requests import HTTPError
from requests import Response
from rest_framework.exceptions import NotFound

from ..views import ProxyLTAView
from ..views import SubtitlePublishView


class TestMissingPublishData(TestCase):
    @patch("portal.plugins.av_lta.views.StorageHelper")
    @patch("portal.plugins.av_lta.views.ItemHelper")
    def test_should_preserve_upstream_error_status_with_or_without_json_body(self, item_helper, storage_helper):
        for body, expected in (
            (b"", {"detail": "Failed to publish ttml"}),
            (b"<h1>Service unavailable</h1>", {"detail": "Failed to publish ttml"}),
            (b'{"error":"Service unavailable"}', {"error": "Service unavailable"}),
        ):
            with self.subTest(body=body):
                upstream = Response()
                upstream.status_code = 503
                upstream._content = body
                item_helper.return_value.getItems.side_effect = HTTPError(response=upstream)
                request = SimpleNamespace(
                    query_params={"itemIds": "TEST-1", "fileId": "TEST-2_TEST-3"}, data=b"<tt></tt>", user="test-user"
                )

                response = SubtitlePublishView().post(request)

                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.data, expected)
                self.assertEqual(storage_helper.return_value.mock_calls, [])

    @patch("portal.plugins.av_lta.views.import_shape_from_existing_file")
    @patch("portal.plugins.av_lta.views.update_or_create_file_data")
    @patch("portal.plugins.av_lta.views.StorageHelper")
    @patch("portal.plugins.av_lta.views.ItemHelper")
    @patch(
        "portal.plugins.av_lta.views.plugin_settings",
        SimpleNamespace(AV_LTA_TARGET_STORAGE_ID="", AV_LTA_PUBLISH_SHAPE_TAG="av-subtitle"),
    )
    @patch("portal.externals.VidiRest.objects.shape.cache_get_vidispine_archive_storages", return_value=[])
    def test_should_publish_valid_source_to_its_item_and_storage(
        self, archive_lookup, item_helper, storage_helper, write_data, import_shape
    ):
        item_helper.return_value.getItems.return_value = [
            VSItem(
                {
                    "id": "TEST-1",
                    "shape": [
                        {
                            "id": "TEST-2",
                            "subtitleComponent": [
                                {
                                    "id": "TEST-3",
                                    "file": [{"id": "TEST-10", "path": "captions.ttml", "storage": "TEST-4"}],
                                }
                            ],
                        }
                    ],
                }
            )
        ]
        storage_helper.return_value.createFileEntity.return_value = {"id": "TEST-30", "state": "OPEN"}
        request = SimpleNamespace(
            query_params={"itemIds": "TEST-1", "fileId": "TEST-2_TEST-3"}, data=b"<tt></tt>", user="test-user"
        )

        response = SubtitlePublishView().post(request)

        self.assertEqual(response.status_code, 200)
        storage_helper.return_value.createFileEntity.assert_called_once_with(
            storageId="TEST-4", filepath="captions.ttml", createOnly=True
        )
        write_data.assert_called_once_with(file_id="TEST-30", data=b"<tt></tt>", runas="test-user")
        import_shape.assert_called_once_with(item_id="TEST-1", file_id="TEST-30", tag="av-subtitle", runas="test-user")

    @patch("portal.plugins.av_lta.views.import_shape_from_existing_file")
    @patch("portal.plugins.av_lta.views.update_or_create_file_data")
    @patch("portal.plugins.av_lta.views.plugin_settings")
    @patch("portal.externals.VidiRest.objects.shape.cache_get_vidispine_archive_storages", return_value=[])
    def test_should_reject_missing_source_filename_before_writing(
        self, archive_lookup, plugin_settings, write_data, import_shape
    ):
        plugin_settings.AV_LTA_TARGET_STORAGE_ID = "TEST-1"
        for file_data in ([], [{"id": "TEST-10"}], [{"id": "TEST-10", "path": None}]):
            for component_type in ("subtitleComponent", "binaryComponent"):
                with self.subTest(file_data=file_data, component_type=component_type):
                    shape = VSShape({"id": "TEST-2", component_type: [{"id": "TEST-3", "file": file_data}]})
                    component = (shape.getSubtitleComponents() + shape.getBinaryComponents())[0]
                    item_helper = Mock()
                    storage_helper = Mock()
                    storage_helper.createFileEntity.return_value = {"id": "TEST-30", "state": "OPEN"}

                    with self.assertRaisesRegex(NotFound, "Unable to determine subtitle filename"):
                        SubtitlePublishView().export_to_new_shape_on_item(
                            item=VSItem({"id": "TEST-1"}),
                            shape=shape,
                            component=component,
                            data=b"<tt></tt>",
                            item_helper=item_helper,
                            storage_helper=storage_helper,
                            runas="test-user",
                        )

                    self.assertEqual(item_helper.mock_calls, [])
                    self.assertEqual(storage_helper.mock_calls, [])
                    write_data.assert_not_called()
                    import_shape.assert_not_called()


class TestMissingProxyHTML(TestCase):
    @patch("portal.plugins.av_lta.views.plugin_settings", SimpleNamespace(AV_LTA_APPS_URL="https://apps.example.test/"))
    @patch("portal.plugins.av_lta.views.requests.request")
    def test_should_preserve_upstream_html_without_head_or_base(self, request):
        for html in (
            b"<h1>Service unavailable</h1>",
            b"<html><head><title>Error</title></head><body>Error</body></html>",
        ):
            with self.subTest(html=html):
                upstream = Response()
                upstream.status_code = 503
                upstream._content = html
                upstream.headers["content-type"] = "text/html"
                request.return_value = upstream

                response = ProxyLTAView().get(RequestFactory().get("/av_lta/apps/"), path="")

                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.content, html)

    @patch("portal.plugins.av_lta.views.reverse", return_value="/av_lta/apps/")
    @patch("portal.plugins.av_lta.views.plugin_settings", SimpleNamespace(AV_LTA_APPS_URL="https://apps.example.test/"))
    @patch("portal.plugins.av_lta.views.requests.request")
    def test_should_still_rewrite_existing_application_base(self, request, reverse):
        upstream = Response()
        upstream.status_code = 200
        upstream._content = b'<html><head><base href="/"></head></html>'
        upstream.headers["content-type"] = "text/html"
        request.return_value = upstream

        response = ProxyLTAView().get(RequestFactory().get("/av_lta/apps/"), path="")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'href="/av_lta/apps/"', response.content)
