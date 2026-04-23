"""Agent 5 — Chatbot Agent: interactive Q&A over the session content."""

from __future__ import annotations
import json
import anthropic

from a2a.message import A2AMessage
from a2a.protocol import A2AProtocol
from .base_agent import BaseAgent
import config

SYSTEM_PROMPT = """أنت مساعد ذكي متخصص في الجلسات القضائية.
لديك إمكانية الوصول إلى:
- النص الكامل المُفرّغ للجلسة
- التحليل القانوني
- محضر الجلسة المُنتَج

أجب على أسئلة المستخدم (قاضي أو محامي) بدقة بناءً على المعلومات المتوفرة فقط.
إذا لم تكن المعلومة موجودة في البيانات، قل ذلك بوضوح.
كن مختصراً ودقيقاً. استخدم لغة قانونية مهنية."""


class ChatbotAgent(BaseAgent):
    """Interactive Q&A chatbot over session data."""

    def __init__(self, protocol: A2AProtocol):
        super().__init__("chatbot_agent", protocol)
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.session_data: dict | None = None
        self.conversation_history: list[dict] = []

    def set_session_data(self, transcript: str, legal_analysis: dict, summary: str):
        """Load session data for Q&A context."""
        self.session_data = {
            "transcript": transcript,
            "legal_analysis": legal_analysis,
            "summary": summary,
        }
        self.conversation_history = []

    def ask(self, question: str) -> str:
        """Answer a question about the current session."""
        if not self.session_data:
            return "لم يتم تحميل بيانات الجلسة بعد."

        analysis_text = json.dumps(
            self.session_data["legal_analysis"], ensure_ascii=False, indent=2
        )

        context = (
            f"## النص المُفرّغ:\n{self.session_data['transcript']}\n\n"
            f"## التحليل القانوني:\n{analysis_text}\n\n"
            f"## محضر الجلسة:\n{self.session_data['summary']}"
        )

        self.conversation_history.append({"role": "user", "content": question})

        messages = [
            {"role": "user", "content": f"بيانات الجلسة:\n{context}"},
            {"role": "assistant", "content": "تم تحميل بيانات الجلسة. يمكنك طرح أسئلتك."},
            *self.conversation_history,
        ]

        response = self.client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        answer = response.content[0].text
        self.conversation_history.append({"role": "assistant", "content": answer})
        return answer

    def handle_message(self, message: A2AMessage):
        msg_type = message.payload.get("type", "ask")

        if msg_type == "load_session":
            self.set_session_data(
                transcript=message.payload.get("full_transcript", ""),
                legal_analysis=message.payload.get("legal_analysis", {}),
                summary=message.payload.get("summary", ""),
            )
            return message.reply(
                payload={"status": "session_loaded"}, sender=self.name
            )

        elif msg_type == "ask":
            question = message.payload.get("question", "")
            answer = self.ask(question)
            return message.reply(payload={"answer": answer}, sender=self.name)
