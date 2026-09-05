# Install Open Automation Creator As A Reusable Skill

This repo can install:

- the full Open Automation Creator runtime
- a general Open Automation Creator builder skill for supported agents
- the reusable Facebook group discovery and posting skill wrappers for supported agents
- the reusable LinkedIn article publishing skill wrappers for supported agents
- the reusable Pastebin and Medium publishing skill wrappers for supported agents

## What gets installed

Running the installer copies the runtime to:

`~/.open-automation-creator`

It also installs wrappers here:

- Codex general builder: `~/.codex/skills/automation-creator-builder`
- OpenCode general builder: `~/.config/opencode/skills/automation-creator-builder`
- Agent-compatible general builder: `~/.agents/skills/automation-creator-builder`
- Claude Code general builder agent: `~/.claude/agents/automation-creator-builder.md`
- Claude-compatible general builder skill: `~/.claude/skills/automation-creator-builder`

The same pattern repeats for each bundle (`linkedin-markdown-article-publisher`, `facebook-group-poster`, `pastebin`, `medium-markdown-story-publisher`) under the matching target directory.

## Main install command

From this repo, run:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/install_agent_bundle.py
```

## Restart apps

Restart these apps after installation so they reload the new skill or agent:

- Codex
- Claude Code
- OpenCode

## Useful installer options

Dry run only:

```bash
.venv/bin/python scripts/install_agent_bundle.py --dry-run
```

Install only for one target:

```bash
.venv/bin/python scripts/install_agent_bundle.py --target codex
.venv/bin/python scripts/install_agent_bundle.py --target claude
.venv/bin/python scripts/install_agent_bundle.py --target opencode
.venv/bin/python scripts/install_agent_bundle.py --target agents
```

Install to a different runtime location:

```bash
.venv/bin/python scripts/install_agent_bundle.py --runtime-dest "/path/to/custom-location"
```

Skip copying browser profiles:

```bash
.venv/bin/python scripts/install_agent_bundle.py --skip-profiles
```

Install only specific bundles:

```bash
.venv/bin/python scripts/install_agent_bundle.py --bundle automation-creator-builder pastebin
```

## What the installed skill does

The installed general Open Automation Creator builder skill can:

- create new automation configs for any website
- run live discovery to find real selectors
- verify selectors before writing final YAML
- validate configs incrementally
- package reusable skills for agents

The installed LinkedIn skill can:

- read a local markdown file
- open LinkedIn with the configured account
- import Cookie-Editor cookies if the session is logged out
- fill the LinkedIn article title and body
- publish the article
- return the published URL

The installed Facebook skill can:

- open Facebook group discovery pages and save visible groups to JSON
- select relevant groups from a saved catalog based on the post topic or content
- open each selected group and attempt to publish the provided content
- save discovery, selection, and posting artifacts for later reuse

## Notes for agents

- Use the installed runtime path, not the temporary repo path: `~/.open-automation-creator`
- If your agent has browser MCP, browser-use, DevTools, or similar browser
  tooling, inspect the real page with that first, then persist the findings
  with `.venv/bin/python run.py --discover-url ...`
- Use `configs/facebook_group_discovery.yaml` to capture a reusable group catalog
- Use `scripts/select_facebook_groups.py` to narrow that catalog to relevant groups
- Use `configs/facebook_group_post_to_saved_groups.yaml` to publish content to the selected groups
- Reuse the existing config: `configs/linkedin_markdown_article_publish.yaml`
- Do not rediscover selectors unless the current config fails
- Do not write a guessed browser script when the task fits the YAML runtime
- If multiple LinkedIn accounts exist, choose the right account or ask
- If LinkedIn is logged out, request Cookie-Editor export JSON for `linkedin.com`

## Installer script

Installer path (relative to this repo):

`scripts/install_agent_bundle.py`
