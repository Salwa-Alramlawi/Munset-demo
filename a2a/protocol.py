"""A2A Protocol — message bus that routes messages between agents and keeps a full log."""

from __future__ import annotations
from collections import defaultdict
from typing import Callable, Any
from .message import A2AMessage


class A2AProtocol:
    """Publish/subscribe message bus for agent-to-agent communication with
    support for clarification requests, feedback loops, and bidirectional messaging."""

    def __init__(self):
        self._subscribers: dict[str, Callable[[A2AMessage], Any]] = {}
        self._log: list[dict] = []
        self._message_store: dict[str, A2AMessage] = {}  # msg_id → message for lookups
        self._stats: dict[str, dict] = defaultdict(lambda: {"sent": 0, "received": 0, "clarifications": 0, "feedbacks": 0})

    # -- registration --
    def register(self, agent_name: str, handler: Callable[[A2AMessage], Any]):
        """Register an agent's message handler."""
        self._subscribers[agent_name] = handler

    # -- sending --
    def send(self, message: A2AMessage) -> Any:
        """Send a message to the target agent and return its response."""
        self._log.append(message.to_dict())
        self._message_store[message.msg_id] = message

        # Update stats
        self._stats[message.sender]["sent"] += 1
        self._stats[message.receiver]["received"] += 1
        if message.msg_type == "clarification_request":
            self._stats[message.sender]["clarifications"] += 1
        elif message.msg_type == "feedback":
            self._stats[message.sender]["feedbacks"] += 1

        handler = self._subscribers.get(message.receiver)
        if handler is None:
            raise ValueError(f"Agent '{message.receiver}' is not registered.")

        result = handler(message)

        # Log the response if the handler returns an A2AMessage
        if isinstance(result, A2AMessage):
            self._log.append(result.to_dict())
            self._message_store[result.msg_id] = result

        return result

    # -- clarification --
    def request_clarification(self, from_agent: str, to_agent: str, question: str, context_msg_id: str | None = None) -> A2AMessage:
        """Allow an agent to request clarification from a previous agent in the pipeline."""
        msg = A2AMessage(
            sender=from_agent,
            receiver=to_agent,
            payload={"clarification_question": question, "context_msg_id": context_msg_id},
            msg_type="clarification_request",
            parent_id=context_msg_id,
            priority="high",
        )
        return self.send(msg)

    # -- feedback --
    def send_feedback(self, from_agent: str, to_agent: str, feedback: str, severity: str = "info", context_msg_id: str | None = None) -> A2AMessage:
        """Send quality feedback from a downstream agent to an upstream agent."""
        msg = A2AMessage(
            sender=from_agent,
            receiver=to_agent,
            payload={"feedback": feedback, "severity": severity, "context_msg_id": context_msg_id},
            msg_type="feedback",
            parent_id=context_msg_id,
        )
        return self.send(msg)

    # -- introspection --
    def get_log(self) -> list[dict]:
        """Return the full message log (useful for demo visualization)."""
        return list(self._log)

    def get_agent_messages(self, agent_name: str) -> list[dict]:
        """Return messages involving a specific agent."""
        return [
            m for m in self._log
            if m["sender"] == agent_name or m["receiver"] == agent_name
        ]

    def get_message(self, msg_id: str) -> A2AMessage | None:
        """Retrieve a message by ID (for tracing conversations)."""
        return self._message_store.get(msg_id)

    def get_conversation_chain(self, msg_id: str) -> list[dict]:
        """Trace the full conversation chain from a message back to its root."""
        chain = []
        current_id = msg_id
        while current_id:
            msg = self._message_store.get(current_id)
            if msg is None:
                break
            chain.append(msg.to_dict())
            current_id = msg.parent_id
        return list(reversed(chain))

    def get_stats(self) -> dict:
        """Return communication statistics per agent."""
        return dict(self._stats)

    def summary(self) -> str:
        """Human-readable summary of all A2A traffic."""
        lines = []
        for m in self._log:
            priority_tag = f" [!{m.get('priority', 'normal')}]" if m.get("priority", "normal") != "normal" else ""
            lines.append(
                f"[{m['timestamp']}] {m['sender']} → {m['receiver']} "
                f"({m['msg_type']}{priority_tag}) id={m['msg_id']}"
            )
        return "\n".join(lines)
