from sdkscan.cli import app
from sdkscan.core import Sdks, scan


def main() -> None:
    app()


__all__ = ["Sdks", "scan"]
