import json
import sys
from collections.abc import Iterable
from pathlib import Path

import typer

from sdkscan.core import scan as scan_apk

app = typer.Typer()


@app.command()
def scan(
    files: list[Path] = typer.Argument(
        help="Paths to the APK files to scan", exists=True, dir_okay=False
    ),
    stdin: bool = typer.Option(False, "--stdin", help="Read APK file paths from stdin"),
):
    file_iterable: Iterable[Path] = files if not stdin else map(Path, sys.stdin.readlines())
    for path, sdks in zip(file_iterable, map(scan_apk, file_iterable)):
        print(json.dumps({"path": str(path), "sdks": [sdk.name for sdk in sdks]}))
