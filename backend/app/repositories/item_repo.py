from app.db.models import Item
from app.db.oracle_client import get_session


def get_item(item_id: int) -> Item | None:
    with get_session() as session:
        return session.get(Item, item_id)


def list_items(item_type: str | None = None, limit: int = 50) -> list[Item]:
    with get_session() as session:
        query = session.query(Item)
        if item_type is not None:
            query = query.filter(Item.item_type == item_type)
        return query.limit(limit).all()
