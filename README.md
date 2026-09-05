# Web Automation Creator Pro Max

A powerful Claude agent skill for building, repairing, and packaging browser automations with the Open Automation Creator runtime. Create verified web automation scripts without manually writing selectors or YAML configurations.

## Overview

Web Automation Creator Pro Max is designed to help you build reliable browser automations through a guided workflow. The skill handles:

- Creating new automations for any website
- Repairing broken automation configurations
- Discovering and verifying live selectors from web pages
- Building reusable agent skills from automation configs
- Packaging automations for use with Claude Code, Codex, OpenCode, and compatible agent systems

## Key Features

- **Live Page Inspection**: Uses browser tooling and MCP to inspect real pages and capture actual selectors
- **Selector Verification**: Verifies important selectors before locking them into configs
- **No Guess Work**: Captures selectors from live pages instead of guessing CSS or XPath
- **User-Friendly**: Designed for non-technical users - no need to know selectors, YAML, or script structure
- **Incremental Verification**: Test your automations step-by-step before final runs
- **Reusable Packages**: Create installable skills for use across multiple systems

## Installation

### For Claude Code Users

Install this skill directly in Claude Code:

```bash
# The skill is available via the Claude Code skill registry
```

### For Manual Installation

1. Clone this repository:
```bash
git clone https://github.com/sionex-code/web-automation-creator-pro-max.git
```

2. Copy to your Claude Code skills directory:
```bash
cp -r web-automation-creator-pro-max ~/.claude/skills/
```

3. Restart Claude Code to see the skill available

## Usage

### Quick Start

Invoke the skill with:
```
/automation-creator-builder
```

Or type the command and describe what you want to automate.

### Typical Workflow

1. **Describe Your Goal**: Tell the skill what website and outcome you need
   - The skill asks 2-4 short non-technical questions
   - Answer with natural language (no technical details needed)

2. **Live Discovery**: The skill inspects the target website
   - Uses browser tools to navigate to the page
   - Captures and screenshots the UI elements
   - Identifies interactive elements automatically

3. **Selector Verification**: Important selectors are tested on the live page
   - The skill shows you what it found
   - Verifies each selector works correctly
   - Makes adjustments if needed

4. **Config Generation**: The skill writes an automation configuration
   - Creates a YAML config ready to use
   - No manual editing needed

5. **Incremental Testing**: Run the automation step-by-step
   - Test first 2 steps, then first 5, then full run
   - Verify each stage works before moving forward
   - Stop before any destructive actions for safety

6. **Packaging (Optional)**: Convert to a reusable installable skill
   - Package the automation for team use
   - Install across Codex, Claude Code, OpenCode, or compatible systems

## Examples

### Example 1: Scraping a Website

```
I want to scrape product names and prices from an e-commerce site
```

The skill will:
- Ask which site and what output format you need
- Navigate to the page and discover selectors for product names and prices
- Create a config to extract and save the data
- Test it step by step

### Example 2: Form Filling

```
I need to fill out a contact form and submit it
```

The skill will:
- Ask for the form URL and details to fill in
- Discover form field selectors
- Create a config to populate and submit the form
- Stop before submission for your confirmation

### Example 3: Repairing a Broken Automation

```
This automation used to work but now fails
```

Provide your existing config and the skill will:
- Test it on the live page
- Find what broke (selector changes, page layout updates)
- Update selectors and fix the configuration
- Verify the repair works

## How It Works

The skill leverages the **Open Automation Creator** runtime to:

1. **Navigate and Inspect**: Visits target websites using a real browser
2. **Capture Selectors**: Records CSS selectors and XPath expressions from live elements
3. **Generate Configs**: Creates YAML automation configurations automatically
4. **Test Incrementally**: Runs automations step-by-step with verification checkpoints
5. **Package for Reuse**: Wraps automations into installable skills

## Configuration Files

### agents/openai.yaml

Defines the skill interface for OpenAI-compatible agent systems:

```yaml
interface:
  display_name: "Open Automation Creator Builder"
  short_description: "Create verified browser automation skills"
  default_prompt: "Build or repair a browser automation skill..."
```

### SKILL.md

The main skill definition containing:
- Complete workflow documentation
- Non-negotiable rules for reliability
- Packaging instructions
- Deliverables checklist

## Requirements

- Claude Code or compatible agent system
- Open Automation Creator runtime installed locally
- Access to live websites you want to automate
- Python 3.8 or higher (for the automation runtime)

## Non-Negotiable Rules

These rules ensure your automations are reliable and safe:

1. Never guess selectors without live page inspection
2. Never ask users for technical implementation details
3. Never write configs before capturing real selectors
4. Never replace config tasks with handwritten scripts
5. Always verify selectors work on the live page
6. Always test automations before final runs
7. Always request confirmation before destructive actions

## Packaging for Distribution

To package this skill for use across multiple systems:

```bash
cd /path/to/automation-runtime
.venv/bin/python scripts/install_agent_bundle.py
```

For specific targets:
```bash
.venv/bin/python scripts/install_agent_bundle.py --target claude
.venv/bin/python scripts/install_agent_bundle.py --target codex
.venv/bin/python scripts/install_agent_bundle.py --target opencode
```

## Troubleshooting

### Selectors Not Found
- Ensure the page has fully loaded before the skill runs discovery
- Check if the website requires authentication
- Verify the page layout matches what you expect

### Automation Fails After Page Updates
- Run the skill again to discover updated selectors
- Common cause: websites redesign or move elements
- The skill can repair broken automations automatically

### Account-Specific Issues
- Verify account credentials are correctly configured in accounts.yaml
- Check if the account needs password reset or two-factor authentication
- Test account access manually first

## Support

For issues, questions, or to contribute:

1. Create an issue on GitHub with details of what went wrong
2. Include the page URL and what you were trying to automate
3. Attach any error messages or discovery artifacts
4. Describe the expected vs actual outcome

## License

This project is provided as-is for use with Claude Code and compatible agent systems.

## Related Resources

- [Open Automation Creator Documentation](https://github.com/your-org/open-automation-creator)
- [Claude Code Documentation](https://claude.ai/code)
- [Agent Skills Guide](https://anthropic.com)

## Contributing

To improve this skill:

1. Test new website automation patterns
2. Share working configs and examples
3. Report selector issues on specific websites
4. Suggest workflow improvements

## Changelog

### Version 1.0 (2026-09-05)
- Initial public release
- Live page inspection with browser tools
- Automatic selector discovery and verification
- YAML config generation
- Incremental testing workflow
- Packaging for multiple agent systems
