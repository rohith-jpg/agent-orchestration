import os
import json
import uuid
from anthropic import Anthropic
from dotenv import load_dotenv
from agents.state import OrchestrationState, Subtask

load_dotenv()

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"

AVAILABLE_SPECIALISTS = ["research_specialist", "code_specialist"]

SPECIALIST_DESCRIPTIONS = {
    "research_specialist": "Searches the web for current, factual, or general-knowledge information.",
    "code_specialist": "Writes and executes Python code to perform calculations, data processing, or algorithmic tasks.",
}

PLANNING_PROMPT = """You are a Supervisor agent that breaks down tasks for a team of specialist agents.
Available specialists:
{specialist_list}

Given the task below, decide on a list of subtasks needed to complete it.
Keep it minimal -- if the task is simple, a single subtask is fine.
Each subtask must be assigned to whichever specialist is the best fit.

Respond with ONLY valid JSON, no other text:
{{
  "subtasks": [
    {{"description": "...", "assigned_to": "research_specialist"}}
  ]
}}

Task: {task}"""

SYNTHESIS_PROMPT = """You are a Supervisor agent. Your specialists have completed the following subtasks for this original task: "{task}"

Subtask results:
{results}

Write a single, clear, well-organized final answer synthesizing the specialists findings.
Do not mention subtasks or specialists in your answer."""


def plan_subtasks(state: OrchestrationState) -> dict:
    task = state["original_task"]
    specialist_list = "\n".join(
        f"- {name}: {SPECIALIST_DESCRIPTIONS[name]}"
        for name in AVAILABLE_SPECIALISTS
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": PLANNING_PROMPT.format(
                specialist_list=specialist_list,
                task=task
            )
        }],
    )
    raw_text = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:].strip()
    plan = json.loads(raw_text)
    subtasks = []
    for item in plan["subtasks"]:
        subtasks.append({
            "id": str(uuid.uuid4())[:8],
            "description": item["description"],
            "assigned_to": item["assigned_to"],
            "status": "pending",
            "result": None,
            "retry_count": 0,
        })
    return {"subtasks": subtasks}


def synthesize_final_answer(state: OrchestrationState) -> dict:
    results_text = "\n\n".join(
        f"- Subtask: {st['description']}\n  Result: {st['result']}"
        for st in state["subtasks"]
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": SYNTHESIS_PROMPT.format(
                task=state["original_task"],
                results=results_text
            )
        }],
    )
    final_text = "".join(
        block.text for block in response.content if block.type == "text"
    )
    return {"final_answer": final_text}