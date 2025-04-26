from enum import IntFlag, auto
import re
from functools import partial, reduce
from pathlib import Path
from collections.abc import Callable
import io
import zipfile
from pydantic import BaseModel

# Takes path, returns True if SDK is detected
type SdkDetectorFn = Callable[[io.BytesIO | Path | str], bool]


class XAPKManifest(BaseModel):
    class APK(BaseModel):
        file: str
        id: str

    xapk_version: int
    package_name: str
    name: str
    version_code: str
    version_name: str
    min_sdk_version: str
    target_sdk_version: str
    permissions: list[str]
    split_configs: list[str]
    total_size: int
    icon: str
    split_apks: list[APK]

    @property
    def base_apk(self) -> str | None:
        return next((apk.file for apk in self.split_apks if apk.id == "base"), None)


def has_file(zip_binary: io.BytesIO | Path | str, target_regex: str) -> bool:
    with zipfile.ZipFile(zip_binary) as zip_file:
        return any(
            filter(
                lambda x: re.search(target_regex, str(x)),
                zip_file.namelist(),
            )
        )


def has_content(zip_binary: io.BytesIO | Path | str, target_regex: str, content_regex: str) -> bool:
    with zipfile.ZipFile(zip_binary) as zip_file:
        matching_files = list(
            filter(
                lambda x: re.search(target_regex, str(x)),
                zip_file.namelist(),
            )
        )

        if not matching_files:
            return False

        try:
            for file in matching_files:
                if re.search(content_regex, zip_file.read(file).decode("utf-8")):
                    return True
            return False
        except (KeyError, UnicodeDecodeError):
            return False


is_xapk = partial(has_file, target_regex="^manifest.json")


def support_xapk(fn: SdkDetectorFn) -> SdkDetectorFn:
    def wrapper(file: io.BytesIO | Path | str) -> bool:
        if not is_xapk(file):
            return fn(file)

        with zipfile.ZipFile(file) as xapk:
            return (
                False
                if (
                    base_apk := XAPKManifest.model_validate_json(
                        xapk.read("manifest.json")
                    ).base_apk
                )
                is None
                else wrapper(io.BytesIO(xapk.read(base_apk)))
            )

    return wrapper


is_kotlin = support_xapk(
    partial(has_file, target_regex=r"^kotlin/"),
)
is_react_native = support_xapk(
    partial(has_file, target_regex=r".*index\.android\.bundle"),
)
is_flutter = support_xapk(
    partial(has_file, target_regex=r"^lib/.*/libflutter\.so"),
)
is_dotnet = support_xapk(
    partial(has_file, target_regex=r"^lib/.*/libmono.*\.so"),
)
is_xamarin = support_xapk(
    partial(has_file, target_regex=r"^lib/.*/libxamarin-app\.so"),
)
is_cordova = support_xapk(
    partial(has_file, target_regex=r"^assets/www/cordova\.js"),
)
is_ionic = support_xapk(
    partial(has_content, target_regex=r"^assets/www/manifest\.js", content_regex=r"Ionic"),
)


class Sdks(IntFlag):
    ANDROID_KOTLIN = auto()
    REACT_NATIVE = auto()
    FLUTTER = auto()
    DOTNET = auto()
    XAMARIN = auto()
    CORDOVA = auto()
    IONIC = auto()

    @staticmethod
    def get_detector() -> dict["Sdks", Callable[[io.BytesIO | Path | str], bool]]:
        return {
            Sdks.ANDROID_KOTLIN: is_kotlin,
            Sdks.REACT_NATIVE: is_react_native,
            Sdks.FLUTTER: is_flutter,
            Sdks.DOTNET: is_dotnet,
            Sdks.XAMARIN: is_xamarin,
            Sdks.CORDOVA: is_cordova,
            Sdks.IONIC: is_ionic,
        }

    @classmethod
    def from_apk(cls, apk: io.BytesIO | Path | str) -> "Sdks":
        detected_sdks = {sdk for sdk, detector in Sdks.get_detector().items() if detector(apk)}

        # Return the combined flags or 0 if none detected
        return reduce(lambda x, y: x | y, detected_sdks) if detected_sdks else cls(0)
