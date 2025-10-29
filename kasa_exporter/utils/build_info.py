"""Build information utility for capturing git hash and version."""

import subprocess
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


def get_git_hash() -> str:
    """
    Get the current git commit hash (short 8-char version).

    Returns:
        Short git hash (8 chars) or "unknown" if git is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        git_hash = result.stdout.strip()
        logger.info("git_hash_detected", git_hash=git_hash)
        return git_hash
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning("git_hash_unavailable", error=str(e))
        return "unknown"


def get_version() -> str:
    """
    Get the application version from pyproject.toml.

    Returns:
        Version string (e.g., "0.2.0") or "unknown" if not found.
    """
    try:
        # Look for pyproject.toml in the project root
        project_root = Path(__file__).parent.parent.parent
        pyproject_path = project_root / "pyproject.toml"

        if pyproject_path.exists():
            content = pyproject_path.read_text()
            # Simple parsing - look for version = "x.y.z" in [tool.poetry] section
            for line in content.splitlines():
                if line.strip().startswith("version ="):
                    # Extract version from: version = "0.2.0"
                    version = line.split("=")[1].strip().strip('"').strip("'")
                    logger.info("version_detected", version=version)
                    return version

        logger.warning("version_not_found_in_pyproject")
        return "unknown"
    except Exception as e:
        logger.warning("version_read_error", error=str(e))
        return "unknown"


# Module-level constants computed once at import time
VERSION = get_version()
GIT_HASH = get_git_hash()
