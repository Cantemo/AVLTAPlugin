from portal.externals.VidiRest.objects.item import VSItem
from portal.utils.test_case import PortalBaseTestCase
from ..transform import transform_shape_to_lta_files, transform_item_to_lta_asset


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

    def test_transform_item_thumbnails(self):
        asset = transform_item_to_lta_asset(self.test_item)

        thumbnails = [file for file in asset.files if file.type == "STILL_FRAME"]
        self.assertGreater(len(thumbnails), 0)
        self.assertEquals(thumbnails[0].url,
                          "/APInoauth/thumbnail/VX-2/VX-1;version=0/0@PAL?hash=2708d1da27db2bafd356887d87425603")
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
        self.assertEquals(file.container.startTime.numerator, 1)
        self.assertEquals(file.container.startTime.denominator, 25)
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
