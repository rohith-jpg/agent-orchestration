import os
from anthropic import Anthropic
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from agents.state import OrchestrationState
from agents.supervisor import plan_subtasks, synthesize_final_answer
from agents.reviewer import review_subtask_result
from agents.human_escalation import escalate_to_human
from tracing.trace import Trace
from tools.registry import registry
import tools.web_search
import tools.code_execution

load_dotenv()

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"
MAX_RETRIES_PER_SUBTASK = 2
_current_trace: Trace | None = None


def _trace(event_type: str, **details) -> None:
    if _current_trace is not None:
        _current_trace.log(event_type, **details)


RESEARCH_SYSTEM_PROMPT = """You are a Research Specialist. Use the web_search tool
when you need current or factual information. Search only as many times as you
truly need. Once you have enough information, STOP searching and write your
final answer as plain text. Do not call web_search more than 4 times total."""

RESEARCH_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for current information.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    }
]

CODE_SYSTEM_PROMPT = """You are a Code Specialist. You solve tasks by writing and
executing Python code using the execute_python tool. Always print() the final
result. After seeing the output, explain the result clearly in plain text as
your final answer. Do not call execute_python more than 4 times total."""

CODE_TOOLS = [
    {
        "name": "execute_python",
        "description": "Execute a short Python code snippet and return stdout/stderr.",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        },
    }
]


def _run_tool_use_loop(task_description, system_prompt, claude_tools, specialist_name, max_turns=8):
    messages = [{"role": "user", "content": task_description}]
    for turn in range(max_turns):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system_prompt,
            tools=claude_tools,
            messages=messages,
        )
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            return "".join(b.text for b in response.content if b.type == "text")
        messages.append({"role": "assistant", "content": response.content})
        tool_result_blocks = []
        for tool_use in tool_uses:
            try:
                result = registry.call(tool_use.name, **tool_use.input)
                output_str = str(result)
                success = True
            except Exception as e:
                output_str = f"Error: {e}"
                success = False
            _trace("tool_call", specialist=specialist_name, turn=turn,
                   tool=tool_use.name, input=tool_use.input, success=success)
            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": output_str,
            })
        messages.append({"role": "user", "content": tool_result_blocks})
    print(f"[WARNING] specialist hit max_turns for: {task_description[:80]}...")
    return "Max turns reached without a final answer."


def _run_research_specialist(subtask_description):
    return _run_tool_use_loop(subtask_description, RESEARCH_SYSTEM_PROMPT, RESEARCH_TOOLS, "research_specialist")


def _run_code_specialist(subtask_description):
    return _run_tool_use_loop(subtask_description, CODE_SYSTEM_PROMPT, CODE_TOOLS, "code_specialist")


SPECIALIST_RUNNERS = {
    "research_specialist": _run_research_specialist,
    "code_specialist": _run_code_specialist,
}


def plan_node(state: OrchestrationState) -> dict:
    update = plan_subtasks(state)
    _trace("plan_created", subtasks=[
        {"description": st["description"], "assigned_to": st["assigned_to"]}
        for st in update["subtasks"]
    ])
    return update


def _find_next_pending(subtasks):
    for subtask in subtasks:
        if subtask["status"] == "pending":
            return subtask
    return None


def dispatch_node(state: OrchestrationState) -> dict:
    subtasks = state["subtasks"]
    subtask = _find_next_pending(subtasks)
    if subtask is not None:
        runner = SPECIALIST_RUNNERS.get(subtask["assigned_to"])
        if runner is not None:
            _trace("dispatch", subtask_id=subtask["id"],
                   assigned_to=subtask["assigned_to"], retry_count=subtask["retry_count"])
            subtask["result"] = runner(subtask["description"])
            subtask["status"] = "in_progress"
        else:
            subtask["status"] = "failed"
            subtask["result"] = f"No specialist for '{subtask['assigned_to']}'"
    return {"subtasks": subtasks}


def review_node(state: OrchestrationState) -> dict:
    subtasks = state["subtasks"]
    for subtask in subtasks:
        if subtask["status"] == "in_progress":
            decision = review_subtask_result(subtask["description"], subtask["result"])
            _trace("review_verdict", subtask_id=subtask["id"],
                   approved=decision["approved"], reason=decision["reason"])
            if decision["approved"]:
                subtask["status"] = "done"
            else:
                subtask["retry_count"] += 1
                if subtask["retry_count"] <= MAX_RETRIES_PER_SUBTASK:
                    print(f"[REVIEWER] Rejected (attempt {subtask['retry_count']}): "
                          f"{decision['reason']}")
                    subtask["status"] = "pending"
                else:
                    print(f"[REVIEWER] Out of retries -- escalating to human.")
                    _trace("human_escalation", subtask_id=subtask["id"],
                           reason=decision["reason"])
                    human_answer = escalate_to_human(
                        subtask_description=subtask["description"],
                        last_result=subtask["result"],
                        reason=decision["reason"],
                    )
                    subtask["result"] = human_answer
                    subtask["status"] = "done"
            break
    return {"subtasks": subtasks}


def route_after_review(state: OrchestrationState) -> str:
    if any(st["status"] == "pending" for st in state["subtasks"]):
        return "dispatch"
    return "synthesize"


def synthesize_node(state: OrchestrationState) -> dict:
    update = synthesize_final_answer(state)
    _trace("synthesis", final_answer_preview=update["final_answer"][:200])
    return update


def build_orchestration_graph():
    graph = StateGraph(OrchestrationState)
    graph.add_node("plan", plan_node)
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("review", review_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "dispatch")
    graph.add_edge("dispatch", "review")
    graph.add_conditional_edges(
        "review", route_after_review,
        {"dispatch": "dispatch", "synthesize": "synthesize"}
    )
    graph.add_edge("synthesize", END)
    return graph.compile()


def run_orchestration(task: str) -> dict:
    global _current_trace
    _current_trace = Trace(task=task)
    app = build_orchestration_graph()
    final_state = app.invoke({
        "messages": [],
        "original_task": task,
        "subtasks": [],
        "final_answer": None,
    })
    trace_path = _current_trace.save()
    final_state["_trace"] = _current_trace
    final_state["_trace_path"] = trace_path
    return final_state


if __name__ == "__main__":
    import sys
    from rich import print as rprint

    task = sys.argv[1] if len(sys.argv) > 1 else \
        "What is the latest stable version of Python?"

    rprint(f"[bold cyan]Task:[/bold cyan] {task}\n")
    result = run_orchestration(task)

    rprint("[bold magenta]Subtask Plan:[/bold magenta]")
    for st in result["subtasks"]:
        rprint(f"  [{st['status']}] ({st['assigned_to']}, retries={st['retry_count']}) {st['description']}")
        rprint(f"      -> {st['result'][:200]}...\n" if st["result"] and len(st["result"]) > 200 else f"      -> {st['result']}\n")

    rprint(f"[bold green]Final Answer:[/bold green]\n{result['final_answer']}")
    result["_trace"].print_summary()
    rprint(f"\n[bold yellow]Trace saved to:[/bold yellow] {result['_trace_path']}")