"""Shared primitives for every contract.

Rule: money is always an integer in minor units (cents) plus a 3-letter currency code.
Field names are snake_case so the generated OpenAPI and the frontend types stay aligned.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Id = Annotated[str, StringConstraints(min_length=1)]
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
Cents = Annotated[int, Field(ge=0)]
IsoDateTime = datetime


class Contract(BaseModel):
    """Base for all contracts: unknown fields are errors, so drift is caught early."""

    model_config = ConfigDict(extra="forbid")
