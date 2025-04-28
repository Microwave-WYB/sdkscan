import io
import re
import zipfile
from enum import IntFlag, auto
from pathlib import Path

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
    KMP = auto()
    REACT_NATIVE = auto()
    FLUTTER = auto()
    DOTNET = auto()
    XAMARIN = auto()
    MAUI = auto()
    CORDOVA = auto()
    IONIC = auto()


def is_android_dalvik(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r"\.dex$", name))


def is_android_kotlin(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r"^kotlin/", name))


def is_kmp(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r".*\.knm", name))


def is_react_native(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r".*index\.android\.bundle", name))


def is_flutter(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r"^lib/.*/libflutter\.so", name))


def is_dotnet(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(
        re.search(r"^lib/.*/libmono.*\.so", name)
        or re.search(r"^assemblies/assemblies\.blob", name)
    )


def is_xamarin(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r"^lib/.*/libxamarin-app\.so", name))


def is_maui(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r"^lib/.*Microsoft.Maui.*\.so", name))


def is_cordova(zip_file: zipfile.ZipFile, name: str) -> bool:
    return bool(re.search(r"^assets/www/cordova\.js", name))


def is_ionic(zip_file: zipfile.ZipFile, name: str) -> bool:
    if not re.search(r"^assets/www/manifest\.js", name):
        return False

    try:
        content = zip_file.read(name).decode("utf-8")
        return "Ionic" in content
    except (UnicodeDecodeError, KeyError):
        return False


def is_xapk(file: io.BytesIO | Path | str) -> bool:
    with zipfile.ZipFile(file) as zip_file:
        return "manifest.json" in zip_file.namelist()


def scan(file_path: io.BytesIO | Path | str) -> Sdks:
    # If this is an XAPK, extract the base APK and scan that instead
    if is_xapk(file_path):
        with zipfile.ZipFile(file_path) as xapk:
            manifest_data = xapk.read("manifest.json")
            manifest = XAPKManifest.model_validate_json(manifest_data)
            base_apk = manifest.base_apk
            if base_apk is None:
                return Sdks(0)
            return scan(io.BytesIO(xapk.read(base_apk)))

    # Map of detector functions to their respective SdkStack flags
    detectors = {
        Sdks.ANDROID_DALVIK: is_android_dalvik,
        Sdks.ANDROID_KOTLIN: is_android_kotlin,
        Sdks.KMP: is_kmp,
        Sdks.REACT_NATIVE: is_react_native,
        Sdks.FLUTTER: is_flutter,
        Sdks.DOTNET: is_dotnet,
        Sdks.XAMARIN: is_xamarin,
        Sdks.MAUI: is_maui,
        Sdks.CORDOVA: is_cordova,
        Sdks.IONIC: is_ionic,
    }

    # Start with no SDKs detected
    detected_sdks = Sdks(0)

    with zipfile.ZipFile(file_path) as zip_file:
        file_list = zip_file.namelist()

        # Scan through all files in the zip
        for name in file_list:
            for sdk, detector in detectors.items():
                # Skip if we've already detected this SDK
                if sdk in detected_sdks:
                    continue

                # Run the detector, passing it the zip_file and filename
                if detector(zip_file, name):
                    detected_sdks |= sdk
    return detected_sdks
