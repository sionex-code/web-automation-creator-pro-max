# Open Automation Creator Skill Guide for AI Agents

Read this entire file before creating or updating an automation in this repo.

This system builds config-driven browser automations with Patchright and YAML.
Your job is not to hand back a plausible config. Your job is to leave behind a
config that was discovered from the live page, verified step by step, and is
ready for the user to run.

This guide is intentionally explicit so even weaker models can follow it
mechanically. If you are unsure what to do next, stop generating code and go
back to live discovery.

## What success looks like

When the user asks for something like "build a LinkedIn posting skill", the
finished result must include all of the following:

1. You asked the user the minimum questions needed to define the automation.
2. You opened the real site in a browser profile and captured a live snapshot.
3. You identified selectors from the live page instead of guessing them.
4. You checked the important selectors before writing the final YAML.
5. You wrote the config into `configs/`.
6. You verified the config incrementally, not just in one final run.
7. You returned an exact run command and clearly stated what was tested.
8. If the user wants a reusable agent skill, you packaged it so it can be
   installed with the Open Automation Creator runtime into supported agent homes.

If you did not verify it on the live page, do not present it as finished.

## Hard-stop rules before you generate anything

Follow these rules literally:

- Do not start by drafting Patchright, Playwright, Puppeteer, or Selenium code.
- The default deliverable in this repo is a YAML config under `configs/`.
- If you do not have selectors from a live page, you are not ready to write
  YAML yet.
- If browser MCP, browser automation, DevTools, or similar live-page tools are
  available in the host agent, use them to inspect the real page first.
- After browser-tool inspection, still run this runtime's discovery flow so the
  repo contains saved snapshots, screenshots, and selector checks.
- If a selector is uncertain, do another discovery pass instead of guessing.
- If all you have is the user request plus your own memory, you do not know
  enough yet.

## Conversation style for normal users

Assume the user is not technical and should not have to understand selectors,
DOM structure, browser automation internals, or YAML layout.

Your job is to lead the conversation and ask only the minimum questions a
normal user can realistically answer.

Rules:

- Start with short, plain-language kickoff questions.
- Ask at most 2 to 4 questions before taking action.
- Ask only for business intent, not technical implementation details.
- Never ask the user to provide selectors, CSS paths, XPath, or step JSON.
- Never ask the user what script should be written.
- If you can inspect the site yourself, do that instead of asking the user to
  describe the UI.
- If the account can be discovered from `configs/accounts.yaml`, check it
  yourself before asking.
- Offer simple options when helpful, for example:
  `draft only`, `stop before publish`, or `publish after confirmation`.

Recommended kickoff questions:

1. What site or page should this automation work on?
2. What should happen from the user's point of view?
3. Which account should be used, if more than one exists?
4. Should the automation stop before any final public or destructive action?

Do not overwhelm the user with a long checklist up front.

## Repo map

```text
Open Automation Creator/
|- run.py                   # CLI entry point
|- core/
|  |- engine.py             # Step executor
|  |- browser.py            # Patchright browser manager
|  |- discovery.py          # Live page discovery and selector checks
|  |- snapshot.py           # JS page snapshots for LLM analysis
|  |- config_loader.py      # YAML parser and validation
|  |- interactive.py        # Runtime questions and confirmations
|  `- account_manager.py    # Multi-account profiles
|- configs/
|  |- accounts.yaml         # Account definitions
|  `- *.yaml                # Automation configs
|- output/discovery/        # Saved discovery snapshots and screenshots
`- profiles/                # Persistent browser profiles
```

## Mandatory workflow

Follow this sequence every time you build or repair an automation.

### 1. Ask focused setup questions

Ask only what you need to move forward. Usually that means:

- Which platform or URL?
- What exact outcome should happen?
- Which account should be used?
- What content or inputs are required?
- Should the automation stop for review before any destructive action?

For a LinkedIn posting automation, ask at least:

- Which LinkedIn account in `configs/accounts.yaml` should be used?
- What is the post topic or draft content?
- Should the automation stop before publishing or publish after confirmation?
- Will it include text only, image upload, or article/link attachment?

Important:

- Keep the opening message short.
- Use non-technical language.
- Do not ask for selectors or page structure.
- After these questions are answered, move directly into inspection and
  discovery.

### 2. Check account availability

Look in `configs/accounts.yaml` before building anything account-specific.

If the requested account is missing, add it first or ask for the missing
details. Do not continue with a fake or placeholder account name.

### 3. Start live discovery before writing YAML

Never guess selectors from memory.

If the host agent exposes browser MCP or similar browser tools, use them first
to:

- open the real site
- navigate to the exact UI state
- inspect candidate selectors and page structure
- note any modal, login, or branching behavior

Then run the Open Automation Creator discovery command below so the repo has
artifacts you can reuse and verify.

Use the discovery mode first:

```bash
.venv/bin/python run.py --discover-url "https://target-site.example" --account ACCOUNT_NAME --pause --snapshot-mode full
```

For LinkedIn posting, start here:

```bash
.venv/bin/python run.py --discover-url "https://www.linkedin.com/feed/" --account ACCOUNT_NAME --pause --snapshot-mode full
```

What this does:

- Opens a persistent browser profile
- Lets the user log in or navigate to the exact screen
- Captures a snapshot plus screenshot into `output/discovery/`
- Gives you real selectors from the current page

Read the saved discovery artifacts after the run. Use them as the source of
truth for the config you write.

Minimum artifacts to inspect before you continue:

- the saved discovery `.json`
- the saved discovery `.txt`
- the screenshot for visual confirmation

### 4. Check important selectors explicitly

Once you have likely selectors, verify them with discovery mode before locking
them into the final config.

Example:

```bash
.venv/bin/python run.py --discover-url "https://www.linkedin.com/feed/" --account ACCOUNT_NAME --pause --snapshot-mode quick --check-selector "button.share-box-feed-entry__trigger" --check-selector ".ql-editor" --check-selector "button.share-actions__primary-action"
```

Do this for the selectors that matter most:

- Main action trigger
- Editor/input field
- Submit button
- Success state indicator
- Any optional modal close or continuation button that commonly appears

If a selector fails, do another discovery pass and fix it before writing the
final YAML.

### 5. Write the config only after discovery

Create the final automation in `configs/NAME.yaml`.

Primary deliverable rules:

- The normal output is YAML config, not an ad-hoc browser script.
- Do not write Patchright, Playwright, Puppeteer, or Selenium code unless the
  user explicitly asked you to change the runtime itself.
- If the user asked for "an automation" and this runtime can express it, prefer
  config over one-off code.
- If selectors or state transitions are still uncertain, return to discovery
  instead of writing placeholders.

Rules:

- Use variables for dynamic content.
- Use `user_input` for anything the user may want to review or edit.
- Add `verify` after important transitions.
- Add `wait` after navigation and modal-opening clicks.
- Add `optional: true` only when the element is genuinely optional.
- Add a final confirmation step before any destructive or public action.
- Prefer `on_error: pause` so the user can recover live sessions manually.

### 6. Verify incrementally

Do not wait until the very end to find out the flow breaks at step 3.

Use partial runs:

```bash
.venv/bin/python run.py configs/your_config.yaml --account ACCOUNT_NAME --through-step 2
.venv/bin/python run.py configs/your_config.yaml --account ACCOUNT_NAME --through-step 5
.venv/bin/python run.py configs/your_config.yaml --account ACCOUNT_NAME --through-step 8
.venv/bin/python run.py configs/your_config.yaml --account ACCOUNT_NAME
```

Use `--from-step` when you need to resume later sections while debugging:

```bash
.venv/bin/python run.py configs/your_config.yaml --account ACCOUNT_NAME --from-step 5 --through-step 8
```

You are not done until the partial checks and the final run both make sense.

### 7. Deliver a runnable handoff

Your final response must include:

- The config path you created or updated
- The account name used
- The exact run command
- What you verified live
- Any remaining manual step such as login or final publish confirmation

Do not say "ready" unless it is actually ready.

### 8. Package reusable skills when requested

If the user wants the automation to be reusable in Codex, Claude Code,
OpenCode, or other agent environments, do not stop at a local config.

Package and install all of the following:

- The Open Automation Creator runtime itself
- The config the skill depends on
- The skill wrapper or agent wrapper for the target tool
- Clear install or restart instructions when the target app requires reload

For this repo, prefer adding an installer script that:

- Copies the runtime into a stable user-level location
- Installs Codex skills into `~/.codex/skills/`
- Installs OpenCode skills into `~/.config/opencode/skills/`
- Installs agent-compatible skills into `~/.agents/skills/`
- Installs Claude Code wrappers into `~/.claude/agents/`

If the runtime path is part of the instructions, generate wrappers that point
at the installed runtime path instead of the temporary working directory.

## Mechanical fallback for weaker models

When you are unsure, follow this exact loop in order:

1. Ask for the target URL, account, intended outcome, and any required content.
2. Inspect `configs/accounts.yaml`.
3. Use browser MCP or similar browser tools, if available, to open the live
   page and reach the exact screen.
4. Run `.venv/bin/python run.py --discover-url ... --pause --snapshot-mode full`.
5. Read the newest discovery `.json`, `.txt`, and screenshot artifacts.
6. Pull candidate selectors from those artifacts, not from memory.
7. Run discovery again with `--check-selector` for the important selectors.
8. Write the smallest YAML config that uses only verified selectors.
9. Validate early with `--through-step`.
10. Only mark the automation as finished after the partial checks and the final
    run both make sense.

Failure rule:

- If something does not match the live UI, rerun discovery.
- Do not patch selectors blindly.
- Do not replace the config with a handwritten browser script just because the
  first attempt failed.

## Quick-start script for the agent

If the user gives only a rough request such as "make an automation for X",
start like this:

1. Ask 2 to 4 short questions the user can answer.
2. Inspect `configs/accounts.yaml` yourself.
3. Inspect the live page with browser MCP or browser tools if available.
4. Run discovery and continue without asking the user for technical details.

Example opening:

"Which site should we automate, what should it do, and should it stop before
the final submit or publish action?"

## LinkedIn posting workflow

When the user asks for a LinkedIn posting automation, use this playbook.

### Discovery target

Start on:

```bash
.venv/bin/python run.py --discover-url "https://www.linkedin.com/feed/" --account ACCOUNT_NAME --pause --snapshot-mode full
```

### What to verify on the live page

Confirm selectors for:

- The "Start a post" or equivalent composer trigger
- The text editor surface
- The publish/post button
- A reliable success indicator after posting

If the user wants images or article links, also verify:

- File input selector or upload trigger
- Link/article attachment field
- Any intermediate modal button

### Required safety behavior

For LinkedIn posting, the config must:

- Let the user review generated content before typing it
- Ask for confirmation before the final publish click
- Verify the page state after publishing
- Save a screenshot after the publish step or final review step

If the site UI changes during testing, rerun discovery. Do not patch blindly.

## Runtime commands you should use

### Run a finished config

```bash
.venv/bin/python run.py configs/your_config.yaml --account ACCOUNT_NAME
```

### Run headless

```bash
.venv/bin/python run.py configs/your_config.yaml --account ACCOUNT_NAME --headless
```

### Auto-confirm non-destructive prompts

```bash
.venv/bin/python run.py configs/your_config.yaml --account ACCOUNT_NAME --auto
```

### Capture a fresh discovery snapshot

```bash
.venv/bin/python run.py --discover-url "https://target-site.example" --account ACCOUNT_NAME --pause --snapshot-mode full
```

### Test selectors during discovery

```bash
.venv/bin/python run.py --discover-url "https://target-site.example" --account ACCOUNT_NAME --pause --snapshot-mode quick --check-selector "SELECTOR_ONE" --check-selector "SELECTOR_TWO"
```

## Supported actions

Use these step actions in configs:

- `goto`
- `wait`
- `scroll`
- `click`
- `type`
- `press`
- `select`
- `upload`
- `snapshot`
- `verify`
- `extract`
- `js_eval`
- `save_data`
- `screenshot`
- `read_markdown`
- `set_content`
- `extract_published_link`
- `user_input`
- `llm_generate`
- `llm_decide`
- `conditional`
- `loop`
- `for_each`
- `load_json`
- `console_log`

## Config skeleton

Use this as a starting point after discovery, not before:

```yaml
name: "Descriptive automation name"
description: "What this automation does"
version: "1.0"

variables:
  topic: ""

settings:
  slow_mo: 80
  profile: "default"

on_error: pause

steps:
  - action: goto
    url: "https://example.com"
    description: "Open the target page"

  - action: snapshot
    mode: quick
    save_to_variable: page_state
    description: "Capture page state before interaction"

  - action: verify
    check: selector_exists
    selector: "CONFIRMED_SELECTOR"
    optional: true
    description: "Check that the expected UI is available"
```

## Non-negotiable rules

1. Never guess selectors.
2. Use browser MCP or equivalent live-page tools first when they are available.
3. Always use discovery mode before final YAML.
4. Always verify important selectors before final YAML.
5. Always verify the config incrementally with `--through-step`.
6. Always add a human confirmation before destructive or public actions.
7. Always tell the user exactly how to run the finished automation.
8. Do not replace a config task with a one-off browser script unless the user
   explicitly asked for code changes to the runtime.

If you follow these rules, the resulting automation is much more likely to be
usable on the first real run.
