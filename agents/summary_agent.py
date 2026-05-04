"""Agent 3 — Summary Agent: generates structured session minutes.
Can re-generate with QA feedback to improve results."""

from __future__ import annotations
import json
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

REGENERATION_PROMPT = """أنت كاتب ضبط ذكي متخصص في إعداد محاضر الجلسات القضائية.

هذه الجولة الثانية. وكيل مراجعة الجودة رفض المحضر السابق وأرسل لك الملاحظات التالية:

{feedback}

أعد إنشاء المحضر مع معالجة كل ملاحظة من الملاحظات أعلاه. تأكد من إضافة كل المعلومات المفقودة وتصحيح أي خطأ.

أنشئ:
1. محضر الجلسة الرسمي (مُحسَّن)
2. ملخص تنفيذي
3. الإجراءات القادمة

اكتب بلغة قانونية رسمية واضحة."""


class SummaryAgent(BaseAgent):
    """Generates structured session minutes and executive summary.
    Can re-generate with feedback from QA agent."""

    def __init__(self, protocol: A2AProtocol):
        super().__init__("summary_agent", protocol)
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self._last_feedback = None

    def summarize(self, transcript: str, legal_analysis: dict, feedback: str | None = None) -> str:
        """Generate session minutes from transcript + legal analysis."""
        analysis_text = json.dumps(legal_analysis, ensure_ascii=False, indent=2)

        if feedback:
            system = REGENERATION_PROMPT.format(feedback=feedback)
        else:
            system = SYSTEM_PROMPT

        response = self.client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=4096,
            system=system,
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
        if message.msg_type == "feedback":
            feedback = message.payload.get("feedback", "")
            self._last_feedback = feedback
            return message.reply(
                payload={"status": "feedback_received", "action": "سيتم إعادة إنتاج المحضر مع مراعاة الملاحظات"},
                sender=self.name,
            )

        if message.msg_type == "clarification_request":
            question = message.payload.get("clarification_question", "")
            return message.reply(
                payload={"clarification_answer": f"وكيل التلخيص: بخصوص '{question}' — تم التوضيح."},
                sender=self.name,
            )

        transcript = message.payload.get("full_transcript", "")
        legal_analysis = message.payload.get("legal_analysis", {})
        feedback = message.payload.get("qa_feedback")

        if feedback:
            self._last_feedback = feedback

        result = self.summarize(transcript, legal_analysis, self._last_feedback)

        if self._last_feedback:
            self._last_feedback = None

        return message.reply(payload={"summary": result}, sender=self.name)
