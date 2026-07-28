"""Kernel événementiel asynchrone, sans boucle active."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol


class EventType(str, Enum):
    """Événements autorisés par l'architecture cible."""

    USER_MESSAGE = "USER_MESSAGE"
    QUESTION_ANSWERED = "QUESTION_ANSWERED"
    LEARNING_REQUESTED = "LEARNING_REQUESTED"
    CONSOLIDATION_REQUESTED = "CONSOLIDATION_REQUESTED"
    SKILL_TEST_FINISHED = "SKILL_TEST_FINISHED"
    PROCESS_FINISHED = "PROCESS_FINISHED"
    SCHEDULED_REVIEW = "SCHEDULED_REVIEW"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    STOP = "STOP"


@dataclass(frozen=True, slots=True)
class Event:
    """Message immuable transporté par la file du kernel."""

    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class EventComponent(Protocol):
    """Contrat minimal d'un composant abonné."""

    async def handle(self, event: Event) -> Any: ...


class EventKernel:
    """Attend la file asyncio et délègue sans interpréter les contenus."""

    def __init__(self) -> None:
        """Initialise une file bloquante et un registre d'abonnements."""

        self.queue: asyncio.Queue[Event] = asyncio.Queue()
        self.handlers: dict[EventType, EventComponent] = {}
        self.running = False
        self.audit: list[dict[str, Any]] = []

    def register(self, event_type: EventType, component: EventComponent) -> None:
        """Associe explicitement un type à un composant unique."""

        self.handlers[event_type] = component

    async def emit(self, event: Event) -> None:
        """Ajoute un événement sans déclencher de traitement concurrent caché."""

        await self.queue.put(event)

    async def run(self) -> None:
        """Bloque sur queue.get et s'arrête uniquement avec l'événement STOP."""

        self.running = True
        while self.running:
            event = await self.queue.get()
            try:
                if event.type == EventType.STOP:
                    self.running = False
                    self.audit.append({"event": event.type.value, "status": "success"})
                    continue
                component = self.handlers.get(event.type)
                if component is None:
                    raise LookupError(f"Aucun composant pour {event.type.value}")
                result = await component.handle(event)
                self.audit.append(
                    {"event": event.type.value, "status": "success", "result": result}
                )
            except Exception as error:
                self.audit.append(
                    {"event": event.type.value, "status": "failure",
                     "error": f"{type(error).__name__}: {error}"}
                )
            finally:
                self.queue.task_done()
