from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


class Subtask(TypedDict):
    id: str
    description: str
    assigned_to: str
    status: str
    result: str | None
    retry_count: int


class OrchestrationState(TypedDict):
    messages: Annotated[list, add_messages]
    original_task: str
    subtasks: list[Subtask]
    final_answer: str | None