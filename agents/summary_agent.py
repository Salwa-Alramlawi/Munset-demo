"""Agent 3 — Summary Agent: generates structured session minutes."""

from __future__ import annotations
import anthropic

from a2a.message import A2AMessage
from a2a.protocol import A2AProtocol
from .base_agent import BaseAgent
import config

SYSTEM_PROMPT = """أنت كاتب ضبط ذكي متخصص في إعداد محاضر الجلسات القضائية.

بناءً على النص المُفرّغ والتحليل القانوني المُقدّم لك، أنشئ:

1. **محضر الجلسة الرسمي**: وثيقة مُهيكلة تتضمن:
   - رقم القضية والتاريخ (إن وُجد)
   - أطراف الدعوى
   - ملخص ما دار في الجلسة
   - الطلبات المقدمة
   - القرارات المتخذة

2. **ملخص تنفيذي**: فقرة واحدة مختصرة للقاضي تلخّص أهم ما جاء في الجلسة.

3. **الإجراءات القادمة**: قائمة بالنقاط المعلّقة والخطوات التالية المطلوبة.

اكتب بلغة قانونية رسمية واضحة."""


class SummaryAgent(BaseAgent):
    """Generates structured session minutes and executive summary."""

    def __init__(self, protocol: A2AProtocol):
        super().__init__("summary_agent", protocol)
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def summarize(self, transcript: str, legal_analysis: dict) -> str:
        """Generate session minutes from transcript + legal analysis."""
        import json
        analysis_text = json.dumps(legal_analysis, ensure_ascii=False, indent=2)

        response = self.client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"## النص المُفرّغ للجلسة:\n{transcript}\n\n"
                        f"## التحليل القانوني:\n{analysis_text}\n\n"
                        "أنشئ محضر الجلسة والملخص التنفيذي والإجراءات القادمة."
                    ),
                }
            ],
        )
        return response.content[0].text

    def handle_message(self, message: A2AMessage):
        # Handle feedback from QA agent (bidirectional A2A)
        if message.msg_type == "feedback":
            feedback = message.payload.get("feedback", "")
            severity = message.payload.get("severity", "info")
            return message.reply(
                payload={"status": "feedback_received", "action": f"ملاحظة ({severity}): {feedback} — سيتم مراعاتها في التلخيصات القادمة."},
                sender=self.name,
            )

        # Handle clarification requests from other agents
        if message.msg_type == "clarification_request":
            question = message.payload.get("clarification_question", "")
            return message.reply(
                payload={"clarification_answer": f"وكيل التلخيص: بخصوص '{question}' — تم التوضيح."},
                sender=self.name,
            )

        transcript = message.payload.get("full_transcript", "")
        legal_analysis = message.payload.get("legal_analysis", {})
        result = self.summarize(transcript, legal_analysis)
        return message.reply(payload={"summary": result}, sender=self.name)
