from app.db.models import Interaction
from app.db.oracle_client import get_session


def create_interaction(item_id: int, action: str, rating: float | None = None) -> Interaction:
    with get_session() as session:
        interaction = Interaction(item_id=item_id, action=action, rating=rating)
        session.add(interaction)
        session.commit()
        session.refresh(interaction)
        return interaction


def list_interactions_for_item(item_id: int) -> list[Interaction]:
    with get_session() as session:
        return (
            session.query(Interaction)
            .filter(Interaction.item_id == item_id)
            .order_by(Interaction.created_at.desc())
            .all()
        )
