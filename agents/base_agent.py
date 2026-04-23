"""Base class for all agents."""

from __future__ import annotations
from abc import ABC, abstractmethod
from a2a.message import A2AMessage
from a2a.protocol import A2AProtocol


class BaseAgent(ABC):
    """Every agent has a name, registers on the A2A bus, and handles messages."""

    def __init__(self, name: str, protocol: A2AProtocol):
        self.name = name
        self.protocol = protocol
        self.protocol.register(self.name, self.handle_message)

    @abstractmethod
    def handle_message(self, message: A2AMessage):
        """Process an incoming A2A message."""
        ...

    def send_to(self, receiver: str, payload: dict, msg_type: str = "data"):
        """Helper to send a message to another agent."""
        msg = A2AMessage(
            sender=self.name,
            receiver=receiver,
            payload=payload,
            msg_type=msg_type,
        )
        return self.protocol.send(msg)
