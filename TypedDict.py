from typing import TypedDict, List, Dict, Literal, Union, Optional


class VersionInfo(TypedDict):
    id: str
    type: str
    url: str
    time: str
    releaseTime: str
    sha1: str
    complianceLevel: int


class AssetIndexInfo(TypedDict):
    id: str
    sha1: str
    size: int
    totalSize: int
    url: str


class DownloadInfo(TypedDict):
    sha1: str
    size: int
    url: str


class Downloads(TypedDict):
    client: DownloadInfo
    server: Optional[DownloadInfo]
    client_mappings: Optional[DownloadInfo]
    server_mappings: Optional[DownloadInfo]


class LibraryDownloadsArtifact(TypedDict):
    path: str
    sha1: str
    size: int
    url: str


class LibraryDownloadsClassifiers(TypedDict, total=False):
    natives_linux: LibraryDownloadsArtifact
    natives_osx: LibraryDownloadsArtifact
    natives_windows: LibraryDownloadsArtifact
    natives_macos: LibraryDownloadsArtifact
    natives_macos_arm64: LibraryDownloadsArtifact
    natives_windows_arm64: LibraryDownloadsArtifact
    natives_windows_x86: LibraryDownloadsArtifact


class LibraryDownloads(TypedDict, total=False):
    artifact: LibraryDownloadsArtifact
    classifiers: LibraryDownloadsClassifiers


class LibraryRuleOS(TypedDict, total=False):
    name: str
    version: str
    arch: str


class LibraryRule(TypedDict):
    action: Literal["allow", "disallow"]
    os: Optional[LibraryRuleOS]
    features: Optional[Dict[str, bool]]


class LibraryExtract(TypedDict):
    exclude: List[str]


class LibraryNatives(TypedDict, total=False):
    linux: str
    osx: str
    windows: str
    macos: str
    macos_arm64: str
    windows_arm64: str
    windows_x86: str


class Library(TypedDict, total=False):
    downloads: LibraryDownloads
    name: str
    rules: List[LibraryRule]
    extract: LibraryExtract
    natives: LibraryNatives


class JavaVersion(TypedDict, total=False):
    component: str
    majorVersion: int


class LoggingFile(TypedDict):
    id: str
    sha1: str
    size: int
    url: str


class LoggingConfig(TypedDict):
    argument: str
    file: LoggingFile
    type: str


class Logging(TypedDict):
    client: LoggingConfig


class ArgumentValue(TypedDict, total=False):
    rules: List[LibraryRule]
    value: Union[str, List[str]]


class Arguments(TypedDict):
    game: List[Union[str, ArgumentValue]]
    jvm: List[Union[str, ArgumentValue]]


class VersionJsonInfo(TypedDict, total=False):
    assetIndex: AssetIndexInfo
    assets: str
    complianceLevel: Optional[int]
    downloads: Downloads
    id: str
    javaVersion: Optional[JavaVersion]
    libraries: List[Library]
    mainClass: str
    minecraftArguments: Optional[str]
    arguments: Optional[Arguments]
    minimumLauncherVersion: int
    releaseTime: str
    time: str
    type: Literal['release', 'snapshot', 'old_alpha', 'old_beta']
    logging: Optional[Logging]
