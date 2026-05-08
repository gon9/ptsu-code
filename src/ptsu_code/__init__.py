"""PTSU - AI Agent CLI tool."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ptsu-code")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
