"""Agent 4 — QA Agent: reviews the session record for quality and completeness.
Uses a structured rubric with weighted criteria for transparent, reproducible scoring.
Acts as a gatekeeper — rejects and requests re-generation if quality is below threshold."""

from __future__ import annotations
import json
import anthropic

from a2a.message import A2AMessage
from a2a.protocol import A2AProtocol
from .base_agent import BaseAgent
import config

QUALITY_THRESHOLD = 85

RUBRIC = [
    {"id": "parties",     "name": "ذكر جميع الأطراف وأسمائهم ووكلائهم", "weight": 15},
    {"id": "claims",      "name": "اكتمال الادعاءات والدفوع",           "weight": 20},
    {"id": "evidence",    "name": "ذكر الأدلة والمستندات",              "weight": 15},
    {"id": "articles",    "name": "دقة المواد النظامية وانطباقها",       "weight": 15},
    {"id": "contradictions", "name": "رصد التناقضات بين الأطراف",       "weight": 10},
    {"id": "decisions",   "name": "قرارات المحكمة والإجراءات",          "weight": 15},
    {"id": "financials",  "name": "دقة المبالغ والتواريخ",              "weight": 10},
]

RUBRIC_TEXT = "\n".join(
    f"  {i+1}. **{c['name']}** — الوزن: {c['weight']}% (المعرّف: {c['id']})"
    for i, c in enumerate(RUBRIC)
)

SYSTEM_PROMPT = f"""أنت مراجع جودة متخصص في محاضر الجلسات القضائية.

مهمتك مراجعة المحضر المُنتَج مقابل النص الأصلي باستخدام معايير التقييم التالية:

{RUBRIC_TEXT}

لكل معيار، قيّم نسبة الاستيفاء (0-100) ثم تُحسب الدرجة النهائية تلقائياً بضرب النسبة في الوزن.

أجب بصيغة JSON فقط:
{{
    "criteria_scores": {{
        "parties": {{"score": 0-100, "notes": "ملاحظة مختصرة"}},
        "claims": {{"score": 0-100, "notes": "..."}},
        "evidence": {{"score": 0-100, "notes": "..."}},
        "articles": {{"score": 0-100, "notes": "..."}},
        "contradictions": {{"score": 0-100, "notes": "..."}},
        "decisions": {{"score": 0-100, "notes": "..."}},
        "financials": {{"score": 0-100, "notes": "..."}}
    }},
    "issues": [
        {{
            "type": "missing_info | contradiction | inaccuracy | suggestion",
            "criterion": "معرّف المعيار المتأثر",
            "description": "وصف المشكلة",
            "severity": "high | medium | low"
        }}
    ],
    "verified_articles": ["المواد النظامية التي تم التحقق منها"],
    "overall_assessment": "تقييم عام مختصر"
}}"""

IMPROVEMENT_PROMPT = f"""أنت مراجع جودة متخصص في محاضر الجلسات القضائية.

هذه الجولة الثانية من المراجعة. المحضر والتحليل تمت إعادة إنتاجهما بعد ملاحظاتك السابقة.

ملاحظاتك السابقة كانت:
{{previous_issues}}

راجع المحضر المُحدَّث باستخدام نفس معايير التقييم:

{RUBRIC_TEXT}

تحقق بالذات من أن الملاحظات السابقة تم معالجتها.

أجب بنفس صيغة JSON:
{{{{
    "criteria_scores": {{{{
        "parties": {{{{"score": 0-100, "notes": "..."}}}},
        "claims": {{{{"score": 0-100, "notes": "..."}}}},
        "evidence": {{{{"score": 0-100, "notes": "..."}}}},
        "articles": {{{{"score": 0-100, "notes": "..."}}}},
        "contradictions": {{{{"score": 0-100, "notes": "..."}}}},
        "decisions": {{{{"score": 0-100, "notes": "..."}}}},
        "financials": {{{{"score": 0-100, "notes": "..."}}}}
    }}}},
    "issues": [...],
    "verified_articles": [...],
    "overall_assessment": "..."
}}}}"""


class QAAgent(BaseAgent):
    """Reviews the generated summary for quality and completeness.
    Acts as a gatekeeper: rejects and sends feedback if score < threshold."""

    def __init__(self, protocol: A2AProtocol):
        super().__init__("qa_agent", protocol)
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    @staticmethod
    def compute_weighted_score(criteria_scores: dict) -> tuple[int, dict]:
        """Compute final score from per-criterion scores using RUBRIC weights.
        Returns (total_score, breakdown_dict)."""
        weight_map = {c["id"]: c["weight"] for c in RUBRIC}
        breakdown = {}
        total = 0.0
        for cid, weight in weight_map.items():
            entry = criteria_scores.get(cid, {})
            raw = entry.get("score", 0) if isinstance(entry, dict) else 0
            weighted = round(raw * weight / 100, 1)
            breakdown[cid] = {"raw_score": raw, "weight": weight, "weighted_score": weighted}
            total += weighted
        return round(total), breakdown

    def review(self, transcript: str, summary: str, legal_analysis: dict, previous_issues: str | None = None) -> dict:
        """Review the summary against the original transcript using structured rubric."""
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
                        "راجع المحضر وقدّم تقرير الجودة حسب معايير التقييم."
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
            result = json.loads(raw.strip())
        except json.JSONDecodeError:
            return {"raw_review": raw, "parse_error": True}

        criteria_scores = result.get("criteria_scores", {})
        total_score, breakdown = self.compute_weighted_score(criteria_scores)
        result["completeness_score"] = total_score
        result["score_breakdown"] = breakdown
        result["rubric"] = [{"id": c["id"], "name": c["name"], "weight": c["weight"]} for c in RUBRIC]
        return result

    def decide_action(self, qa_result: dict) -> str:
        """Autonomous decision: accept or reject based on weighted score."""
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
