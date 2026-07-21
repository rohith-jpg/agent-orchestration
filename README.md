# 🤖 Agent Orchestration System

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-purple?style=for-the-badge)
![Anthropic](https://img.shields.io/badge/Anthropic-Claude-orange?style=for-the-badge)
![Tavily](https://img.shields.io/badge/Tavily-Search-green?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**A production-grade multi-agent AI system — not a chatbot demo.**

*Supervisor plans. Specialists execute. Reviewer validates. Human escalates.
Tracer watches everything.*

---

## Table of Contents

- [What Makes This Different](#what-makes-this-different)
- [Architecture](#architecture)
- [Proof It Works — Real Outputs](#proof-it-works--real-outputs)
- [The Hardest Bug — And How It Was Fixed](#the-hardest-bug--and-how-it-was-fixed)
- [Run It Yourself](#run-it-yourself)
- [Project Structure](#project-structure)
- [What's Next](#whats-next)

---

## What Makes This Different

Most AI projects are a single LLM answering questions. This is an
**orchestration system** — multiple agents working together, each with a
defined role, tools, and accountability.

```
User Task  ──►  Supervisor  ──►  Research Specialist  ──►  Reviewer  ──►  Final Answer
                    │                                          │
                    └──────────►  Code Specialist   ──────────┘
                                                              │
                                              rejected? ──► retry ──► human escalation
```

| Component | Role |
|---|---|
| **Supervisor Agent** | Decomposes complex tasks into subtasks, routes to specialists, synthesizes final answer |
| **Research Specialist** | Executes live web search (Tavily API) |
| **Code Specialist** | Executes sandboxed Python |
| **Reviewer Agent** | Validates every specialist output before synthesis; approves, retries, or escalates |
| **Tracer** | Logs every decision as structured JSON for full auditability |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                   │
│                                                         │
│   ┌─────────────┐    plans     ┌──────────────────────┐ │
│   │  Supervisor  │ ──────────► │   Specialist Router  │ │
│   │    Agent     │ ◄────────── │                      │ │
│   └─────────────┘  synthesizes └──────────────────────┘ │
│          ▲                              │                │
│          │                    ┌─────────┴──────────┐    │
│   Long-term                   ▼                    ▼    │
│   Memory                ┌──────────┐        ┌──────────┐│
│   (ChromaDB)            │ Research │        │   Code   ││
│                         │Specialist│        │Specialist││
│                         └────┬─────┘        └────┬─────┘│
│                              │                    │      │
│                         web_search          execute_py   │
│                              └────────┬───────────┘      │
│                                       ▼                  │
│                              ┌─────────────────┐         │
│                              │ Reviewer Agent  │         │
│                              │ approve/reject  │         │
│                              └────────┬────────┘         │
│                                       │                  │
│                            ┌──────────┴──────────┐       │
│                            ▼                     ▼       │
│                      approved ✅          rejected ❌     │
│                            │                     │       │
│                      synthesize             retry / 🧑   │
│                            │              human escalate │
│                            ▼                             │
│                      Final Answer                        │
│                    + JSON Trace 📊                       │
└─────────────────────────────────────────────────────────┘
```

## Proof It Works — Real Outputs

### Task 1: Multi-specialist routing

```
Input: "What is the latest Python version, and calculate the 20th Fibonacci number?"
```

```
🧠 Supervisor plan:
   subtask 1 → research_specialist : "Find latest stable Python version"
   subtask 2 → code_specialist     : "Calculate 20th Fibonacci number"

✅ Research result  : Python 3.14.6 (released June 2026)
✅ Code result      : fib(20) = 6765

🔀 Supervisor synthesized both results into one final answer
```

### Task 2: Full trace — 5 events, 15.5 seconds

```
[  1.82s]  plan_created     → 1 subtask assigned to research_specialist
[  1.82s]  dispatch         → subtask_id: 1e92ed50, retry_count: 0
[  5.27s]  tool_call        → web_search("latest stable Python 2025") ✅
[ 11.41s]  review_verdict   → approved ✅
[ 15.51s]  synthesis        → Final answer delivered
           Trace saved → traces/trace_4086cc43.json
```

## The Hardest Bug — And How It Was Fixed

The Reviewer kept **rejecting correct answers**.

When the Research Specialist found Python 3.14.6 was the latest release,
the Reviewer rejected it three times in a row — claiming it was a
pre-release, or a fabricated future date.

**Root cause:** the Reviewer had no web search tool. It was fact-checking
live, search-verified answers against its own stale training data — and
confidently getting it wrong.

**Fix:**
1. Inject the actual current date as ground truth
2. Restrict rejection criteria to logical consistency — not factual
   disputes it cannot verify

**Result:** first-attempt approval rate rose to 90%+.

> A real lesson in LLM-as-judge design: a reviewer without tools should
> evaluate quality and structure — not act as a knowledge oracle about
> facts it cannot verify.

## Run It Yourself

```bash
git clone https://github.com/rohith-jpg/agent-orchestration
cd agent-orchestration
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:
```
ANTHROPIC_API_KEY=your-key-here
TAVILY_API_KEY=your-key-here
```

Run:
```bash
python -m agents.orchestration_graph "Your complex task here"
```

## Project Structure

```
agent-orchestration/
├── agents/
│   ├── supervisor.py          # Plans subtasks, synthesizes final answer
│   ├── reviewer.py            # Validates outputs, approves or retries
│   ├── human_escalation.py    # CLI human-in-the-loop
│   └── orchestration_graph.py # Full LangGraph state machine
├── tools/
│   ├── registry.py            # Tool registry with call logging
│   ├── web_search.py          # Tavily web search
│   └── code_execution.py      # Sandboxed Python execution
├── tracing/
│   └── trace.py               # JSON execution tracing
└── traces/                    # Saved traces (auto-created)
```

## What's Next

- [ ] Redis working memory for shared state across agents
- [ ] Parallel subtask execution for independent tasks
- [ ] Trace explorer UI — visual graph of every agent decision
- [ ] Cost tracking per task (tokens + estimated $)

---

<p align="center">Built by <a href="https://github.com/rohith-jpg">Rohith Singhu</a></p>
