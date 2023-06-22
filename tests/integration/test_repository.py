import pytest
from api.adapters import repository
from api.domain import models


@pytest.mark.asyncio
async def test_get_order_by_id(sqlite_session_factory):
    session = sqlite_session_factory()
    order_id = "123"
    order = models.Order(
        id=order_id,
        consume_location=models.ConsumeLocation.IN_HOUSE,
        user_id="123",
        order_items=[
            models.OrderItem(
                order_id="123",
                product_id="123",
                variation_id="123",
                quantity=2,
                unit_price=10.0,
            )
        ],
        total_cost=20.0,
    )
    repo = repository.SqlAlchemyOrderRepository(session)
    await repo.add(order)
    await session.commit()
    result = await repo.get(order_id)
    assert result == order
    await session.close()
