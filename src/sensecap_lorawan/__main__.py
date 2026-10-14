"""Discover SenseCAP devices and print their readings."""

from lorawan_connection.cli_helper import run

from . import SenseCapDeviceCollection


def main() -> None:
    """Run the SenseCAP command-line interface."""
    run(SenseCapDeviceCollection.DEVICES)


if __name__ == "__main__":
    main()
