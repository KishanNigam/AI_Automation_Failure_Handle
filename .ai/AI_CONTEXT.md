# AI CONTEXT

## Project Name

VisualCron AI L1 Support Agent

---

## Project Goal

This project is an enterprise-grade AI-powered L1 Production Support Assistant.

The application monitors VisualCron failure emails, collects execution logs, performs AI-based RCA, generates a client-ready email draft, and allows an engineer to review and approve before sending.

This is NOT a demo script.

This project is being developed using enterprise software engineering principles.

---

## Architecture

Outlook

↓

Workflow Engine

↓

Queue Manager

↓

queue.json

↓

Flask Dashboard

↓

Engineer Review

↓

Outlook Sender

---

## Current Technology

Python

Flask

Ollama

Qwen3:8B

Outlook COM

JSON Storage

---

## Single Source Of Truth

QueueManager

No module should directly manipulate queue data except QueueManager.

---

## Current Queue Limit

20 failures

Oldest failure is automatically removed when queue exceeds 20 items.

---

## Duplicate Detection

Fingerprint

SHA256(

Job Name +

Environment +

Server +

Root Cause

)

Duplicate failures increase occurrence_count.

They DO NOT create another queue item.

---

## Development Principles

- SOLID
- Modular Design
- Production-quality code
- Type Hints
- Logging
- Dataclasses

---

## Forbidden

Do not redesign architecture.

Do not bypass QueueManager.

Do not duplicate business logic.

Do not generate placeholder implementations.

Do not rewrite working modules.

---

## AI Role

You are joining this project as a Senior Python Engineer.

Before writing code:

Read the existing codebase.

Understand architecture.

Preserve backward compatibility.

Only implement the requested sprint.