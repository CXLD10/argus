"""F-000 smoke tests: package importable, CLI works, version consistent."""

import re

from typer.testing import CliRunner

import argus
from argus.cli import app

runner = CliRunner()


def test_package_importable() -> None:
    assert argus.__version__ is not None


def test_version_is_semver() -> None:
    assert re.match(r"^\d+\.\d+\.\d+", argus.__version__)


def test_version_command_exits_zero() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0


def test_version_command_prints_version() -> None:
    result = runner.invoke(app, ["version"])
    assert argus.__version__ in result.output


def test_help_exits_zero() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
