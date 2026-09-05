# Web Automation Creator Pro Max

A complete browser automation runtime with an agent skill built on top of it. Clone this repository and you have everything needed to discover, build, run, repair, and package browser automations, no separate download required.

It runs two ways:

1. **Directly from the command line**, driving the runtime yourself
2. **Through an agent** (Claude Code, Codex, Antigravity, OpenCode, or another compatible system), which leads a short conversation and does the technical work for you

Either way, the same principle applies: an automation is only trustworthy once it has been verified against the real page. The runtime inspects the live page, captures real selectors, verifies them, and only then generates a runnable automation config. It never guesses.

## Table of Contents

- [Supported Agents](#supported-agents)
- [Key Features](#key-features)
- [Quick Start (Command Line)](#quick-start-command-line)
- [Agent Installation](#agent-installation)
- [Using the Skill Through an Agent](#using-the-skill-through-an-agent)
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

| Agent System | Notes |
|---|---|
| Claude Code | Installs as a skill under `~/.claude/skills` |
| Codex | Installs via the `codex` packaging target |
| Antigravity | Installs via the generic `agents` packaging target |
| OpenCode | Installs via the `opencode` packaging target |
| Other agent systems | Any system that can load a skill bundle and run a local Python process can use the generic `agents` target |

The runtime itself has no agent dependency. Everything above is optional convenience on top of it.

## Key Features

- **Live page inspection**: uses browser automation and MCP tooling to load the real page and read its actual structure
- **Verified selectors**: every selector is checked against the live page before it is written into a config
- **No blind scripting**: never falls back to a handwritten script just because it seems faster
- **Non-technical front end**: when driven by an agent, the user answers plain-language questions, never selectors, XPath, or YAML
- **Incremental execution**: automations are tested in small steps before a full run
- **Safety checkpoints**: execution pauses before destructive or public actions such as submit, publish, or delete
- **Multi-agent packaging**: one automation can be installed across Claude Code, Codex, Antigravity, OpenCode, and other systems

## Quick Start (Command Line)

This is the foundation everything else builds on. It works with no agent involved.

```bash
git clone https://github.com/sionex-code/web-automation-creator-pro-max.git
cd web-automation-creator-pro-max

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Set up your accounts, if any automation needs a login:

```bash
cp configs/accounts.yaml.example configs/accounts.yaml
# edit configs/accounts.yaml with your own details
```

Discover real selectors on a live page:

```bash
.venv/bin/python run.py --discover-url "https://example.com" --pause --snapshot-mode full
```

Verify a specific selector before trusting it:

```bash
.venv/bin/python run.py --discover-url "https://example.com" --check-selector "#login-button"
```

Run a config incrementally, then in full:

```bash
.venv/bin/python run.py configs/scrape_example.yaml --through-step 2
.venv/bin/python run.py configs/scrape_example.yaml
```

## Agent Installation

If you want the guided, conversational version of this workflow, install the skill into your agent of choice. Paste the matching prompt below and let the agent handle it. Each one clones the repository, sets up the runtime from the Quick Start steps above, and registers the skill in the right place for that platform.

### Claude Code

```
Clone https://github.com/sionex-code/web-automation-creator-pro-max into a temp
folder, read its SKILL.md and README.md, then install it as a Claude Code
skill under ~/.claude/skills so I can use it as /automation-creator-builder.
Set up the Python virtual environment and dependencies, then confirm it is
ready to use.
```

### Codex

```
Clone https://github.com/sionex-code/web-automation-creator-pro-max, read its
SKILL.md and README.md, and install it for yourself as a Codex skill using
its packaging script with the codex target. Set up the Python virtual
environment and dependencies, then confirm it is ready to use.
```

### Antigravity

```
Clone https://github.com/sionex-code/web-automation-creator-pro-max, read its
SKILL.md and README.md, and install it for yourself using its packaging
script with the generic agents target. Set up the Python virtual environment
and dependencies, then confirm it is ready to use.
```

### OpenCode

```
Clone https://github.com/sionex-code/web-automation-creator-pro-max, read its
SKILL.md and README.md, and install it for yourself as an OpenCode skill
using its packaging script with the opencode target. Set up the Python
virtual environment and dependencies, then confirm it is ready to use.
```

### Any Other Compatible Agent System

```
Clone https://github.com/sionex-code/web-automation-creator-pro-max and read
its SKILL.md and README.md. Figure out how your platform loads skills, then
install this one for yourself using its packaging script (the generic agents
target works if nothing more specific applies). Set up the Python virtual
environment and dependencies, then confirm it is ready to use.
```

## Using the Skill Through an Agent

Once installed, describe the goal in plain language. For example:

```
Build an automation that logs into my dashboard and downloads the monthly report
```

The agent asks a few short, non-technical questions, then handles page inspection, selector discovery, config writing, and testing on its own.

## Workflow

Both the command line and the agent-driven skill follow the same sequence.

1. **Short intake**: which site, what outcome, which account if any, and whether to stop before a public or destructive action
2. **Live discovery**: opens the real page and captures its structure, using browser or MCP tooling when available, saving screenshots and structured artifacts
3. **Selector verification**: checks each important selector against the live page before using it
4. **Config generation**: writes a YAML automation config from verified selectors only
5. **Incremental testing**: runs the automation in stages, first a few steps, then a larger partial run, then the full run once earlier stages pass
6. **Packaging (optional)**: wraps the finished automation into an installable skill for one or more agent systems

## Examples

### Scraping structured data

Request:
```
Scrape product names and prices from this category page
```

Result: selectors for the product listing are discovered and verified, a config is written, and it runs in stages to confirm the extracted data is correct.

### Filling and submitting a form

Request:
```
Fill out this contact form with the details I give you
```

Result: each form field selector is discovered and confirmed, the form is filled, and execution pauses before the final submit step for confirmation.

### Repairing a broken automation

Request:
```
This automation worked last month but fails now
```

Result: discovery re-runs on the live page, the changed selectors are found, the config is updated, and the repair is verified before being handed back.

## Project Structure

```
web-automation-creator-pro-max/
  SKILL.md                    Agent skill definition and required workflow
  RUNTIME_GUIDE.md             Full reference guide for the runtime
  INSTALL_SKILL.md             Step by step install and packaging reference
  run.py                       CLI entry point for discovery and running configs
  requirements.txt             Python dependencies
  agents/
    openai.yaml                 Interface definition for OpenAI-compatible agents
  core/
    engine.py                    Runs automation configs step by step
    discovery.py                  Live page inspection and selector discovery
    snapshot.py                    Compact page-state capture
    browser.py                     Browser session management
    account_manager.py             Loads and resolves accounts.yaml
    config_loader.py                Parses and validates YAML configs
    interactive.py                  Pause and confirm prompts
    markdown_tools.py               Markdown file handling for publishing configs
    console.py                      Terminal output formatting
  scripts/
    install_agent_bundle.py         Packages and installs skills for every target
    select_facebook_groups.py       Narrows a saved group catalog by relevance
  bundles/
    facebook-group-poster/           Skill template for Facebook group posting
    linkedin-markdown-article-publisher/  Skill template for LinkedIn publishing
    medium-markdown-story-publisher/       Skill template for Medium publishing
    pastebin/                          Skill template for Pastebin publishing
  configs/
    accounts.yaml.example              Template for your own accounts.yaml
    scrape_example.yaml                Minimal scraping example
    linkedin_*.yaml                     LinkedIn posting and publishing examples
    pastebin_*.yaml                      Pastebin publishing examples
    medium_markdown_story_publish.yaml   Medium publishing example
    facebook_group_*.yaml                Facebook group discovery and posting examples
  README.md
  LICENSE
```

Running the runtime creates local directories that are never committed: `configs/accounts.yaml` holds your real credentials, `profiles/` holds browser session data, and `screenshots/` and `output/` hold run artifacts. All four are already listed in `.gitignore`.

## Requirements

- Python 3.9 or higher
- Network access to the websites you intend to automate
- Optional: a host agent system such as Claude Code, Codex, Antigravity, or OpenCode, if you want the guided conversational workflow instead of driving the CLI directly

## Core Rules

These rules hold regardless of whether the runtime is driven by hand or by an agent.

1. Never guess a selector. Every selector must come from live page inspection.
2. Never ask the user for selectors, CSS, XPath, or YAML.
3. Never write a config before selectors are captured and verified.
4. Never substitute a handwritten script for a proper config, even if it seems quicker.
5. Always prefer browser or MCP tooling for live inspection when it is available.
6. Always verify an automation incrementally before a full run.
7. Always pause for human confirmation before a destructive or public action.

## Packaging for Multiple Agents

A single automation, or the whole runtime, can be packaged once and installed everywhere. This is the script every agent installation prompt above runs on your behalf.

```bash
# Install for every supported target at once
.venv/bin/python scripts/install_agent_bundle.py

# Install for one specific target
.venv/bin/python scripts/install_agent_bundle.py --target claude
.venv/bin/python scripts/install_agent_bundle.py --target codex
.venv/bin/python scripts/install_agent_bundle.py --target opencode
.venv/bin/python scripts/install_agent_bundle.py --target agents

# Install only specific bundled skills
.venv/bin/python scripts/install_agent_bundle.py --bundle automation-creator-builder pastebin

# Preview what would happen without writing anything
.venv/bin/python scripts/install_agent_bundle.py --dry-run
```

The `agents` target is the generic one, used for Antigravity and any other framework without a dedicated target. It produces a portable bundle rather than a platform-specific one. See `INSTALL_SKILL.md` for the full list of options.

## Troubleshooting

**Selectors are not found during discovery**
- Confirm the page has fully loaded before discovery runs
- Check whether the page requires authentication first
- Confirm the page layout matches what was expected

**An automation that used to work now fails**
- Re-run discovery on the live page to capture updated selectors
- This is usually caused by a site redesign or an element being moved
- The runtime can repair the config once new selectors are captured

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
