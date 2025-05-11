from functools import reduce
import io
import re
import itertools
import zipfile
from enum import IntFlag, auto
from pathlib import Path
from collections.abc import Callable

from pydantic import BaseModel


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


class Sdks(IntFlag):
    ANDROID_DALVIK = auto()
    ANDROID_KOTLIN = auto()
    KOTLIN_MULTI_PLATFORM = auto()
    REACT_NATIVE = auto()
    FLUTTER = auto()
    DOTNET = auto()
    XAMARIN = auto()
    MAUI = auto()
    CORDOVA = auto()
    IONIC = auto()
    TITANIUM = auto()
    QT = auto()
    UNITY = auto()
    UNREAL_ENGINE = auto()


class SdkDetectors(dict[Sdks, Callable[[zipfile.ZipFile, str], bool]]):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SdkDetectors, cls).__new__(cls)
        return cls._instance

    @staticmethod
    def register(
        sdks: Sdks,
    ) -> Callable[[Callable[[zipfile.ZipFile, str], bool]], Callable[[zipfile.ZipFile, str], bool]]:
        def decorator(
            func: Callable[[zipfile.ZipFile, str], bool],
        ) -> Callable[[zipfile.ZipFile, str], bool]:
            SdkDetectors()[sdks] = func
            return func

        return decorator


@SdkDetectors.register(Sdks.ANDROID_DALVIK)
def is_android_dalvik(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r"\.dex$", name))


@SdkDetectors.register(Sdks.ANDROID_KOTLIN)
def is_android_kotlin(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r"^kotlin/", name))


@SdkDetectors.register(Sdks.KOTLIN_MULTI_PLATFORM)
def is_kmp(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r".*\.knm", name))


@SdkDetectors.register(Sdks.REACT_NATIVE)
def is_react_native(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r".*index\.android\.bundle", name))


@SdkDetectors.register(Sdks.FLUTTER)
def is_flutter(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r"^lib/.*/libflutter\.so", name))


@SdkDetectors.register(Sdks.DOTNET)
def is_dotnet(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(
        re.search(r"^lib/.*/libmono.*\.so", name)
        or re.search(r"^assemblies/assemblies\.blob", name)
    )


@SdkDetectors.register(Sdks.XAMARIN)
def is_xamarin(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r"^lib/.*/libxamarin-app\.so", name))


@SdkDetectors.register(Sdks.MAUI)
def is_maui(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r"^lib/.*/.*Microsoft.Maui.*\.so", name))


@SdkDetectors.register(Sdks.CORDOVA)
def is_cordova(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r"^assets/www/cordova\.js", name))


@SdkDetectors.register(Sdks.IONIC)
def is_ionic(zip_file: zipfile.ZipFile, name: str) -> bool:
    if not re.search(r"^assets/www/manifest\.js", name):
        return False

    try:
        content = zip_file.read(name).decode("utf-8")
        return "Ionic" in content
    except UnicodeDecodeError:
        return False


@SdkDetectors.register(Sdks.TITANIUM)
def is_titanium(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(
        re.search(r"^lib/.*/libti\..*\.so", name)
        or name in ("assets/Resources/ti.kernel.js.bin", "assets/Resources/ti.main.js.bin")
    )


@SdkDetectors.register(Sdks.QT)
def is_qt(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r"^lib/.*/libQt.*\.so", name))


@SdkDetectors.register(Sdks.UNITY)
def is_unity(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(
        re.search(r"^lib/.*/libunity\.so", name)
        or name == "assets/bin/Data/Resources/unity_builtin_extra"
    )


@SdkDetectors.register(Sdks.UNREAL_ENGINE)
def is_unreal_engine(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(
        re.search(r"^lib/.*/libUE\d+\.so", name)  # Match libUE4.so, libUE5.so, etc.
    )


def scan(file_path: io.BytesIO | Path | str) -> Sdks:
    with zipfile.ZipFile(file_path) as zip_file:
        if "manifest.json" in zip_file.namelist():
            manifest = XAPKManifest.model_validate_json(zip_file.read("manifest.json"))
            return reduce(
                lambda x, y: x | y,
                (scan(io.BytesIO(zip_file.read(apk.file))) for apk in manifest.split_apks),
            )

        detected_sdks = Sdks(0)
        for name, (sdk, detector) in itertools.product(zip_file.namelist(), SdkDetectors().items()):
            if sdk not in detected_sdks and detector(zip_file, name):
                detected_sdks |= sdk
        return detected_sdks
