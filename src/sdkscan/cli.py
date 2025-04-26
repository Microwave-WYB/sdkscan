from pathlib import Path
from sdkscan.core import Sdks
import typer

app = typer.Typer()


@app.command()
def scan(file: Path = typer.Argument(..., help="Path to the APK file to scan")) -> None:
    sdks = Sdks.from_apk(file)
    for sdk in sdks:
        typer.echo(sdk.name)
