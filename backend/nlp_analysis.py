"""NLP analysis using Groq LLM for sentiment and severity classification."""

from dataclasses import dataclass
import re
import os
import json

from groq import Groq

_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

_PROMPT = """You are a civic issue classifier for a municipal complaint system.
Analyze the citizen's complaint and return ONLY a JSON object with these fields:
- sentiment_label: one of "negative", "neutral", "positive"
- sentiment_score: float between -1.0 and 1.0
- severity: one of "low", "medium", "high", "critical"
- severity_score: 0.25 for low, 0.5 for medium, 0.75 for high, 1.0 for critical

Severity guide:
- critical: life threatening, emergency, collapsed road, people injured
- high: dangerous, deep pothole, flooded road, near school/hospital, injury risk
- medium: pothole, waterlogging, garbage, blocked drain, bad smell
- low: minor issue, cosmetic damage, no immediate risk

Return only valid JSON, no explanation."""


@dataclass(frozen=True)
class DescriptionAnalysis:
    sentiment_score: float
    sentiment_label: str
    severity: str
    severity_score: float


def sentence_count(text: str) -> int:
    return len([p for p in re.split(r"[.!?]+", text.strip()) if p.strip()])


def analyze_description(description: str) -> DescriptionAnalysis:
    try:
        response = _client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _PROMPT},
                {"role": "user", "content": description},
            ],
            temperature=0.1,
            max_tokens=100,
        )
        result = json.loads(response.choices[0].message.content)
        return DescriptionAnalysis(
            sentiment_score=float(result["sentiment_score"]),
            sentiment_label=result["sentiment_label"],
            severity=result["severity"],
            severity_score=float(result["severity_score"]),
        )
    except Exception:
        # Fallback to rule-based if Groq fails
        return _fallback(description)


def _fallback(description: str) -> DescriptionAnalysis:
    normalized = description.lower()
    if any(w in normalized for w in ("emergency", "injured", "collapsed", "life threatening")):
        return DescriptionAnalysis(-0.8, "negative", "critical", 1.0)
    if any(w in normalized for w in ("dangerous", "deep pothole", "flooded", "school", "hospital")):
        return DescriptionAnalysis(-0.6, "negative", "high", 0.75)
    if any(w in normalized for w in ("pothole", "waterlogging", "garbage", "blocked", "smell")):
        return DescriptionAnalysis(-0.3, "negative", "medium", 0.5)
    return DescriptionAnalysis(0.0, "neutral", "low", 0.25)
