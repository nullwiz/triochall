from __future__ import annotations
import logging
from typing import TYPE_CHECKING, List, Union, Type, Dict, Callable
from typing import Any, Awaitable
from api.domain import commands, events

if TYPE_CHECKING:
    from . import unit_of_work

logger = logging.getLogger(__name__)

Message = Union[commands.Command, events.Event]


class MessageBus:
    def __init__(
        self,
        uow: unit_of_work.AbstractUnitOfWork,
        event_handlers: Dict[
            Type[events.Event], List[Callable[[Any], Awaitable]]
        ],
        command_handlers: Dict[
            Type[commands.Command], Callable[[Any], Awaitable]
        ],
    ):
        self.uow = uow
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers

    async def handle(self, message: Message):
        self.command_queue = [message]
        self.event_queue = []
        result = None
        while self.command_queue:
            message = self.command_queue.pop(0)
            if isinstance(message, commands.Command):
                result = await self.handle_command(message)
            else:
                raise Exception(f"{message} was not an Event or Command")
        while self.event_queue:
            message = self.event_queue.pop(0)
            if isinstance(message, events.Event):
                await self.handle_event(message)
            else:
                raise Exception(f"{message} was not an Event or Command")
        return result

    async def handle_event(self, event: events.Event):
        for handler in self.event_handlers[type(event)]:
            try:
                logger.debug(f"Handling event {event} with handler {handler}")
                await handler(event)
                self.event_queue.extend(self.uow.collect_new_events())
            except Exception:
                logger.exception(f"Exception handling event {event}")
                continue

    async def handle_command(self, command: commands.Command):
        logger.debug(f"Handling command {command}")
        try:
            handler = self.command_handlers[type(command)]
            result = await handler(command)
            self.event_queue.extend(self.uow.collect_new_events())
            return result
        except Exception:
            logger.exception(f"Exception handling command {command}")
            raise
