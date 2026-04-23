"""Agent 4 — QA Agent: reviews the session record for quality and completeness."""

from __future__ import annotations
import json
import anthropic

from a2a.message import A2AMessage
from a2a.protocol import A2AProtocol
from .base_agent import BaseAgent
import config

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


class QAAgent(BaseAgent):
    """Reviews the generated summary for quality and completeness."""

    def __init__(self, protocol: A2AProtocol):
        super().__init__("qa_agent", protocol)
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def review(self, transcript: str, summary: str, legal_analysis: dict) -> dict:
        """Review the summary against the original transcript."""
        analysis_text = json.dumps(legal_analysis, ensure_ascii=False, indent=2)

        response = self.client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
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

    def _send_feedback_to_agents(self, qa_result: dict):
        """Send feedback to upstream agents if quality issues are found (bidirectional A2A)."""
        issues = qa_result.get("issues", [])
        feedback_log = []

        for issue in issues:
            severity = issue.get("severity", "low")
            issue_type = issue.get("type", "")
            description = issue.get("description", "")

            # Route feedback to the appropriate upstream agent
            if issue_type in ("missing_info", "inaccuracy"):
                # Feedback to summary agent — missing or inaccurate content
                self.protocol.send_feedback(
                    from_agent=self.name,
                    to_agent="summary_agent",
                    feedback=f"[{issue_type}] {description}",
                    severity=severity,
                )
                feedback_log.append({"to": "summary_agent", "issue": description})

            elif issue_type == "contradiction":
                # Feedback to legal analysis agent — contradiction detected
                self.protocol.send_feedback(
                    from_agent=self.name,
                    to_agent="legal_analysis_agent",
                    feedback=f"[تناقض] {description}",
                    severity=severity,
                )
                feedback_log.append({"to": "legal_analysis_agent", "issue": description})

        return feedback_log

    def handle_message(self, message: A2AMessage):
        # Handle clarification requests from other agents
        if message.msg_type == "clarification_request":
            question = message.payload.get("clarification_question", "")
            return message.reply(
                payload={"clarification_answer": f"وكيل المراجعة: {question} — يتم التحقق."},
                sender=self.name,
            )

        transcript = message.payload.get("full_transcript", "")
        summary = message.payload.get("summary", "")
        legal_analysis = message.payload.get("legal_analysis", {})
        result = self.review(transcript, summary, legal_analysis)

        # Send feedback to upstream agents about quality issues (bidirectional A2A)
        feedback_log = self._send_feedback_to_agents(result)
        result["feedback_sent"] = feedback_log

        return message.reply(payload={"qa_review": result}, sender=self.name)
