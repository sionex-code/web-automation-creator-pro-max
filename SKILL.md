---
name: open-automation-creator-builder
description: Build, repair, and package browser automations with the Open Automation Creator runtime. Use when the user wants to create a new automation skill or config for any website, inspect the live page with browser tooling, capture and verify selectors, and leave behind a reusable runnable result instead of a guessed script.
---

# Open Automation Creator Builder

This skill runs on the Open Automation Creator runtime bundled in this same repository (`core/`, `run.py`, `scripts/`, `bundles/`, `configs/`).

Before creating or updating any automation, read:

`RUNTIME_GUIDE.md`

Treat that guide as the source of truth for how to build automations in this
runtime.

This skill is intentionally strict so weaker models do not jump straight into a
plausible-looking script. If selectors were not captured from the live page,
you are not ready to write the config.

This skill must also be easy for normal users. Do not expect the user to know
selectors, YAML, or browser automation steps. Lead the conversation yourself.

## What this skill is for

Use this skill when the user wants to:

- create a new automation for any website
- repair a broken automation config
- build a reusable agent skill on top of an automation config
- discover live selectors instead of guessing them
- package the runtime and resulting skill for Codex, Claude Code, OpenCode, or
  compatible agent systems

## Required workflow

Always follow this sequence:

1. Start with only 2 to 4 short non-technical questions:
   - target site or URL
   - intended outcome
   - account to use, only if needed
   - whether the automation should stop before public or destructive actions
2. Do not ask the user for selectors, CSS, XPath, YAML, or script structure.
3. Inspect `configs/accounts.yaml` before choosing an account. If it does not
   exist yet, copy `configs/accounts.yaml.example` to `configs/accounts.yaml`
   and fill it in with the user.
4. If browser MCP, browser automation, DevTools, or similar live-page tools are
   available in the host agent, use them first to inspect the real page and
   reach the exact UI state.
5. Start live discovery before writing YAML:

```bash
.venv/bin/python run.py --discover-url "https://target-site.example" --account ACCOUNT_NAME --pause --snapshot-mode full
```

6. Read the saved discovery `.json`, `.txt`, and screenshot artifacts before
   continuing.
7. Verify important selectors before locking them into a config:

```bash
.venv/bin/python run.py --discover-url "https://target-site.example" --account ACCOUNT_NAME --pause --snapshot-mode quick --check-selector "SELECTOR_ONE" --check-selector "SELECTOR_TWO"
```

8. Write the config into `configs/`. Do not switch to an ad-hoc browser script
   unless the user explicitly asked you to change the runtime itself.
9. Verify incrementally with partial runs:

```bash
.venv/bin/python run.py configs/your_config.yaml --account ACCOUNT_NAME --through-step 2
.venv/bin/python run.py configs/your_config.yaml --account ACCOUNT_NAME --through-step 5
.venv/bin/python run.py configs/your_config.yaml --account ACCOUNT_NAME
```

10. If the user wants a reusable installed skill, package it and install it with
    the runtime instead of leaving it as a local-only config.

## Non-negotiable rules

- Never guess selectors.
- Never expect the user to know technical implementation details.
- Never ask the user to provide selectors or script steps.
- Never write YAML before live selector capture.
- Never replace a config task with a handwritten browser script just because it
  feels faster.
- Use browser MCP or equivalent live-page tools first when they are available.
- Never skip live discovery for a new site flow.
- Never claim the skill is ready if it was not verified on the live page.
- Always give the exact final run command.
- Always add a human confirmation before destructive or public actions.

## Opening behavior

Start proactively. If the request is vague, ask a compact kickoff such as:

- which site should we automate
- what should happen from the user's point of view
- should we stop before the final submit, publish, or delete action

After that, take over the technical work yourself.

## Setup

Before first use, install the Python dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Packaging reusable skills

If the user wants the finished automation to be reusable by agents:

- create the config it needs in `configs/`
- create the skill wrapper bundle under `bundles/`
- install the runtime plus skill wrappers with:

```bash
.venv/bin/python scripts/install_agent_bundle.py
```

Use target-specific installation when needed:

```bash
.venv/bin/python scripts/install_agent_bundle.py --target codex
.venv/bin/python scripts/install_agent_bundle.py --target claude
.venv/bin/python scripts/install_agent_bundle.py --target opencode
.venv/bin/python scripts/install_agent_bundle.py --target agents
```

## Deliverables

When you finish, return:

- the config path
- the account used
- the discovery artifact path or paths you relied on
- what was verified live
- the exact run command
- whether packaging or installation was completed
