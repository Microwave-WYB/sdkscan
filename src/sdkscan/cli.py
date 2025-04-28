from pathlib import Path
import zipfile
from sdkscan.core import scan as scan_apk
import typer


app = typer.Typer()


@app.command()
def scan(file: Path = typer.Argument(help="Path to the APK file to scan")) -> None:
    try:
        sdks = scan_apk(file)
    except zipfile.BadZipFile as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    for sdk in sdks:
        typer.echo(sdk.name)
