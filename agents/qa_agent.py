"""Agent 4 — QA Agent: reviews the session record for quality and completeness.
Acts as a gatekeeper — rejects and requests re-generation if quality is below threshold."""

from __future__ import annotations
import json
import anthropic

from a2a.message import A2AMessage
from a2a.protocol import A2AProtocol
from .base_agent import BaseAgent
import config

QUALITY_THRESHOLD = 85

SYSTEM_PROMPT = """أنت مراجع جودة متخصص في محاضر الجلسات القضائية.

مهمتك مراجعة المحضر المُنتَج والتحقق من:

1. **اكتمال المعلومات**: هل يحتوي المحضر على كل ما ذُكر في النص الأصلي؟
2. **دقة الإشارات النظامية**: هل المواد النظامية المذكورة صحيحة ومناسبة؟
3. **تناقضات الأقوال**: هل يوجد تناقض في أقوال أي طرف؟
4. **معلومات مفقودة**: هل فاتت أي نقطة جوهرية؟

أجب بصيغة JSON:
{
    "completeness_score": 0-100,
    "issues": [
        {
            "type": "missing_info | contradiction | inaccuracy | suggestion",
            "description": "وصف المشكلة",
            "severity": "high | medium | low"
        }
    ],
    "verified_articles": ["المواد النظامية التي تم التحقق منها"],
    "overall_assessment": "تقييم عام مختصر"
}"""

IMPROVEMENT_PROMPT = """أنت مراجع جودة متخصص في محاضر الجلسات القضائية.

هذه الجولة الثانية من المراجعة. المحضر والتحليل تمت إعادة إنتاجهما بعد ملاحظاتك السابقة.

ملاحظاتك السابقة كانت:
{previous_issues}

راجع المحضر المُحدَّث وقدّم تقرير جودة جديد. تحقق بالذات من أن الملاحظات السابقة تم معالجتها.

أجب بنفس صيغة JSON:
{{
    "completeness_score": 0-100,
    "issues": [...],
    "verified_articles": [...],
    "overall_assessment": "..."
}}"""


class QAAgent(BaseAgent):
    """Reviews the generated summary for quality and completeness.
    Acts as a gatekeeper: rejects and sends feedback if score < threshold."""

    def __init__(self, protocol: A2AProtocol):
        super().__init__("qa_agent", protocol)
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def review(self, transcript: str, summary: str, legal_analysis: dict, previous_issues: str | None = None) -> dict:
        """Review the summary against the original transcript."""
        analysis_text = json.dumps(legal_analysis, ensure_ascii=False, indent=2)

        if previous_issues:
            system = IMPROVEMENT_PROMPT.format(previous_issues=previous_issues)
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
                        f"## النص الأصلي المُفرّغ:\n{transcript}\n\n"
                        f"## التحليل القانوني:\n{analysis_text}\n\n"
                        f"## المحضر المُنتَج:\n{summary}\n\n"
                        "راجع المحضر وقدّم تقرير الجودة."
                    ),
                }
            ],
        )

        raw = response.content[0].text
        try:
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            return {"raw_review": raw, "parse_error": True}

    def decide_action(self, qa_result: dict) -> str:
        """Autonomous decision: accept or reject the session record."""
        score = qa_result.get("completeness_score", 0)
        if score >= QUALITY_THRESHOLD:
            return "accept"
        return "reject"

    def _build_feedback_for_agents(self, qa_result: dict) -> dict:
        """Decide WHICH upstream agent to send feedback to based on issue type."""
        issues = qa_result.get("issues", [])
        summary_feedback = []
        legal_feedback = []

        for issue in issues:
            issue_type = issue.get("type", "")
            description = issue.get("description", "")
            severity = issue.get("severity", "low")

            if issue_type in ("missing_info", "inaccuracy", "suggestion"):
                summary_feedback.append({"description": description, "severity": severity, "type": issue_type})
            elif issue_type == "contradiction":
                legal_feedback.append({"description": description, "severity": severity, "type": issue_type})

        return {"summary_agent": summary_feedback, "legal_analysis_agent": legal_feedback}

    def send_rejection_feedback(self, qa_result: dict) -> list[dict]:
        """Send targeted feedback to upstream agents via A2A when rejecting."""
        feedback_map = self._build_feedback_for_agents(qa_result)
        feedback_log = []

        for agent_name, issues in feedback_map.items():
            if not issues:
                continue
            feedback_text = "\n".join(f"- [{i['type']}][{i['severity']}] {i['description']}" for i in issues)
            self.protocol.send_feedback(
                from_agent=self.name,
                to_agent=agent_name,
                feedback=feedback_text,
                severity="high",
            )
            feedback_log.append({"to": agent_name, "issues": issues})

        return feedback_log

    def handle_message(self, message: A2AMessage):
        if message.msg_type == "clarification_request":
            question = message.payload.get("clarification_question", "")
            return message.reply(
                payload={"clarification_answer": f"وكيل المراجعة: {question} — يتم التحقق."},
                sender=self.name,
            )

        transcript = message.payload.get("full_transcript", "")
        summary = message.payload.get("summary", "")
        legal_analysis = message.payload.get("legal_analysis", {})
        previous_issues = message.payload.get("previous_issues")

        result = self.review(transcript, summary, legal_analysis, previous_issues)

        action = self.decide_action(result)
        result["decision"] = action
        result["quality_threshold"] = QUALITY_THRESHOLD

        if action == "reject":
            feedback_log = self.send_rejection_feedback(result)
            result["feedback_sent"] = feedback_log
        else:
            result["feedback_sent"] = []

        return message.reply(payload={"qa_review": result}, sender=self.name)
