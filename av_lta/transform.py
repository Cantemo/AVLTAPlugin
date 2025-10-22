import logging
from itertools import chain
from typing import Optional

from portal.externals.VidiRest.objects.item import SubClip
from portal.externals.VidiRest.objects.item import VSACLMerged
from portal.externals.VidiRest.objects.item import VSItem
from portal.externals.VidiRest.objects.item import VSThumbnail
from portal.externals.VidiRest.objects.shape import VSAudioComponent
from portal.externals.VidiRest.objects.shape import VSBinaryComponent
from portal.externals.VidiRest.objects.shape import VSComponentBase
from portal.externals.VidiRest.objects.shape import VSObject
from portal.externals.VidiRest.objects.shape import VSShape
from portal.externals.VidiRest.objects.shape import VSSubtitleComponent
from portal.externals.VidiRest.objects.shape import VSVideoComponent
from portal.utils.general import get_site_domain
from Timecode.timecode import Timecode as PortalTimecode

from ...externals.VidiRest.objects.storage import VSFile  # type: ignore
from .lta_types import MIME_TO_FORMAT
from .lta_types import Asset
from .lta_types import AudioStream
from .lta_types import CallerAccess
from .lta_types import Container
from .lta_types import File
from .lta_types import Marker
from .lta_types import MarkerGroup
from .lta_types import MarkerTrack
from .lta_types import MetadataField
from .lta_types import SubtitleStream
from .lta_types import Timecode
from .lta_types import VideoStream

log = logging.getLogger(__name__)


def transform_items_to_lta_assets(items: list[VSItem], force_full_domain=False) -> list[Asset]:
    return [transform_item_to_lta_asset(item=item, force_full_domain=force_full_domain) for item in items]


def transform_item_to_lta_asset(item: VSItem, force_full_domain=False) -> Asset:
    asset_id = item.json_object["id"]

    marker_groups = transform_subclips_to_marker_groups(item=item)

    title = item.getTitle()

    metadata: list[MetadataField] = [MetadataField(key="title", value=title)]

    files = list(
        chain.from_iterable(
            [
                transform_shape_to_lta_files(shape=shape, force_full_domain=force_full_domain)
                for shape in item.getShapes()
            ]
        )
    )

    thumbnails = [
        _transform_thumbnail_to_lta_still_frame_file(
            thumbnail=thumbnail, item=item, index=index, force_full_domain=force_full_domain
        )
        for [index, thumbnail] in enumerate(item.getThumbnailObjects())
    ]

    acl = item.getACLMerged()

    if acl is not None:
        caller_access = CallerAccess(read=acl.hasGenericReadPermission(), write=acl.hasGenericWritePermission())
    else:
        caller_access = None

    return Asset(
        id=asset_id, files=files + thumbnails, metadata=metadata, callerAccess=caller_access, markerGroups=marker_groups
    )


def transform_subclips_to_marker_groups(item: VSItem) -> list[MarkerGroup]:
    subclips_grouped_by_track_id: dict = {}
    for subclip in _get_subclips_by_group_name(group_name="AvMarker", item=item):
        track_id = subclip.getFieldByName(field_name="av_marker_track_id")
        if not track_id:
            continue
        subclips_grouped_by_track_id.setdefault(track_id, []).append(subclip)

    track_mappings = {
        "av:track:video:issues": "Video issues",
        "av:track:audio:issues": "Audio issues",
        "av:track:subtitle:issues": "Subtitle issues",
        "av:track:other": "Other",
    }
    marker_tracks = [
        MarkerTrack(
            title=title,
            markers=[
                transform_subclip_to_lta_marker(subclip) for subclip in subclips_grouped_by_track_id.get(track_id, [])
            ],
        )
        for track_id, title in track_mappings.items()
        if subclips_grouped_by_track_id.get(track_id, [])
    ]

    if not marker_tracks:
        return []

    return [
        MarkerGroup(
            title="Manual",
            markerTracks=marker_tracks,
        )
    ]


def _get_subclips_by_group_name(group_name: str, item: VSItem) -> list[SubClip]:
    return [
        subclip
        for subclip in item.getAnnotationsFromMetadataDocument(item.json_object["metadata"])
        if subclip.getMetadataFieldGroupName() == group_name
    ]


def transform_subclip_to_lta_marker(subclip: SubClip) -> Marker:
    metadata_mappings = {
        "name": "title",
        "description": "av_marker_description",
    }

    metadata = [
        MetadataField(key=key, value=value)
        for key, field_name in metadata_mappings.items()
        if (value := subclip.getFieldByName(field_name))
    ]

    return Marker(
        start=transform_portal_timecode_to_lta_timecode(subclip.getStartTimecode()),
        end=transform_portal_timecode_to_lta_timecode(subclip.getEndTimecode()),
        metadata=metadata,
    )


def transform_portal_timecode_to_lta_timecode(timecode: PortalTimecode) -> Timecode:
    return Timecode(
        frame=timecode.frames, numerator=timecode.fpsAsFraction()[0], denominator=timecode.fpsAsFraction()[1]
    )


def transform_shape_to_lta_files(shape: VSShape, force_full_domain=False) -> list[File]:
    files: list[File] = []
    video_components = shape.getVideoComponents()
    audio_components = shape.getAudioComponents()
    subtitle_components = shape.getSubtitleComponents()
    container_component = shape.getContainerComponent()
    binary_components = shape.getBinaryComponents()
    video_vs_files = list(chain.from_iterable([video_component.getFiles() for video_component in video_components]))

    # Shapes may have multiple audio components, one file per component
    for audio_component in audio_components:
        if _is_same_files(video_vs_files, audio_component.getFiles()):
            # This component belongs to the video, continue
            continue
        files.append(
            _tranform_audio_component_to_audio_file(
                audio_component=audio_component,
                shape=shape,
                force_full_domain=force_full_domain,
            )
        )

    # Shapes may have multiple subtitle files, one file per component
    for subtitle_or_binary_component in subtitle_components + binary_components:
        if _is_same_files(video_vs_files, subtitle_or_binary_component.getFiles()):
            # This component belongs to the video, continue
            continue
        files.append(
            _tranform_subtitle_or_binary_component_to_file(
                subtitle_or_binary_component=subtitle_or_binary_component,
                shape=shape,
                force_full_domain=force_full_domain,
            )
        )

    if len(video_components) == 0:
        return files

    container = Container(videoStreams=[], audioStreams=[], subtitleStreams=[], format=_get_container_format(shape))

    # start time
    start_time_code = container_component.getStartTimecode()
    time_code_numerator, time_code_denominator = container_component.getTimeCodeTimeBase()
    if None not in [start_time_code, time_code_numerator, time_code_denominator]:
        container.startTime = Timecode(
            frame=start_time_code, numerator=time_code_denominator, denominator=time_code_numerator
        )

    for video_component in video_components:
        if video_component.getFramerateAsFraction():
            container.videoStreams.append(_transform_video_component_to_video_stream(video_component))

    for audio_component in audio_components:
        container.audioStreams.append(_transform_audio_component_to_audio_stream(audio_component))

    for subtitle_component in subtitle_components + binary_components:
        container.subtitleStreams.append(_tranform_subtitle_component_to_subtitle_stream(subtitle_component))

    metadata: list[MetadataField] = []
    metadata += [MetadataField(key="tag", value=tag) for tag in shape.getTags()]

    files.append(
        File(
            id=shape.getId(),
            type=None,
            fileName=get_filename(video_vs_files),
            url=_get_url(video_vs_files, shape=shape, force_full_domain=force_full_domain) or "",
            container=container,
            metadata=metadata,
        )
    )

    return files


def _is_same_files(a: list[VSFile], b: list[VSFile]) -> bool:
    if len(a) != len(b):
        return False
    for i in range(len(a)):
        if a[i].getId() != b[i].getId():
            return False
    return True


def _tranform_subtitle_or_binary_component_to_file(
    subtitle_or_binary_component: VSBinaryComponent | VSSubtitleComponent, shape: VSShape, force_full_domain=False
) -> File:
    file_id = f"{shape.getId()}_{subtitle_or_binary_component.getId()}"
    vs_files = subtitle_or_binary_component.getFiles()
    container = Container(videoStreams=[], audioStreams=[], subtitleStreams=[], format=_get_container_format(shape))

    return File(
        id=file_id,
        type=None,
        fileName=get_filename(vs_files),
        url=_get_url(vs_files, shape=shape, force_full_domain=force_full_domain) or "",
        metadata=_get_metadatas(subtitle_or_binary_component),
        container=container,
    )


def _get_container_format(shape: VSShape) -> str:
    mime_type = shape.getMimeType()
    return MIME_TO_FORMAT.get(mime_type, mime_type)


def _tranform_audio_component_to_audio_file(
    audio_component: VSAudioComponent, shape: VSShape, force_full_domain=False
) -> File:
    file_id = f"{shape.getId()}_{audio_component.getId()}"
    vs_files = audio_component.getFiles()
    container = Container(
        videoStreams=[],
        audioStreams=[_transform_audio_component_to_audio_stream(audio_component)],
        subtitleStreams=[],
    )
    metadata = _get_metadatas(audio_component)
    item_track = audio_component.getItemTrack()
    if item_track is not None:
        metadata.append(MetadataField(key="itemTrack", value=item_track))
    return File(
        id=file_id,
        type=None,
        fileName=get_filename(vs_files),
        url=_get_url(vs_files, shape=shape, force_full_domain=force_full_domain) or "",
        metadata=metadata,
        container=container,
    )


def get_filename(files: list[VSFile]) -> str:
    file_names: dict[int, str] = {}

    for file in files:
        path = file.getPath()
        if not path or path.strip() == "":
            file_names[1001] = path
            continue
        elif 1000 not in file_names:
            file_names[1000] = path

        upper_path = path.upper()
        if upper_path.endswith(".MP4"):
            file_names[1] = path
        elif upper_path.endswith(".WEBM"):
            file_names[2] = path
        elif upper_path.endswith(".ADTS"):
            file_names[3] = path
        elif upper_path.endswith(".MP3"):
            file_names[4] = path
        elif upper_path.endswith(".WAV"):
            file_names[5] = path

    return file_names.get(min(file_names.keys()), "")


def _get_url(files: list[VSFile], shape: VSShape, force_full_domain=True) -> str | None:
    for file in files:
        uri = file.getURI(method="https") or file.getURI(method="http")
        url = _get_preview_url(shape, uri, force_full_domain=force_full_domain)
        if uri is not None:
            return url
    return None


def _transform_video_component_to_video_stream(video_component: VSVideoComponent) -> VideoStream:
    video_stream = VideoStream()
    frame_rate = video_component.getFramerateAsFraction()
    video_stream.frameRateNumerator = frame_rate["numerator"]
    video_stream.frameRateDenominator = frame_rate["denominator"]
    video_stream.timeBaseNumerator, video_stream.timeBaseDenominator = video_component.getTimeBase()
    video_stream.resolutionWidth = video_component.getResolutionWidth()
    video_stream.resolutionHeight = video_component.getResolutionHeight()
    video_stream.codec = video_component.getCodec()
    video_stream.bitrate = video_component.getBitRate()
    duration = _get_duration(video_component)
    if duration is not None:
        video_stream.duration = duration
    video_stream.aspectRatioWidth, video_stream.aspectRatioHeight = video_component.getAspectRatio(asString=False)
    video_stream.metadata = _get_metadatas(video_component)
    return video_stream


def _transform_audio_component_to_audio_stream(audio_component: VSAudioComponent) -> AudioStream:
    audio_stream = AudioStream()
    audio_stream.timeBaseNumerator, audio_stream.timeBaseDenominator = audio_component.getTimeBase()
    audio_stream.sampleRate = int(audio_component.getSamplingRate())
    audio_stream.channels = audio_component.getChannels()
    audio_stream.codec = audio_component.getCodec()
    audio_stream.bitrate = audio_component.getBitRate()
    duration = _get_duration(audio_component)
    if duration is not None:
        audio_stream.duration = duration
    audio_stream.metadata = _get_metadatas(audio_component)
    item_track = audio_component.getItemTrack()
    if item_track is not None:
        audio_stream.metadata.append(MetadataField(key="itemTrack", value=item_track))
    return audio_stream


def _tranform_subtitle_component_to_subtitle_stream(subtitle_component: VSComponentBase) -> SubtitleStream:
    subtitle_stream = SubtitleStream()
    subtitle_stream.metadata = _get_metadatas(subtitle_component)
    return subtitle_stream


def _get_preview_url(vs_object: VSObject, uri: str | None, force_full_domain=False) -> str | None:
    if uri is None:
        return uri
    url = vs_object.replace_url(uri)
    if force_full_domain and not url.startswith("http"):
        url = get_site_domain() + url
    return url


def _get_duration(component: VSComponentBase) -> Optional[int]:
    try:
        return component.json_object["duration"]["samples"]
    except (KeyError, TypeError):
        return None


def _get_metadatas(component: VSComponentBase) -> list[MetadataField]:
    return [MetadataField(key=x["key"], value=x["value"]) for x in component.json_object.get("metadata", [])]


def _transform_thumbnail_to_lta_still_frame_file(
    thumbnail: VSThumbnail, item: VSItem, index: int, force_full_domain=False
) -> File:
    asset_id = item.json_object["id"]
    return File(
        id=f"{asset_id}-thumbnail-{index}",
        fileName=f"thumbnail-{index}",
        type="STILL_FRAME",
        url=_get_preview_url(item, thumbnail.url, force_full_domain=force_full_domain) or "",
        container=None,
        metadata=[MetadataField(key="still_frame:timestamp", value=thumbnail.timecode.toVidispine())],
    )
