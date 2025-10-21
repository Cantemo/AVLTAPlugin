from portal.externals.VidiRest.objects.item import VSItem
from portal.utils.test_case import PortalBaseTestCase

from ..transform import transform_item_to_lta_asset
from ..transform import transform_shape_to_lta_files
from ..transform import transform_subclips_to_marker_groups


class TestTransform(PortalBaseTestCase):

    def setUp(self, mock_authenticate=True):
        super().setUp(mock_authenticate=mock_authenticate)
        super(TestTransform, self).setUp()
        self.test_item = VSItem(**self.read_json("vsitem.json"))
        self.test_video_proxy_shape = self.test_item.getShapes()[0]
        self.test_video_original_shape = self.test_item.getShapes()[1]
        self.test_subtitle_ttml_shape = self.test_item.getShapes()[2]

    def test_transform_item_to_lta_asset(self):
        asset = transform_item_to_lta_asset(self.test_item)
        # Asset
        self.assertEqual(asset.id, "VX-1")
        self.assertGreater(len(asset.files), 0)
        self.assertEqual(asset.metadata[0].key, "title")
        self.assertEqual(asset.metadata[0].value, "Bunny_H264_Webproxy_TC2.mp4")
        self.assertEqual(asset.callerAccess.write, True)
        self.assertEqual(asset.callerAccess.read, True)

    def test_transform_item_thumbnails(self):
        asset = transform_item_to_lta_asset(self.test_item)

        thumbnails = [file for file in asset.files if file.type == "STILL_FRAME"]
        self.assertGreater(len(thumbnails), 0)
        self.assertEquals(
            thumbnails[0].url, "/APInoauth/thumbnail/VX-2/VX-1;version=0/0@PAL?hash=2708d1da27db2bafd356887d87425603"
        )
        self.assertEquals(thumbnails[0].metadata[0].key, "still_frame:timestamp")
        self.assertEquals(thumbnails[0].metadata[0].value, "0@PAL")

    def test_transform_video_shape_to_lta_file(self):
        file = transform_shape_to_lta_files(self.test_video_proxy_shape)[0]
        # File
        self.assertEquals(file.id, "VX-2")
        self.assertEquals(file.type, "VIDEO")
        self.assertEquals(file.url, "/APInoauth/storage/VX-1/file/VX-2/0.818499829971718/VX-2.mp4")
        self.assertEqual(file.metadata[0].key, "tag")
        self.assertEqual(file.metadata[0].value, "lowres")
        # Container
        self.assertEquals(file.container.format, "video/mp4")
        self.assertEquals(file.container.startTime.frame, 0)
        self.assertEquals(file.container.startTime.numerator, 25)
        self.assertEquals(file.container.startTime.denominator, 1)
        # Video streams
        self.assertEquals(len(file.container.videoStreams), 1)
        self.assertEquals(file.container.videoStreams[0].frameRateNumerator, 25)
        self.assertEquals(file.container.videoStreams[0].frameRateDenominator, 1)
        self.assertEquals(file.container.videoStreams[0].timeBaseNumerator, 1)
        self.assertEquals(file.container.videoStreams[0].timeBaseDenominator, 12800)
        self.assertEquals(file.container.videoStreams[0].resolutionWidth, 1280)
        self.assertEquals(file.container.videoStreams[0].resolutionHeight, 720)
        self.assertEquals(file.container.videoStreams[0].codec, "h264")
        self.assertEquals(file.container.videoStreams[0].aspectRatioWidth, 16)
        self.assertEquals(file.container.videoStreams[0].aspectRatioHeight, 9)
        self.assertEquals(file.container.videoStreams[0].duration, 7329280)
        self.assertEquals(file.container.videoStreams[0].bitrate, 2500305)
        self.assertEquals(len(file.container.videoStreams[0].metadata), 7)
        # Audio streams
        self.assertEqual(len(file.container.audioStreams), 1)
        self.assertEquals(file.container.audioStreams[0].channels, 2)
        self.assertEquals(file.container.audioStreams[0].timeBaseNumerator, 1)
        self.assertEquals(file.container.audioStreams[0].timeBaseDenominator, 44100)
        self.assertEquals(file.container.audioStreams[0].sampleRate, 44100)
        self.assertEquals(file.container.audioStreams[0].codec, "aac")
        self.assertEquals(file.container.audioStreams[0].bitrate, 130230)
        self.assertEquals(file.container.audioStreams[0].duration, 25251043)
        self.assertEquals(len(file.container.audioStreams[0].metadata), 6)
        item_track = next((x for x in file.container.audioStreams[0].metadata if x.key == "itemTrack"), None)
        self.assertEquals(item_track.value, "A1")

    def test_transform_shape_to_lta_file_subtitle(self):
        file = transform_shape_to_lta_files(self.test_subtitle_ttml_shape)[0]
        self.assertEquals(file.id, "VX-62_VX-14")
        self.assertEquals(file.type, "SUBTITLE")
        self.assertEquals(file.url, "/APInoauth/storage/VX-1/file/VX-4/0.08703483378792176/VX-4.ttml")
        # Container
        self.assertEquals(file.container.format, "ttml")

    def test_extract_marker_groups(self):
        marker_groups = transform_subclips_to_marker_groups(self.test_item)
        self.assertEqual(len(marker_groups), 1)
        self.assertEqual(marker_groups[0].title, "Manual")
        self.assertEqual(len(marker_groups[0].markerTracks), 1)

        marker_track = marker_groups[0].markerTracks[0]
        self.assertEqual(marker_track.title, "Video issues")
        self.assertEqual(len(marker_track.markers), 1)

        marker = marker_track.markers[0]
        self.assertEqual(marker.start.frame, 3147)
        self.assertEqual(marker.start.numerator, 25)
        self.assertEqual(marker.start.denominator, 1)
        self.assertEqual(marker.end.frame, 3148)
        self.assertEqual(marker.end.numerator, 25)
        self.assertEqual(marker.end.denominator, 1)

        name_field = next((field for field in marker.metadata if field.key == "name"), None)
        self.assertIsNotNone(name_field, "Metadata field with key 'name' not found")
        self.assertEqual(name_field.value, "Artifact")

        description_field = next((field for field in marker.metadata if field.key == "description"), None)
        self.assertIsNotNone(description_field, "Metadata field with key 'description' not found")
        self.assertEqual(description_field.value, "Freeze frame")

class TestTransformVideoComponentNoFramerate(PortalBaseTestCase):

    def setUp(self, mock_authenticate=True):
        super().setUp(mock_authenticate=mock_authenticate)
        super(TestTransformVideoComponentNoFramerate, self).setUp()
        self.test_item = VSItem(**self.read_json("vsitem2.json"))
        self.test_video_proxy_shape = self.test_item.getShapes()[0]
        self.test_video_original_shape = self.test_item.getShapes()[1]

    def test_transform_item_to_lta_asset(self):
        asset = transform_item_to_lta_asset(self.test_item)
        # Asset
        self.assertEqual(asset.id, "VX-21")
        self.assertGreater(len(asset.files), 0)
        self.assertEqual(asset.metadata[0].key, "title")
        self.assertEqual(asset.metadata[0].value, "Item with video and image")


    def test_transform_video_shape_to_lta_file(self):
        file = transform_shape_to_lta_files(self.test_video_proxy_shape)[0]
        # File
        self.assertEquals(file.id, "VX-27")
        self.assertEquals(file.type, "VIDEO")

        self.assertEqual(file.metadata[0].key, "tag")
        self.assertEqual(file.metadata[0].value, "lowres")
        # Container
        self.assertEquals(file.container.format, "video/mp4")
        self.assertEquals(file.container.startTime.frame, 0)
        self.assertEquals(file.container.startTime.numerator, 24)
        self.assertEquals(file.container.startTime.denominator, 1)
        # Video streams
        self.assertEquals(len(file.container.videoStreams), 1)
        print(file.container.videoStreams[0])
        self.assertEquals(file.container.videoStreams[0].frameRateNumerator, 24000)
        self.assertEquals(file.container.videoStreams[0].frameRateDenominator, 1001)
        self.assertEquals(file.container.videoStreams[0].timeBaseNumerator, 1)
        self.assertEquals(file.container.videoStreams[0].timeBaseDenominator, 90000)
        self.assertEquals(file.container.videoStreams[0].resolutionWidth, 1280)
        self.assertEquals(file.container.videoStreams[0].resolutionHeight, 720)
        self.assertEquals(file.container.videoStreams[0].codec, "h264")
        self.assertEquals(file.container.videoStreams[0].aspectRatioWidth, 16)
        self.assertEquals(file.container.videoStreams[0].aspectRatioHeight, 9)
        self.assertEquals(file.container.videoStreams[0].duration, 345330)
        self.assertEquals(file.container.videoStreams[0].bitrate, 2480478)
        self.assertEquals(len(file.container.videoStreams[0].metadata), 7)
        # Audio streams
        self.assertEqual(len(file.container.audioStreams), 1)
        self.assertEquals(file.container.audioStreams[0].channels, 2)
        self.assertEquals(file.container.audioStreams[0].timeBaseNumerator, 1)
        self.assertEquals(file.container.audioStreams[0].timeBaseDenominator, 44100)
        self.assertEquals(file.container.audioStreams[0].sampleRate, 44100)
        self.assertEquals(file.container.audioStreams[0].codec, "aac")
        self.assertEquals(file.container.audioStreams[0].bitrate, 131474)
        self.assertEquals(file.container.audioStreams[0].duration, 158010)
        self.assertEquals(len(file.container.audioStreams[0].metadata), 6)
        item_track = next((x for x in file.container.audioStreams[0].metadata if x.key == "itemTrack"), None)
        self.assertEquals(item_track.value, "A1")
