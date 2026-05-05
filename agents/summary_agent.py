"""Agent 3 — Summary Agent: generates structured session minutes.
Makes autonomous decisions:
  - Determines detail level (brief/standard/detailed) based on session complexity
  - Adjusts structure based on case type and number of parties
Can re-generate with QA feedback to improve results."""

from __future__ import annotations
import json
import anthropic

from a2a.message import A2AMessage
from a2a.protocol import A2AProtocol
from .base_agent import BaseAgent
import config

DETAIL_LEVELS = {
    "brief": {
        "label": "مختصر",
        "instruction": "اكتب محضراً مختصراً (لا يتجاوز 300 كلمة) يركّز على القرارات والنتائج فقط.",
        "conditions": "جلسة قصيرة (أقل من 3 دقائق) أو جلسة إجرائية بسيطة",
    },
    "standard": {
        "label": "قياسي",
        "instruction": "اكتب محضراً متوسط التفصيل يشمل الادعاءات والدفوع والقرارات.",
        "conditions": "جلسة عادية (3-10 دقائق) بطرفين أو ثلاثة",
    },
    "detailed": {
        "label": "تفصيلي",
        "instruction": "اكتب محضراً تفصيلياً شاملاً يوثّق كل ادعاء ودفاع ودليل وتناقض بالتفصيل، مع إبراز النقاط الخلافية.",
        "conditions": "جلسة طويلة أو معقدة (أكثر من 10 دقائق)، أطراف متعددة، تناقضات، أو مبالغ كبيرة",
    },
}

SYSTEM_PROMPT_TEMPLATE = """أنت كاتب ضبط ذكي متخصص في إعداد محاضر الجلسات القضائية.

## قرارك المستقل — مستوى التفصيل: {detail_level_label}
{detail_instruction}

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
    Autonomous decisions:
      - Determines detail level (brief/standard/detailed) based on complexity
      - Adjusts format based on case characteristics
    Can re-generate with feedback from QA agent."""

    def __init__(self, protocol: A2AProtocol):
        super().__init__("summary_agent", protocol)
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self._last_feedback = None
        self._last_detail_decision = None

    def decide_detail_level(self, transcript: str, legal_analysis: dict) -> dict:
        """Autonomous decision: determine appropriate detail level."""
        word_count = len(transcript.split())
        num_parties = len(legal_analysis.get("requests", {}).get("plaintiff", [])) + \
                      len(legal_analysis.get("requests", {}).get("defendant", []))
        num_contradictions = len(legal_analysis.get("contradictions", []))
        num_claims = len(legal_analysis.get("claims", []))
        num_defenses = len(legal_analysis.get("defenses", []))

        complexity_score = 0
        if word_count > 500:
            complexity_score += 2
        elif word_count > 200:
            complexity_score += 1

        if num_contradictions > 0:
            complexity_score += 2
        if num_claims + num_defenses > 4:
            complexity_score += 1
        if num_parties > 3:
            complexity_score += 1

        if complexity_score >= 4:
            level = "detailed"
        elif complexity_score >= 2:
            level = "standard"
        else:
            level = "brief"

        return {
            "level": level,
            "label": DETAIL_LEVELS[level]["label"],
            "reasoning": {
                "word_count": word_count,
                "num_claims": num_claims,
                "num_defenses": num_defenses,
                "num_contradictions": num_contradictions,
                "complexity_score": complexity_score,
            },
        }

    def summarize(self, transcript: str, legal_analysis: dict, feedback: str | None = None) -> tuple[str, dict]:
        """Generate session minutes from transcript + legal analysis.
        Returns (summary_text, detail_decision)."""
        analysis_text = json.dumps(legal_analysis, ensure_ascii=False, indent=2)

        detail_decision = self.decide_detail_level(transcript, legal_analysis)
        self._last_detail_decision = detail_decision

        if feedback:
            system = REGENERATION_PROMPT.format(feedback=feedback)
        else:
            level = detail_decision["level"]
            system = SYSTEM_PROMPT_TEMPLATE.format(
                detail_level_label=DETAIL_LEVELS[level]["label"],
                detail_instruction=DETAIL_LEVELS[level]["instruction"],
            )

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
        return response.content[0].text, detail_decision

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

        summary_text, detail_decision = self.summarize(transcript, legal_analysis, self._last_feedback)

        if self._last_feedback:
            self._last_feedback = None

        return message.reply(
            payload={"summary": summary_text, "detail_decision": detail_decision},
            sender=self.name,
        )
