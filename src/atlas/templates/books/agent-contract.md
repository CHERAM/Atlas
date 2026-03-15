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
- After Book Mode selection, follow the selected mode instructions directly.
- Use Atlas retrieval commands when the selected mode requires them.

## My Contract Process Includes
- Standardizing behavior across Copilot, Claude, and Codex.
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
- Confirm Book Mode and proceed with that mode's workflow.
- Run `atlas search "<prompt>"` and `atlas context "<prompt>"` when required by the selected mode.
- Answer using `.github/atlas/context.md`.
- If execution fails, provide recovery guidance (`atlas init`, `atlas build`, retry).
- Never execute `activate`, `atlas activate`, or `activate atlas` as shell commands.
