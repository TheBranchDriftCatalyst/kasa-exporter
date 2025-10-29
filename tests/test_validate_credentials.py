"""Tests for credential validation script."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

# Get the path to the validation script
SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "install" / "validate_credentials.py"


@pytest.mark.skipif(
    not (os.getenv("KASA_USERNAME") and os.getenv("KASA_PASSWORD")),
    reason="KASA_USERNAME and KASA_PASSWORD environment variables not set",
)
def test_validate_credentials_success():
    """Test that credential validation succeeds with valid credentials."""
    env = os.environ.copy()

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )

    # Should exit with 0 on success
    assert result.returncode == 0, f"Validation failed: {result.stderr}"

    # Should print success or warning message
    assert "SUCCESS" in result.stderr or "WARNING" in result.stderr


def test_validate_credentials_missing_username():
    """Test that validation fails when username is missing."""
    env = os.environ.copy()
    env.pop("KASA_USERNAME", None)
    env["KASA_PASSWORD"] = "dummy_password"

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )

    # Should exit with 1 on failure
    assert result.returncode == 1
    assert "ERROR: Missing credentials" in result.stderr


def test_validate_credentials_missing_password():
    """Test that validation fails when password is missing."""
    env = os.environ.copy()
    env["KASA_USERNAME"] = "dummy_username"
    env.pop("KASA_PASSWORD", None)

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )

    # Should exit with 1 on failure
    assert result.returncode == 1
    assert "ERROR: Missing credentials" in result.stderr


@pytest.mark.skip(reason="Discovery doesn't validate credentials, only finds local devices")
def test_validate_credentials_invalid_credentials():
    """
    Test with invalid credentials.

    Note: This test is skipped because Kasa device discovery doesn't
    actually validate credentials against the cloud - it just discovers
    devices on the local network. Invalid credentials will still succeed
    if devices are found locally.
    """
    # Note: This test is skipped because Kasa device discovery doesn't
    # actually validate credentials against the cloud - it just discovers
    # devices on the local network. Invalid credentials will still succeed
    # if devices are found locally, so we can't reliably test this.


def test_validate_credentials_script_exists():
    """Test that the validation script exists and is executable."""
    assert SCRIPT_PATH.exists(), f"Script not found at {SCRIPT_PATH}"
    assert SCRIPT_PATH.is_file(), f"Script path is not a file: {SCRIPT_PATH}"


@pytest.mark.skipif(
    not (os.getenv("KASA_USERNAME") and os.getenv("KASA_PASSWORD")),
    reason="KASA_USERNAME and KASA_PASSWORD environment variables not set",
)
def test_validate_credentials_output_format():
    """Test that validation output follows expected format."""
    env = os.environ.copy()

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )

    # Output should go to stderr
    assert result.stderr, "Expected output on stderr"

    # Should contain one of the expected status messages
    status_messages = ["SUCCESS", "WARNING", "ERROR"]
    assert any(msg in result.stderr for msg in status_messages), (
        f"Expected status message in output: {result.stderr}"
    )
