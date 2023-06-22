import inspect
from typing import Awaitable, Callable
import os
from api.adapters import orm, redis_eventpublisher
from api.adapters.notifications import (
    AbstractNotifications,
    EmailLocalNotifications,
    EmailAWSNotifications,
)
from api.domain import events
from api.service_layer import handlers, messagebus, unit_of_work
import logging

logger = logging.getLogger(__name__)


def bootstrap(
    uow: unit_of_work.AbstractUnitOfWork = None,
    notifications: AbstractNotifications = None,
    start_orm: bool = True,
    publish: Callable[
        [str, events.Event, dict], Awaitable
    ] = redis_eventpublisher.publish,
) -> messagebus.MessageBus:
    if notifications is None:
        environment = os.getenv("NOTIFICATIONS_ENV", "dev")
        if environment == "production":
            notifications = EmailAWSNotifications()
        else:
            notifications = EmailLocalNotifications()
    # Here we could switch configs. i.e pymongo
    if not uow:
        if os.getenv("UOW") == "sqlalchemy":
            logger.info("Starting ORM")
            uow = unit_of_work.SqlAlchemyUnitOfWork()
            logger.info("Using UOW: %s", uow.__class__)
            print("Using UOW: %s", uow.__class__)
            if start_orm and orm.has_started_mappers() is False:
                orm.start_mappers()
        else:  # We are doing the same, as it's an example.
            logger.info("Starting ORM")
            uow = unit_of_work.SqlAlchemyUnitOfWork()
            logger.info("Using UOW: %s", uow.__class__)
            print("Using UOW: %s", uow.__class__)
            if start_orm and orm.has_started_mappers() is False:
                orm.start_mappers()

    dependencies = {
        "uow": uow,
        "notifications": notifications,
        "publish": publish,
    }

    injected_event_handlers = {
        event_type: [
            inject_dependencies(handler, dependencies)
            for handler in event_handlers
        ]
        for event_type, event_handlers in handlers.EVENT_HANDLERS.items()
    }
    injected_command_handlers = {
        command_type: inject_dependencies(handler, dependencies)
        for command_type, handler in handlers.COMMAND_HANDLERS.items()
    }

    return messagebus.MessageBus(
        uow=uow,
        event_handlers=injected_event_handlers,
        command_handlers=injected_command_handlers,
    )


def inject_dependencies(handler, dependencies):
    params = inspect.signature(handler).parameters
    deps = {
        name: dependency
        for name, dependency in dependencies.items()
        if name in params
    }
    return lambda message: handler(message, **deps)
