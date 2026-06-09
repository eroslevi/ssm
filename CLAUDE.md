# SSM Legal Compliance Checker — Development Guide

## Project Summary

Single-pass SSM-based system that checks a company statement for compliance with a
preceding corpus of laws. The full input stream is structured as:

```
[law corpus .............. | company statement]
       ↓ SSM accumulates law context   ↓ SSM checks statement against hidden state
```

The SSM runs with very low volatility so the law context persists in the hidden state
until the statement is processed. Compliance violations surface when the statement
contradicts the accumulated law context. No retrieval phases — one streaming pass.

**Target environment:** Windows (HP EliteBook), on-prem, Python 3.10+, CPU-first with
optional CUDA.

---

## Development Methodology

### 1. Spec-First Iterative Refinement

All implementation is preceded by written specifications reviewed by the human before
any code is written. Spec levels are strictly ordered — each must be approved before
the next begins:

| File | Level | Contents |
|------|-------|----------|
| `specs/01_user_spec.md` | High | What the system does, who uses it, inputs/outputs, constraints |
| `specs/02_system_spec.md` | Mid | Components, data flow, SSM architecture, interfaces |
| `specs/03_components/*.md` | Low | One file per component: design, parameters, data structures, acceptance criteria |

No code is written until all component specs are approved.

### 2. Narrow Feature Iteration

Each implementation stage covers exactly one component or one integration boundary.
For every stage:

1. Implement the feature
2. Write a minimal evaluation script
3. Measure: correct output? latency and memory on target hardware?
4. If unsatisfactory: identify root cause, rewrite, re-measure
5. Do not advance until the feature meets the acceptance criteria defined in its spec

### 3. Human Review Gates

Every stage produces exactly one artifact for review — a spec document or a feature
result summary. Each artifact must be:

- Self-contained (readable without scrolling back through prior conversation)
- Bounded (target: fits on one screen)
- Accompanied by a clear yes/no question: "does this match your intent?"

Implementation does not proceed past a gate without explicit human approval.

### 4. Persistent Status Tracking

`status.md` is the single source of truth for project state. It is updated at the end
of every stage. It contains current phase, completed items with outcome notes, open
questions, and the single next action.

**Always read `status.md` at the start of a new session before taking any action.**

---

## Implementation Stages

| Stage | Artifact | Gate |
|-------|----------|------|
| 0 | `specs/01_user_spec.md` | Human approval |
| 1 | `specs/02_system_spec.md` | Human approval |
| 2a–2d | `specs/03_components/*.md` one per component | Human approval per component |
| 3a | Document loader — implementation + measurement | Human approval |
| 3b | SSM engine — streaming pass + measurement | Human approval |
| 3c | Compliance flag extractor — implementation + measurement | Human approval |
| 3d | Output reporter — implementation + measurement | Human approval |
| 3e | End-to-end integration — full pipeline + measurement | Human approval |
