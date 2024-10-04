from __future__ import annotations

from pathlib import Path
from functools import wraps

from loguru import logger

from sandbox.exceptions import Abort


cache_dir: Path = Path.home() / ".local/share/sandbox"


def init_cache(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            cache_dir.mkdir(exist_ok=True, parents=True)
            info_file = cache_dir / "info.txt"
            info_file.write_text("This directory is used by Sandbox CLI for its cache.")
        except Exception:
            raise Abort(
                """
                Cache directory {cache_dir} doesn't exist, is not writable, or could not be created.

                Please check your home directory permissions and try again.
                """,
                subject="Non-writable cache dir",
                log_message="Non-writable cache dir",
            )
        return func(*args, **kwargs)

    return wrapper
