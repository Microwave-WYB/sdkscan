# sdkscan

Simple tool to detect SDKs used in Android apps

## Installation

### As CLI Tool only

```bash
# with pipx
pipx install git+https://github.com/Microwave-WYB/sdkscan.git

# with uv
uv tool install git+https://github.com/Microwave-WYB/sdkscan.git
```

### As Python Module and CLI Tool

```bash
# with pip
pip install git+https://github.com/Microwave-WYB/sdkscan.git

# with uv
uv pip install git+https://github.com/Microwave-WYB/sdkscan.git
```

## Usage

You can use this module as a CLI tool or as a Python module. Both .apk and .xapk files are supported.

### As CLI Tool

Simply run the `sdkscan` command, with the path to the APK or XAPK file.

```bash
sdkscan example.apk
ANDROID_KOTLIN
REACT_NATIVE

# xapk is also supported
sdkscan example.xapk
ANDROID_KOTLIN
FLUTTER
```

### As Python Module

```python
from sdkscan import Sdks

sdks = Sdks.from_apk('example.apk')
for sdk in sdks:
    print(sdk.name)
```
