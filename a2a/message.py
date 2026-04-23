"""A2A Message — the data unit exchanged between agents."""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class A2AMessage:
    sender: str
    receiver: str
    payload: dict[str, Any]
    msg_type: str = "data"  # data | request | response | error | clarification_request | clarification_response | feedback
    msg_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    parent_id: str | None = None  # for chaining / tracing
    priority: str = "normal"  # low | normal | high | critical

    def to_dict(self) -> dict:
        return {
            "msg_id": self.msg_id,
            "parent_id": self.parent_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "msg_type": self.msg_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "priority": self.priority,
        }

    def reply(self, payload: dict[str, Any], sender: str) -> A2AMessage:
        """Create a reply message linked to this one."""
        return A2AMessage(
            sender=sender,
            receiver=self.sender,
            payload=payload,
            msg_type="response",
            parent_id=self.msg_id,
        )

    def clarification_request(self, question: str, sender: str, target: str) -> A2AMessage:
        """Request clarification from another agent (back-and-forth communication)."""
        return A2AMessage(
            sender=sender,
            receiver=target,
            payload={"clarification_question": question, "original_msg_id": self.msg_id},
            msg_type="clarification_request",
            parent_id=self.msg_id,
            priority="high",
        )

    def feedback(self, feedback_text: str, sender: str, target: str, severity: str = "info") -> A2AMessage:
        """Send feedback to a previous agent about quality issues."""
        return A2AMessage(
            sender=sender,
            receiver=target,
            payload={
                "feedback": feedback_text,
                "severity": severity,  # info | warning | error
                "original_msg_id": self.msg_id,
            },
            msg_type="feedback",
            parent_id=self.msg_id,
        )
