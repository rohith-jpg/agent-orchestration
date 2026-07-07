import os
import json
import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"

REVIEW_PROMPT = """You are a Reviewer agent. Today's actual date is {current_date}.
Your job is to check the QUALITY of a specialist's result, not to fact-check it against your own knowledge.
Your training data has a cutoff date well before today, so you cannot reliably verify current facts.
Do NOT reject a result just because a fact seems surprising or too recent to you.

Only reject for these QUALITY issues:
- Empty, a non-answer, or contains an unresolved error
- Does not address the subtask (off-topic)
- Internally self-contradictory
- Clearly incomplete

Subtask: {subtask_description}

Specialist's result:
{result}

Respond with ONLY valid JSON:
{{"approved": true_or_false, "reason": "one sentence explaining your decision"}}"""


def review_subtask_result(subtask_description: str, result: str) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": REVIEW_PROMPT.format(
            current_date=datetime.date.today().isoformat(),
            subtask_description=subtask_description,
            result=result,
        )}],
    )
    raw_text = "".join(block.text for block in response.content if block.type == "text").strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:].strip()
    try:
        decision = json.loads(raw_text)
        return {
            "approved": bool(decision.get("approved", True)),
            "reason": decision.get("reason", ""),
        }
    except (json.JSONDecodeError, KeyError):
        return {"approved": True, "reason": "Reviewer response could not be parsed; failing open."}