import pytest
import requests
from api import bootstrap, config
from api.domain import enums
from api.adapters import notifications
from api.domain import commands, models
from api.service_layer import unit_of_work


@pytest.fixture()
def bus(sqlite_session_factory):
    bus = bootstrap.bootstrap(
        start_orm=True,
        uow=unit_of_work.SqlAlchemyUnitOfWork(sqlite_session_factory),
        notifications=notifications.EmailLocalNotifications(),
        publish=lambda *args: None,
    )
    yield bus


def get_last_mailhog_email():
    host = config.get_mailhog_host()
    port = 8025
    all_emails = requests.get(f"http://{host}:{port}/api/v2/messages").json()
    return all_emails["items"][0]


@pytest.mark.asyncio
async def test_order_created_email(bus, db_state_dict_sqlite):
    state = db_state_dict_sqlite
    user_id = state["users"][1]["id"]
    result = await bus.handle(
        commands.CreateOrder(
            consume_location=enums.ConsumeLocation.IN_HOUSE,
            user_id=user_id,
            order_items=[
                {
                    "product_id": state["products"][0]["id"],
                    "variation_id": state["variations"][0]["id"],
                    "quantity": 1,
                }
            ],
        )
    )
    assert isinstance(result, models.Order)
