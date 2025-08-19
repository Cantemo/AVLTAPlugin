from dataclasses import dataclass, field
from typing import List, Optional, Dict, Literal


@dataclass
class MetadataField:
    key: str
    value: str


@dataclass
class Timecode:
    frame: int
    numerator: int
    denominator: int


@dataclass
class VideoStream:
    frameRateNumerator: Optional[int] = None
    frameRateDenominator: Optional[int] = None
    timeBaseNumerator: Optional[int] = None
    timeBaseDenominator: Optional[int] = None
    duration: Optional[int] = None
    resolutionWidth: Optional[int] = None
    resolutionHeight: Optional[int] = None
    aspectRatioWidth: Optional[int] = None
    aspectRatioHeight: Optional[int] = None
    metadata: List[MetadataField] = field(default_factory=list)
    bitrate: Optional[int] = None
    codec: Optional[str] = None


@dataclass
class AudioStream:
    timeBaseNumerator: Optional[int] = None
    timeBaseDenominator: Optional[int] = None
    duration: Optional[int] = None
    sampleRate: Optional[int] = None
    channels: Optional[int] = None
    metadata: List[MetadataField] = field(default_factory=list)
    bitrate: Optional[int] = None
    codec: Optional[str] = None


@dataclass
class SubtitleStream:
    metadata: List[MetadataField] = field(default_factory=list)


@dataclass
class Container:
    format: Optional[str] = None
    startTime: Optional[Timecode] = None
    videoStreams: List[VideoStream] = field(default_factory=list)
    audioStreams: List[AudioStream] = field(default_factory=list)
    subtitleStreams: List[SubtitleStream] = field(default_factory=list)


FileType = Literal["VIDEO", "AUDIO", "SUBTITLE", "STILL_FRAME", "SPRITE_MAP", "WAVEFORM", "MISC"]

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
    "application/ttml+xml": "ttml",
    "text/vtt": "vtt"
}

MIME_TO_FORMAT = {} | SUBTITLE_MIMES


@dataclass
class File:
    url: str
    id: Optional[str]
    fileName: Optional[str]
    container: Optional[Container]
    type: Optional[FileType]
    _type: Optional[FileType] = field(init=False, repr=False)
    metadata: Optional[List[MetadataField]] = field(default_factory=list)

    @property
    def type(self) -> Optional[FileType]:
        if self._type is not None:
            return self._type
        return self.__get_inferred_type()

    @type.setter
    def type(self, value: Optional[FileType]):
        self._type = value

    def __get_inferred_type(self) -> FileType:
        if self.container:
            if len(self.container.videoStreams) > 0:
                return "VIDEO"
            elif len(self.container.audioStreams) > 0:
                return "AUDIO"
            elif self.__is_subtitle():
                return "SUBTITLE"
        return "MISC"

    def __is_subtitle(self) -> bool:
        if self.container and self.container.format in list(SUBTITLE_MIMES.values()):
            return True
        if self.fileName.lower().endswith(tuple(SUPPORTED_SUBTITLE_EXTENTIONS)):
            return True
        return False


@dataclass
class CallerAccess:
    read: bool
    write: bool


@dataclass
class Marker:
    start: Timecode
    end: Timecode
    metadata: List[MetadataField]


@dataclass
class MarkerTrack:
    title: str
    markers: List[Marker] = field(default_factory=list)


@dataclass
class MarkerGroup:
    title: str
    markerTracks: List[MarkerTrack]


@dataclass
class Asset:
    id: Optional[str]
    metadata: Optional[List[MetadataField]]
    files: List[File]
    callerAccess: Optional[CallerAccess]
    markerGroups: Optional[List[MarkerGroup]]


@dataclass
class Data:
    assets: List[Asset]


@dataclass
class HttpEndpoint:
    url: str
    method: Literal["GET", "POST", "PUT", "DELETE"]
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class Endpoint:
    download: Optional[bool] = None
    http: Optional[HttpEndpoint] = None


@dataclass
class Endpoints:
    publish: Optional[Endpoint] = None


@dataclass
class WaveformSettingsVidispine:
    apiBaseUrl: Optional[str] = None
    shape: Optional[str] = None
    tag: Optional[str] = None
    sampleMin: Optional[int] = None
    sampleMax: Optional[int] = None


@dataclass
class WaveformsSettings:
    active: Optional[str] = None
    vidispine: Optional[WaveformSettingsVidispine] = None
    requestDebounceTimeMs: Optional[int] = None


@dataclass
class TimelineSettings:
    waveforms: Optional[WaveformsSettings] = None


@dataclass
class Settings:
    licenseKey: Optional[str] = None
    timeline: Optional[TimelineSettings] = None


@dataclass
class LaunchTemplate:
    data: Data
    endpoints: Optional[Endpoints] = None
    settings: List[Settings] = field(default_factory=list)
