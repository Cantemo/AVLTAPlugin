from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from portal.externals.VidiRest.objects.item import VSItem
from portal.externals.VidiRest.objects.storage import VSFile
from portal.externals.VidiRest.objects.storage import VSStorage

from ..transform import get_filename
from ..transform import transform_item_to_lta_asset
from ..transform import transform_shape_to_lta_files


class TestMissingMedia(TestCase):
    def setUp(self):
        video_file = {"id": "TEST-10", "path": "video.mp4", "uri": ["https://media.example.test/video.mp4"]}
        video_shape = {
            "id": "TEST-2",
            "tag": ["lowres"],
            "mimeType": ["video/mp4"],
            "containerComponent": {"startTimecode": 0, "timeCodeTimeBase": {"numerator": 1, "denominator": 25}},
            "videoComponent": [
                {
                    "id": "TEST-20",
                    "file": [video_file],
                    "codec": "h264",
                    "timeBase": {"numerator": 1, "denominator": 12800},
                    "averageFrameRate": {"numerator": 25, "denominator": 1},
                    "resolution": {"width": 1280, "height": 720},
                    "displayAspectRatio": {"horizontal": 16, "vertical": 9},
                }
            ],
            "audioComponent": [
                {
                    "id": "TEST-21",
                    "file": [video_file],
                    "codec": "aac",
                    "channelCount": 2,
                    "timeBase": {"numerator": 1, "denominator": 44100},
                }
            ],
        }
        sibling = deepcopy(video_shape)
        sibling["id"] = "TEST-3"
        self.shapes = [
            video_shape,
            sibling,
            {
                "id": "TEST-4",
                "mimeType": ["application/ttml+xml"],
                "subtitleComponent": [
                    {
                        "id": "TEST-22",
                        "file": [
                            {
                                "id": "TEST-11",
                                "path": "captions.ttml",
                                "uri": ["https://media.example.test/captions.ttml"],
                            }
                        ],
                    }
                ],
            },
        ]
        self.item_data = {"json_object": {"id": "TEST-1", "metadata": {"timespan": []}, "shape": self.shapes}}
        self.archive_lookup = patch(
            "portal.externals.VidiRest.objects.shape.cache_get_vidispine_archive_storages", return_value=[]
        )
        self.archive_lookup.start()
        self.addCleanup(self.archive_lookup.stop)

    def test_should_skip_video_derivative_without_files_and_keep_other_shapes(self):
        for omit_files in (False, True):
            with self.subTest(omit_files=omit_files):
                for component_type in ("videoComponent", "audioComponent"):
                    component = self.shapes[0][component_type][0]
                    if omit_files:
                        component.pop("file")
                    else:
                        component["file"] = []

                asset = transform_item_to_lta_asset(VSItem(**self.item_data))

                self.assertEqual([file.id for file in asset.files], ["TEST-3", "TEST-4_TEST-22"])
                self.assertEqual(asset.files[0].type, "VIDEO")
                self.assertEqual(asset.files[0].url, "https://media.example.test/video.mp4")

    def test_should_skip_video_files_filtered_out_by_archive_storage(self):
        self.shapes[0]["videoComponent"][0]["file"][0]["storage"] = "TEST-99"
        with patch(
            "portal.externals.VidiRest.objects.shape.cache_get_vidispine_archive_storages",
            return_value=[VSStorage({"id": "TEST-99"})],
        ):
            asset = transform_item_to_lta_asset(VSItem(**self.item_data))

        self.assertEqual([file.id for file in asset.files], ["TEST-3", "TEST-4_TEST-22"])

    def test_should_keep_video_without_optional_container_component(self):
        del self.shapes[0]["containerComponent"]

        file = transform_shape_to_lta_files(VSItem(**self.item_data).getShapes()[0])[0]

        self.assertEqual(file.id, "TEST-2")
        self.assertEqual(file.type, "VIDEO")
        self.assertEqual(file.url, "https://media.example.test/video.mp4")
        self.assertIsNone(file.container.startTime)
        self.assertEqual(file.container.videoStreams[0].frameRateNumerator, 25)

    def test_should_skip_empty_standalone_components_beside_playable_video(self):
        for component_type in ("audioComponent", "subtitleComponent", "binaryComponent"):
            with self.subTest(component_type=component_type):
                self.shapes[0][component_type] = [{"id": "empty", "file": []}]
                files = transform_shape_to_lta_files(VSItem(**self.item_data).getShapes()[0])
                self.assertEqual([file.id for file in files], ["TEST-2"])

    def test_should_skip_derivatives_without_browser_accessible_urls(self):
        for component_type in ("videoComponent", "audioComponent", "subtitleComponent", "binaryComponent"):
            for uris in ([], ["file:///offline/media.mp4"]):
                with self.subTest(component_type=component_type, uris=uris):
                    shape = self.shapes[0].copy()
                    for key in ("videoComponent", "audioComponent", "subtitleComponent", "binaryComponent"):
                        shape.pop(key, None)
                    shape[component_type] = [
                        {"id": "offline", "file": [{"id": "file", "path": "media.mp4", "uri": uris}]}
                    ]
                    self.item_data["json_object"]["shape"] = [shape]
                    files = transform_shape_to_lta_files(VSItem(**self.item_data).getShapes()[0])
                    self.assertEqual(files, [])

    def test_should_keep_standalone_audio_when_video_has_no_files(self):
        self.shapes[0]["videoComponent"][0]["file"] = []

        files = transform_shape_to_lta_files(VSItem(**self.item_data).getShapes()[0])

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].type, "AUDIO")
        self.assertEqual(files[0].container.audioStreams[0].sampleRate, 44100)

    def test_should_transform_item_without_optional_metadata(self):
        for metadata in (None, {}):
            with self.subTest(metadata=metadata):
                self.item_data["json_object"]["metadata"] = metadata
                asset = transform_item_to_lta_asset(VSItem(**self.item_data))
                self.assertEqual(asset.metadata[0].value, "TEST-1")
                self.assertEqual(asset.markerGroups, [])

        del self.item_data["json_object"]["metadata"]
        asset = transform_item_to_lta_asset(VSItem(**self.item_data))

        self.assertEqual(asset.id, "TEST-1")
        self.assertEqual(asset.markerGroups, [])
        self.assertIn("TEST-2", [file.id for file in asset.files])

    def test_should_return_asset_without_files_for_fully_empty_shape(self):
        self.item_data["json_object"]["shape"] = [{"id": "TEST-5", "tag": ["vod"]}]

        asset = transform_item_to_lta_asset(VSItem(**self.item_data))

        self.assertEqual(asset.id, "TEST-1")
        self.assertEqual(asset.files, [])

    def test_should_skip_thumbnail_without_timestamp_and_keep_valid_thumbnail(self):
        self.item_data["json_object"]["thumbnails"] = {
            "uri": [
                "https://media.example.test/thumbnail.jpg",
                "https://media.example.test/thumbnail/TEST-1;version=0/0@PAL",
            ]
        }

        asset = transform_item_to_lta_asset(VSItem(**self.item_data))

        thumbnails = [file for file in asset.files if file.type == "STILL_FRAME"]
        self.assertEqual([file.id for file in thumbnails], ["TEST-1-thumbnail-1"])
        self.assertEqual(thumbnails[0].metadata[0].value, "0@PAL")
        self.assertEqual(asset.files[0].id, "TEST-2")

    def test_should_return_empty_filename_when_no_usable_path_exists(self):
        for paths in ([], [None], [""], ["   "]):
            with self.subTest(paths=paths):
                self.assertEqual(get_filename([VSFile({"path": path}) for path in paths]), "")

    def test_should_preserve_filename_preference_with_missing_paths(self):
        files = [VSFile({"path": path}) for path in (None, "audio.wav", "video.webm", "video.mp4", "   ")]

        self.assertEqual(get_filename(files), "video.mp4")
