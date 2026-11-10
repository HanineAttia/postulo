"""Fictional sample profile ("Camille Exemple") for the demo mode (SPEC 6.2)."""

from __future__ import annotations

import json
from importlib import resources

from postulo.services.profile.schema import CareerProfile


def sample_profile() -> CareerProfile:
    """Return the sample profile with fresh item ids."""
    text = resources.files("postulo").joinpath("data/sample_profile.json").read_text("utf-8")
    return CareerProfile.model_validate(json.loads(text))
