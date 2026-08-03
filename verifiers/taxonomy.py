from __future__ import annotations

import enum
from dataclasses import dataclass


class Layer(str, enum.Enum):
    SCHEMA = "schema"
    SCORE = "score"
    SECURITY = "security"
    POLICY = "policy"
    QUALITY = "quality"
    CROSS_REF = "cross_ref"


@dataclass(frozen=True)
class Concern:
    id: str
    layer: Layer
    description: str
