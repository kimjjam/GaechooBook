from app.db.models import UserTasteProfile
from app.db.oracle_client import get_session


def get_latest_profile() -> UserTasteProfile | None:
    with get_session() as session:
        return (
            session.query(UserTasteProfile)
            .order_by(UserTasteProfile.updated_at.desc())
            .first()
        )


def create_profile(**fields) -> UserTasteProfile:
    with get_session() as session:
        profile = UserTasteProfile(**fields)
        session.add(profile)
        session.commit()
        session.refresh(profile)
        return profile


def update_profile(profile_id: int, **fields) -> UserTasteProfile | None:
    with get_session() as session:
        profile = session.get(UserTasteProfile, profile_id)
        if profile is None:
            return None
        for key, value in fields.items():
            setattr(profile, key, value)
        session.commit()
        session.refresh(profile)
        return profile
