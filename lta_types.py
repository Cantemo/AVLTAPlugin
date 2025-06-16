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


FileType = Literal["VIDEO", "AUDIO", "SUBTITLE", "STILL_FRAME", "SPRITE_MAP", "WAVEFORM", "UNKNOWN"]


@dataclass
class File:
    id: Optional[str]
    fileName: Optional[str]
    type: FileType
    url: str
    container: Optional[Container]
    metadata: Optional[List[MetadataField]] = field(default_factory=list)


@dataclass
class Asset:
    id: Optional[str]
    metadata: Optional[List[MetadataField]]
    files: List[File]


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
class Data:
    assets: List[Asset]
    markerGroups: List[MarkerGroup] = field(default_factory=list)


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
class Settings:
    licenseKey: Optional[str] = None


@dataclass
class LaunchTemplate:
    data: Data
    endpoints: Optional[Endpoints] = None
    settings: Optional[Settings] = None
