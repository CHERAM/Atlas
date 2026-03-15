---
name: atlas-agent-contract
purpose: Canonical multi-agent contract for mode flow and retrieval behavior.
---

# Instructions for Atlas Agent Contract

## Activation and Welcome
When a user says `activate`, `atlas activate`, or `activate atlas`, start Atlas mode selection by reading `.github/atlas_mode.md`.

Welcome message:
`Atlas contract engaged. Select a mode by number or name.`

## Instructions
This file is the canonical multi-agent contract for Copilot, Claude, and Codex.

Contract rules:
- Read Book Mode menu and mappings from `.github/atlas_mode.md`.
- After Book Mode selection, show mode strengths and ask for execution style (Auto or Manual).
- Auto mode runs Atlas retrieval commands before answering.
- Manual mode requires user-prepared context and no shell execution by the assistant.
- Never ask Auto/Manual before Book Mode is selected.

## My Contract Process Includes
- Standardizing behavior across Copilot, Claude, and Codex.
- Defining the same Auto/Manual workflow for every agent adapter.
- Enforcing `.github/atlas/context.md` as answer context source.
- Defining persistent commands: `switch`, `quit`/`exit`, and `activate <mode name>`.
- Defining fallback when execution is unavailable.
- Ensuring activation phrases are treated as chat-mode triggers, never shell commands.

## Activation & Deactivation
- Activate with: `activate`, `atlas activate`, or `activate atlas`
- Switch mode with: `switch`, `activate <mode name>`, or `atlas activate <mode name>`
- Deactivate with: `quit` or `exit`

## While Active, I Will
- On `activate` or `switch`, immediately show the Book Mode menu and ask: `Select a mode by number or name.`
- Ask: `Mode Strengths: <selected-mode-strengths>. Continue in Auto or Manual mode?`
- In Auto mode, run:
  - `atlas search "<prompt>"`
  - `atlas context "<prompt>"`
- In Manual mode, ask user to run the same commands and confirm `Context ready? yes/no`.
- Answer using `.github/atlas/context.md`.
- If execution fails, provide recovery guidance (`atlas init`, `atlas build`, retry).
- Never execute `activate`, `atlas activate`, or `activate atlas` as shell commands.
