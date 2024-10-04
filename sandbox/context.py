from typing import Optional

from pydantic import BaseModel

from sandbox.config import Settings


class CliContext(BaseModel, arbitrary_types_allowed=True):
    settings: Optional[Settings] = None
