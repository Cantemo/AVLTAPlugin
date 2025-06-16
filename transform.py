import logging
from typing import Optional

from portal.externals.VidiRest.objects.item import VSItem, VSThumbnail
from portal.externals.VidiRest.objects.shape import VSObject, VSShape, VSComponentBase
from portal.utils.general import get_site_domain
from .lta_types import Asset, File, FileType, Container, VideoStream, AudioStream, SubtitleStream, MetadataField, \
    Timecode

log = logging.getLogger(__name__)

SUPPORTED_SUBTITLE_EXTENTIONS = [
    ".cap",
    ".fpc",
    ".imsc",
    ".itt",
    ".pac",
    ".scc",
    ".srt",
    ".stl",
    ".ttml",
    ".vtt"
]

SUBTITLE_MIMES = {
    "application/ttml": "ttml",
    "application/ttml+xml": "ttml"
}

MIME_TO_FORMAT = {} | SUBTITLE_MIMES


def transform_items_to_lta_assets(items: list[VSItem], force_site_domain=False) -> list[Asset]:
    return [transform_item_to_lta_asset(item=item, force_site_domain=force_site_domain) for item in items]


def transform_item_to_lta_asset(item: VSItem, force_site_domain=False) -> Asset:
    asset_id = item.json_object["id"]

    title = item.getTitle()

    metadata: list[MetadataField] = [MetadataField(key="title", value=title)]

    files = [transform_shape_to_lta_file(shape=shape, force_site_domain=force_site_domain) for shape in
             item.getShapes()]

    thumbnails = [
        _transform_thumbnail_to_lta_still_frame_file(
            thumbnail=thumbnail,
            item=item,
            index=index,
            force_site_domain=force_site_domain) for [index, thumbnail] in
        enumerate(item.getThumbnailObjects())]

    return Asset(
        id=asset_id,
        files=files + thumbnails,
        metadata=metadata
    )


def transform_shape_to_lta_file(shape: VSShape, force_site_domain=False) -> Optional[File]:
    video_components = shape.getVideoComponents()
    audio_components = shape.getAudioComponents()
    subtitle_components = shape.getSubtitleComponents()
    container_component = shape.getContainerComponent()
    binary_components = shape.getBinaryComponents()
    file_id = shape.getId()
    file_type = _get_inferred_type(shape)
    url: str | None = None

    container = Container(
        videoStreams=[],
        audioStreams=[],
        subtitleStreams=[],
        format=_get_container_format(shape)
    )

    # start time
    start_time_code = container_component.getStartTimecode()
    time_code_numerator, time_code_denominator = container_component.getTimeCodeTimeBase()
    if None not in [start_time_code, time_code_numerator, time_code_denominator]:
        container.startTime = Timecode(
            frame=start_time_code,
            numerator=time_code_numerator,
            denominator=time_code_denominator
        )

    for file in shape.getAllFiles():
        uri = file.getURI(method="https") or file.getURI(method="http")
        url = _get_preview_url(shape, uri, force_site_domain=force_site_domain)
        if uri is not None:
            break

    for video_component in video_components:
        video_stream = VideoStream()
        frame_rate = video_component.getFramerateAsFraction()
        video_stream.frameRateNumerator = frame_rate["numerator"]
        video_stream.frameRateDenominator = frame_rate["denominator"]
        video_stream.timeBaseNumerator, video_stream.timeBaseDenominator = video_component.getTimeBase()
        video_stream.resolutionWidth = video_component.getResolutionWidth()
        video_stream.resolutionHeight = video_component.getResolutionHeight()
        video_stream.codec = video_component.getCodec()
        video_stream.bitrate = video_component.getBitRate()
        video_stream.duration = _get_duration(video_component)
        video_stream.aspectRatioWidth, video_stream.aspectRatioHeight = video_component.getAspectRatio(asString=False)
        video_stream.metadata = _get_metadatas(video_component)
        container.videoStreams.append(video_stream)

    for audio_component in audio_components:
        audio_stream = AudioStream()
        audio_stream.timeBaseNumerator, audio_stream.timeBaseDenominator = audio_component.getTimeBase()
        audio_stream.sampleRate = int(audio_component.getSamplingRate())
        audio_stream.channels = audio_component.getChannels()
        audio_stream.codec = audio_component.getCodec()
        audio_stream.bitrate = audio_component.getBitRate()
        audio_stream.duration = _get_duration(audio_component)
        audio_stream.metadata = _get_metadatas(audio_component)
        container.audioStreams.append(audio_stream)

    for subtitle_component in subtitle_components:
        subtitle_stream = SubtitleStream()
        subtitle_stream.metadata = _get_metadatas(subtitle_component)
        container.subtitleStreams.append(subtitle_stream)

    metadata: list[MetadataField] = []
    metadata += [MetadataField(key="tag", value=tag) for tag in shape.getTags()]

    if file_type == "SUBTITLE":
        for binary_component in binary_components:
            subtitle_stream = SubtitleStream()
            subtitle_stream.metadata = _get_metadatas(binary_component)
            container.subtitleStreams.append(subtitle_stream)

    return File(
        id=file_id,
        fileName=shape.getFirstFileName(),
        type=file_type,
        url=url,
        container=container,
        metadata=metadata
    )


def _get_inferred_type(shape: VSShape) -> FileType:
    video_components = shape.getVideoComponents()
    audio_components = shape.getAudioComponents()
    # Process video components
    if len(video_components) > 0:
        return "VIDEO"
    if len(audio_components) > 0:
        return "AUDIO"
    if _is_subtitle(shape):
        return "SUBTITLE"
    return "UNKNOWN"


def _is_subtitle(shape: VSShape) -> bool:
    if shape.getMimeType() in SUBTITLE_MIMES:
        return True
    if shape.getFirstFileName().lower().endswith(tuple(SUPPORTED_SUBTITLE_EXTENTIONS)):
        return True
    return False


def _get_container_format(shape: VSShape) -> str:
    mime_type = shape.getMimeType()
    return MIME_TO_FORMAT.get(mime_type, mime_type)


def _get_preview_url(vs_object: VSObject, uri: str | None, force_site_domain=False) -> str | None:
    if uri is None:
        return uri
    url = vs_object.replace_url(uri)
    if force_site_domain and not url.startswith("http"):
        url = get_site_domain() + url
    return url


def _get_duration(component: VSComponentBase) -> Optional[float]:
    try:
        return component.json_object["duration"]["samples"]
    except (KeyError, TypeError):
        return None


def _get_metadatas(component: VSComponentBase) -> list[MetadataField]:
    return [MetadataField(key=x["key"], value=x["value"]) for x in component.json_object.get("metadata", [])]


def _transform_thumbnail_to_lta_still_frame_file(thumbnail: VSThumbnail, item: VSItem, index: int,
                                                 force_site_domain=False) -> File:
    asset_id = item.json_object["id"]
    return File(
        id=f"{asset_id}-thumbnail-{index}",
        fileName=f"thumbnail-{index}",
        type="STILL_FRAME",
        url=_get_preview_url(item, thumbnail.url, force_site_domain=force_site_domain),
        container=None,
        metadata=[
            MetadataField(key="still_frame:timestamp", value=thumbnail.timecode.toVidispine())
        ]
    )
