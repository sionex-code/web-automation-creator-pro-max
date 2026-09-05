---
name: linkedin-markdown-article-publisher
description: Publish a local Markdown file as a LinkedIn article using the Open Automation Creator runtime at {{RUNTIME_ROOT}}. Use when the user wants LinkedIn article publishing from a .md file, including loading the file, preserving basic formatting, filling the LinkedIn title/body fields, publishing, and returning the published URL. Prefer this skill over ad-hoc LinkedIn browser scripting in this environment.
---

# LinkedIn Markdown Article Publisher

Use the deterministic LinkedIn article flow in the Open Automation Creator runtime at `{{RUNTIME_ROOT}}`.

Do not use subagents for this skill.
Do not add `llm_generate` or `llm_decide` steps to the runtime path.

## Inputs to confirm

Confirm these before running:

- Absolute path to the markdown file.
- LinkedIn account name from `configs/accounts.yaml`.
- Whether the saved LinkedIn profile is already logged in.
- Whether the run should stop before publishing or publish immediately.

Default account: `main_linkedin`
Default runtime path: `{{RUNTIME_ROOT}}`

If the runtime has moved, ask for the new path before continuing.

## Main workflow

1. Change into the runtime:

```bash
cd "{{RUNTIME_ROOT}}"
```

2. Ensure dependencies are installed:

```bash
.venv/bin/pip install -r requirements.txt
```

3. If LinkedIn is not logged in, ask the user to export cookies from
Cookie-Editor for `linkedin.com` and paste the JSON when the runtime asks for
it. The config imports those cookies before retrying the feed.

4. Resolve the LinkedIn account before publishing:

- Inspect `configs/accounts.yaml`.
- Filter accounts where `platform: linkedin`.
- If exactly one LinkedIn account exists, let the runtime auto-use it.
- If multiple LinkedIn accounts exist and the user names one, pass
  `--account that_name`.
- If multiple LinkedIn accounts exist and the user does not identify one, ask
  which account to use. Do not guess between multiple LinkedIn accounts.

5. Validate the deterministic publisher config:

Config path:
`configs/linkedin_markdown_article_publish.yaml`

Non-destructive partial run:

```bash
.venv/bin/python run.py configs/linkedin_markdown_article_publish.yaml --account main_linkedin --through-step 11 --set markdown_path="~/article.md"
```

6. Publish the article when the user wants the final run:

```bash
.venv/bin/python run.py configs/linkedin_markdown_article_publish.yaml --account main_linkedin --set markdown_path="~/article.md" --set publish_decision=publish
```

7. Return the published URL from one of these sources:

- The terminal output line that prints `Published link: ...`
- `output/linkedin_last_published_link_<account_name>.txt`

## Behavior notes

- The runtime reads the markdown file locally and derives the title from the
  first H1 if present.
- The runtime converts markdown to HTML before inserting the article body into
  LinkedIn.
- The runtime can import Cookie-Editor JSON exports when the LinkedIn profile
  is logged out.
- The runtime auto-selects the only LinkedIn account when exactly one exists.
- The runtime raises a clear error when multiple LinkedIn accounts exist and
  `--account` was omitted.
- The runtime asks for manual intervention only when the LinkedIn session,
  editor state, or published-link extraction cannot be resolved automatically.
- The safest default is to validate through the editor-open steps before
  running the publish command.

## What not to do

- Do not rewrite the article with an LLM unless the user explicitly asks for
  writing help.
- Do not create a second LinkedIn publishing flow if
  `configs/linkedin_markdown_article_publish.yaml` already fits.
- Do not claim the automation is fully verified if the profile is still on
  LinkedIn's login page.
