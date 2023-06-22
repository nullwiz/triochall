import pytest
import requests
from api import bootstrap, config
from api.adapters import notifications
from api.domain import commands, enums
from api.service_layer import unit_of_work


@pytest.fixture()
def bus(sqlite_session_factory):
    bus = bootstrap.bootstrap(
        start_orm=False,
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
async def test_cancelled_order_email(bus, db_state_dict_sqlite):
    state = db_state_dict_sqlite
    order_id = state["orders"][0]["id"]
    user_id = state["users"][1]["id"]
    result = await bus.handle(
        commands.CancelOrder(order_id=order_id, user_id=user_id)
    )
    assert result[1] == "Order cancelled successfully"
    assert result[0] is True
    email = get_last_mailhog_email()
    assert email["Raw"]["From"] == "test@example.com"
    assert email["Raw"]["To"] == ["customer@example.com"]
    assert (
        f"Your order status is updated to Cancelled"
        in email["Content"]["Headers"]["Subject"][0]
    )
