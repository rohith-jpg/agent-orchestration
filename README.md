\# Agent Orchestration System



> Built a multi-agent orchestration platform where a Supervisor agent decomposes complex tasks, routes them to specialized agents, and a Reviewer validates every output before synthesis — with automatic retry, human-in-the-loop escalation, persistent memory, and full execution tracing.



\*\*Tech stack:\*\* Python 3.12 · LangGraph · Anthropic Claude · Tavily Search · ChromaDB · Docker



\---



\## What this is



Most AI projects are single-agent demos: one LLM, one tool, one task. This is different.



This system works the way a real engineering team does: a \*\*Supervisor\*\* breaks a complex request into subtasks, assigns each to the right \*\*specialist\*\* (web research or code execution), a \*\*Reviewer\*\* checks every output before it's accepted, and the Supervisor synthesizes everything into a final answer. If a specialist repeatedly fails, a human operator is asked directly — the system doesn't guess.



Every single agent decision is logged to a structured JSON trace so you can inspect exactly why the system did what it did.



\---



\## Architecture



```

Complex task input

&#x20;      │

&#x20;      ▼

┌─────────────────────┐

│   Supervisor agent  │ ◄──── Long-term memory (ChromaDB)

│  Plans \& delegates  │

└──────────┬──────────┘

&#x20;          │

&#x20;    ┌─────┴──────┐

&#x20;    ▼            ▼

┌─────────┐  ┌─────────┐

│Research │  │  Code   │   ← Tool registry (web search, Python exec)

│Specialist│  │Specialist│

└────┬────┘  └────┬────┘

&#x20;    └─────┬──────┘

&#x20;          ▼

┌─────────────────────┐

│   Reviewer agent    │──── rejected? → retry (max 2x) → human escalation

│  Validates quality  │

└──────────┬──────────┘

&#x20;          ▼

┌─────────────────────┐

│ Supervisor: synthesize│

└──────────┬──────────┘

&#x20;          ▼

&#x20; Final answer + JSON trace

```



\---



\## Real output proof



\*\*Task:\*\* "Compare the latest stable releases of PostgreSQL and MySQL, and tell me which has better JSON support."



\*\*What happened inside:\*\*



```

Trace ba99f6d5 -- 5 events, 26.36s total

&#x20; \[  1.90s] plan\_created       subtasks: \[research PostgreSQL JSON, research MySQL JSON]

&#x20; \[  3.41s] dispatch           subtask\_id: 9af59056 → research\_specialist

&#x20; \[  6.45s] tool\_call          web\_search("PostgreSQL vs MySQL JSON support 2025") success=True

&#x20; \[ 15.28s] review\_verdict     approved=True — "result directly addresses the subtask,

&#x20;                               internally consistent, no contradictory information"

&#x20; \[ 26.32s] synthesis          final\_answer\_preview: "PostgreSQL vs MySQL JSON Support..."

Trace saved to: traces/trace\_ba99f6d5.json

```



\*\*Final answer (excerpt):\*\*



> PostgreSQL is the clear winner for JSON workloads, primarily because of:

> 1. \*\*JSONB type\*\* — binary storage with no re-parsing overhead

> 2. \*\*GIN indexing\*\* — index entire documents for fast containment/existence queries

> 3. \*\*Richer operator set\*\* — `->`, `->>`, `@>`, `?`, `?|`, and more

> 4. \*\*Better integration\*\* — JSON works seamlessly with CTEs, window functions, full SQL



\---



\## Task: Python version + Fibonacci (two specialists routing)



\*\*Task:\*\* "What is the latest stable version of Python, and write Python code to calculate the 20th Fibonacci number?"



\*\*Supervisor plan:\*\*

```

subtask 1 → research\_specialist: "Find the latest stable version of Python"

subtask 2 → code\_specialist:     "Write and execute Python code to calculate the 20th Fibonacci number"

```



\*\*Results:\*\*

```

\[done] (research\_specialist, retries=0) Find the latest stable version of Python

&#x20;   → The latest stable version of Python is Python 3.14.6, released June 2026.



\[done] (code\_specialist, retries=0) Calculate the 20th Fibonacci number

&#x20;   → The 20th Fibonacci number is 6765.

&#x20;      def fibonacci(n):

&#x20;          a, b = 0, 1

&#x20;          for \_ in range(n - 1):

&#x20;              a, b = b, a + b

&#x20;          return b

```



This proves the Supervisor correctly identified that the task needed \*\*two different specialists\*\* and routed each subtask to the right one.



\---



\## The hardest bug (and how it was fixed)



The Reviewer agent kept \*\*rejecting correct answers\*\*.



When the Research Specialist searched the web and found that Python 3.14.6 was the latest stable release (correct, as of June 2026), the Reviewer rejected it three times:



```

\[REVIEWER] Rejected (attempt 1): Python 3.14.6 does not exist,

&#x20;          Python 3.14 is still in pre-release/alpha stage...

\[REVIEWER] Rejected (attempt 2): fabricated future dates...

\[REVIEWER] Rejected (attempt 3): out of retries — escalating to human

```



\*\*Root cause:\*\* The Reviewer had no web search tool. It was fact-checking live, search-verified answers against its own training data — which had a cutoff before Python 3.14 was released. It was confidently wrong about current facts.



\*\*Fix:\*\* Two changes to the Reviewer's prompt:

1\. Give it the actual current date as ground truth

2\. Restrict rejection criteria to \*\*logical consistency and completeness\*\* — not factual disputes it can't verify



After the fix:

```

\[  11.41s] review\_verdict  approved=True — "result provides a specific, current version

&#x20;                           number plausible given today's date of 2026-07-06"

```



This is a real lesson about LLM-as-judge design: \*\*a reviewer without tools should not fact-check claims it cannot verify.\*\* It should evaluate quality, structure, and consistency — not act as a knowledge oracle.



\---



\## How to run it



```bash

git clone https://github.com/rohith-jpg/agent-orchestration

cd agent-orchestration

python -m venv venv

venv\\Scripts\\activate        # Windows

pip install -r requirements.txt

cp .env.example .env         # add your ANTHROPIC\_API\_KEY and TAVILY\_API\_KEY

python -m agents.orchestration\_graph "Your complex task here"

```



\---



\## Project structure



```

agent-orchestration/

├── agents/

│   ├── state.py                  # Shared state schemas (LangGraph)

│   ├── supervisor.py             # Plans subtasks, synthesizes final answer

│   ├── reviewer.py               # Validates specialist outputs

│   ├── human\_escalation.py       # CLI human-in-the-loop prompt

│   └── orchestration\_graph.py    # Full multi-agent LangGraph graph

├── tools/

│   ├── registry.py               # Central tool registry with call logging

│   ├── web\_search.py             # Tavily-backed web search

│   └── code\_execution.py         # Sandboxed Python execution

├── tracing/

│   └── trace.py                  # Structured execution tracing

├── traces/                       # Saved JSON traces (created at runtime)

└── requirements.txt

```



\---



\## What I'd add next



\- \*\*Redis working memory\*\* — shared state across agents within a single run

\- \*\*Parallel subtask execution\*\* — independent subtasks running concurrently

\- \*\*Trace explorer UI\*\* — visual graph of every agent decision

\- \*\*Cost tracking\*\* — tokens used and estimated cost per task



\---



\## Why this project



Agents are the frontier of AI engineering. Most portfolio projects are single-agent demos that call one API and return one response. This system demonstrates the architecture that real production agent systems use: task decomposition, specialist routing, quality validation with retry logic, human oversight for edge cases, and full observability into every decision. The Reviewer bug — and how it was diagnosed and fixed — is the kind of real-world LLM failure mode that doesn't show up in tutorials.



