import pytest
from api.domain import models, enums
from datetime import datetime
from api.domain.events import Event


@pytest.fixture
def user_data():
    return {
        "email": "test@test.com",
        "password": "test",
        "role": enums.UserRole.MANAGER,
    }


def test_user_creation(user_data):
    user = models.User(**user_data)
    assert user.email == user_data["email"]
    assert user.password == user_data["password"]
    assert user.role == user_data["role"]
    assert isinstance(user.id, str)  # ID should be auto-generated
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)


def test_user_append_event(user_data):
    user = models.User(**user_data)
    event = Event()
    user.append_event(event)
    assert len(user._events) == 1
    assert user._events[0] == event


def test_user_pop_events(user_data):
    user = models.User(**user_data)
    event = Event()
    user.append_event(event)
    popped_events = user.pop_events()
    assert len(user._events) == 0
    assert popped_events == [event]
