"""Persistence of the single-row career library (table `profile`)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Session, select

from postulo.db.models import Profile, utcnow
from postulo.db.session import get_engine
from postulo.services.profile.schema import CareerProfile


class StoredProfile(BaseModel):
    version: int
    updated_at: datetime | None
    profile: CareerProfile


class VersionConflictError(Exception):
    """The profile changed since the client loaded it (another tab, an import...)."""

    def __init__(self, current_version: int) -> None:
        super().__init__(f"Profile version is {current_version}")
        self.current_version = current_version


def _row(session: Session) -> Profile | None:
    return session.exec(select(Profile).order_by(Profile.id)).first()  # type: ignore[arg-type]


def get_profile() -> StoredProfile:
    """Return the stored profile, or an empty one (version 0) before the first save."""
    with Session(get_engine()) as session:
        row = _row(session)
        if row is None:
            return StoredProfile(version=0, updated_at=None, profile=CareerProfile())
        return StoredProfile(
            version=row.version,
            updated_at=row.updated_at,
            profile=CareerProfile.model_validate(row.data),
        )


def save_profile(profile: CareerProfile, *, expected_version: int | None = None) -> StoredProfile:
    """Replace the profile. With `expected_version`, refuse to overwrite a newer version."""
    with Session(get_engine()) as session:
        row = _row(session)
        current_version = row.version if row else 0
        if expected_version is not None and expected_version != current_version:
            raise VersionConflictError(current_version)
        data = profile.model_dump(mode="json")
        if row is None:
            row = Profile(data=data, version=1, updated_at=utcnow())
        else:
            row.data = data
            row.version = current_version + 1
            row.updated_at = utcnow()
        session.add(row)
        session.commit()
        session.refresh(row)
        return StoredProfile(version=row.version, updated_at=row.updated_at, profile=profile)
