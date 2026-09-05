# Web Automation Creator Pro Max

A complete browser automation runtime plus a cross-agent skill on top of it. Clone this repository and you have everything needed to build, run, repair, and package browser automations, no separate download required. It works with Claude Code, Codex, Antigravity, OpenCode, and other compatible agent systems, and just as well from a plain terminal.

Instead of guessing CSS selectors or hand-writing scripts, the runtime inspects the live page, captures real selectors, verifies them, and only then generates a runnable automation config.

## Table of Contents

- [Supported Agents](#supported-agents)
- [Overview](#overview)
- [Key Features](#key-features)
- [Installation](#installation)
- [Usage](#usage)
- [Direct CLI Usage](#direct-cli-usage)
- [Workflow](#workflow)
- [Examples](#examples)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Core Rules](#core-rules)
- [Packaging for Multiple Agents](#packaging-for-multiple-agents)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Supported Agents

| Agent System | Status | Notes |
|---|---|---|
| Claude Code | Supported | Install as a skill under `~/.claude/skills` |
| Codex | Supported | Install via the `codex` packaging target |
| Antigravity | Supported | Install via the generic `agents` packaging target |
| OpenCode | Supported | Install via the `opencode` packaging target |
| Other agent systems | Supported | Any system that can read a skill bundle and run a Python runtime can use the generic `agents` target |

## Overview

Web Automation Creator Pro Max is built around one principle: an automation is only trustworthy if it was verified on the real page. The skill leads a short, non-technical conversation with the user, then takes over all the technical work: page inspection, selector discovery, config writing, and incremental testing.

It handles:

- Creating new automations for any website
- Repairing automations that broke after a site update
- Discovering and verifying live selectors instead of guessing them
- Generating reusable YAML configs
- Packaging the runtime and configs into an installable skill for multiple agent platforms

## Key Features

- **Live page inspection**: uses browser automation and MCP tooling to load the real page and read its actual structure
- **Verified selectors**: every selector is checked against the live page before it is written into a config
- **No blind scripting**: never falls back to a handwritten script just because it seems faster
- **Non-technical front end**: the user answers plain-language questions, never selectors, XPath, or YAML
- **Incremental execution**: automations are tested in small steps before a full run
- **Safety checkpoints**: execution pauses before destructive or public actions (submit, publish, delete)
- **Multi-agent packaging**: one config can be installed across Claude Code, Codex, Antigravity, OpenCode, and other systems

## Installation

No manual setup is required. Copy the prompt for your agent below, paste it in, and let the agent install itself. It will clone the repository, read the skill definition, and configure everything correctly for its own platform.

### Claude Code

```
Clone https://github.com/sionex-code/web-automation-creator-pro-max into a temp
folder, read its SKILL.md and README.md, then install it as a Claude Code
skill under ~/.claude/skills so I can use it as /automation-creator-builder.
Set up any runtime dependencies it needs and confirm it is ready to use.
```

### Codex

```
Clone https://github.com/sionex-code/web-automation-creator-pro-max, read its
SKILL.md and README.md, and install it for yourself as a Codex skill using
its packaging script with the codex target. Set up any dependencies it needs
and confirm it is ready to use.
```

### Antigravity

```
Clone https://github.com/sionex-code/web-automation-creator-pro-max, read its
SKILL.md and README.md, and install it for yourself using its packaging
script with the generic agents target. Set up any dependencies it needs and
confirm it is ready to use.
```

### OpenCode

```
Clone https://github.com/sionex-code/web-automation-creator-pro-max, read its
SKILL.md and README.md, and install it for yourself as an OpenCode skill
using its packaging script with the opencode target. Set up any dependencies
it needs and confirm it is ready to use.
```

### Any Other Compatible Agent System

```
Clone https://github.com/sionex-code/web-automation-creator-pro-max and read
its SKILL.md and README.md. Figure out how your platform loads skills, then
install this one for yourself using its packaging script (the generic agents
target works if nothing more specific applies). Set up any dependencies it
needs and confirm it is ready to use.
```

## Usage

Once installed, invoke the skill in natural language. For example:

```
Build an automation that logs into my dashboard and downloads the monthly report
```

The skill starts the conversation, so no special syntax is required beyond describing the goal.

## Direct CLI Usage

The runtime works on its own, without any agent in the loop, if you want to drive it by hand.

```bash
git clone https://github.com/sionex-code/web-automation-creator-pro-max.git
cd web-automation-creator-pro-max
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Discover selectors on a live page
.venv/bin/python run.py --discover-url "https://example.com" --pause --snapshot-mode full

# Verify a specific selector
.venv/bin/python run.py --discover-url "https://example.com" --check-selector "#login-button"

# Run a config, one step at a time, then in full
.venv/bin/python run.py configs/scrape_example.yaml --through-step 2
.venv/bin/python run.py configs/scrape_example.yaml
```

Copy `configs/accounts.yaml.example` to `configs/accounts.yaml` and fill in your own accounts before running configs that need a login.

## Workflow

The skill always follows the same sequence, regardless of host agent.

1. **Short intake**: asks 2 to 4 plain-language questions
   - Which site or URL
   - What outcome you want
   - Which account to use, if any
   - Whether to stop before a public or destructive action

2. **Live discovery**: opens the real page and captures its structure
   - Uses browser or MCP tooling when available
   - Saves screenshots and structured discovery artifacts

3. **Selector verification**: checks each important selector against the live page before using it

4. **Config generation**: writes a YAML automation config from verified selectors only

5. **Incremental testing**: runs the automation in stages
   - First few steps
   - A larger partial run
   - The full run, once earlier stages pass

6. **Packaging (optional)**: wraps the finished automation into an installable skill for one or more agent systems

## Examples

### Scraping structured data

Request:
```
Scrape product names and prices from this category page
```

Result: the skill discovers the product listing selectors, verifies them, writes a config, and runs it in stages to confirm the extracted data is correct.

### Filling and submitting a form

Request:
```
Fill out this contact form with the details I give you
```

Result: the skill discovers each form field selector, confirms them, fills the form, and pauses before the final submit step for confirmation.

### Repairing a broken automation

Request:
```
This automation worked last month but fails now
```

Result: the skill re-runs discovery on the live page, finds which selectors changed, updates the config, and verifies the repair before handing it back.

## Project Structure

```
web-automation-creator-pro-max/
  SKILL.md                 Skill definition and required workflow
  RUNTIME_GUIDE.md          Full reference guide for the runtime (source of truth)
  INSTALL_SKILL.md          Step by step install and packaging reference
  run.py                    CLI entry point for discovery and running configs
  requirements.txt          Python dependencies
  agents/
    openai.yaml              Interface definition for OpenAI-compatible agents
  core/
    engine.py                 Runs automation configs step by step
    discovery.py               Live page inspection and selector discovery
    snapshot.py                 Compact page-state capture
    browser.py                  Browser session management
    account_manager.py          Loads and resolves accounts.yaml
    config_loader.py            Parses and validates YAML configs
    interactive.py              Pause and confirm prompts
    markdown_tools.py           Markdown file handling for publishing configs
    console.py                  Terminal output formatting
  scripts/
    install_agent_bundle.py      Packages and installs skills for every target
    select_facebook_groups.py    Narrows a saved group catalog by relevance
  bundles/
    facebook-group-poster/        Skill template for Facebook group posting
    linkedin-markdown-article-publisher/  Skill template for LinkedIn publishing
    medium-markdown-story-publisher/      Skill template for Medium publishing
    pastebin/                      Skill template for Pastebin publishing
  configs/
    accounts.yaml.example          Template for your own accounts.yaml
    scrape_example.yaml            Minimal scraping example
    linkedin_*.yaml                 LinkedIn posting and publishing examples
    pastebin_*.yaml                  Pastebin publishing examples
    medium_markdown_story_publish.yaml  Medium publishing example
    facebook_group_*.yaml            Facebook group discovery and posting examples
  README.md
  LICENSE
```

Running the runtime creates a few local directories that are never committed: `configs/accounts.yaml` (your real credentials), `profiles/` (browser session data), `screenshots/`, and `output/`. These are already listed in `.gitignore`.

## Requirements

- Python 3.9 or higher
- Network access to the websites you intend to automate
- Optional: a host agent system such as Claude Code, Codex, Antigravity, or OpenCode, if you want the guided conversational workflow instead of driving the CLI directly

## Core Rules

These rules apply regardless of which agent system runs the skill.

1. Never guess a selector. Every selector must come from live page inspection.
2. Never ask the user for selectors, CSS, XPath, or YAML.
3. Never write a config before selectors are captured and verified.
4. Never substitute a handwritten script for a proper config, even if it seems quicker.
5. Always prefer browser or MCP tooling for live inspection when it is available.
6. Always verify an automation incrementally before a full run.
7. Always pause for human confirmation before a destructive or public action.

## How the Installation Prompts Work

Under the hood, every installation prompt above runs the same packaging script. This is what your agent executes on your behalf, so you never have to run it manually.

```bash
# Install for every supported target at once
.venv/bin/python scripts/install_agent_bundle.py

# Install for one specific target
.venv/bin/python scripts/install_agent_bundle.py --target claude
.venv/bin/python scripts/install_agent_bundle.py --target codex
.venv/bin/python scripts/install_agent_bundle.py --target opencode
.venv/bin/python scripts/install_agent_bundle.py --target agents
```

The `agents` target is the generic one, used for Antigravity and any other framework without a dedicated target. It produces a portable bundle rather than a platform-specific one. You only need these commands directly if you are scripting the install yourself instead of asking your agent to do it.

## Troubleshooting

**Selectors are not found during discovery**
- Confirm the page has fully loaded before discovery runs
- Check whether the page requires authentication first
- Confirm the page layout matches what was expected

**An automation that used to work now fails**
- Re-run discovery on the live page to capture updated selectors
- This is usually caused by a site redesign or an element being moved
- The skill can repair the config automatically once new selectors are captured

**Account-related failures**
- Confirm credentials in `configs/accounts.yaml` are current
- Check for password resets or two-factor authentication prompts
- Test the account manually in a browser before retrying

## Contributing

Contributions are welcome. Useful ways to help:

- Report selector issues on specific websites
- Share working configs for common automation patterns
- Suggest improvements to the discovery or verification workflow
- Add support for additional agent platforms

Please open an issue with the target site, the goal of the automation, and any error output or discovery artifacts.

## License

Released under the MIT License. See [LICENSE](LICENSE) for details.
