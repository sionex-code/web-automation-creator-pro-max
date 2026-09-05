---
name: medium-markdown-story-publisher
description: Publish a local Markdown file to Medium as a fully formatted story with a cover image, using the Open Automation Creator runtime at {{RUNTIME_ROOT}}. Use when the user wants to post or publish an article to Medium from a .md file, including title, headings, lists, quotes, code blocks, links, cover/preview image, topics, paywall setting, and returning the draft or published URL. Prefer this skill over ad-hoc Medium browser scripting in this environment.
---

# Medium Markdown Story Publisher

Use the deterministic Medium story flow in the Open Automation Creator runtime at `{{RUNTIME_ROOT}}`.

Do not use subagents for this skill.
Do not add `llm_generate` or `llm_decide` steps to the runtime path.

## Inputs to confirm

Confirm these before running:

- Absolute path to the markdown file.
- Absolute path to the cover image, or that there is no cover image.
- Whether the run should stop at the draft or publish after confirmation.
- Topics (up to five, comma separated) if the user wants them.
- Whether the story should be paywalled (member-only). Default is not paywalled.

Default account: `main_medium`
Default runtime path: `{{RUNTIME_ROOT}}`
Config: `configs/medium_markdown_story_publish.yaml`

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

3. Resolve the Medium account:

- Inspect `configs/accounts.yaml`.
- Filter accounts where `platform: medium`.
- If exactly one exists, let the runtime auto-use it.
- If the user names one, pass `--account that_name`.
- If several exist and the user does not identify one, ask. Do not guess.

4. Draft-only run (safe, stops at the draft):

```bash
.venv/bin/python run.py configs/medium_markdown_story_publish.yaml --account main_medium \
  --set markdown_path="/absolute/path/story.md" \
  --set cover_image_path="/absolute/path/cover.png" \
  --set publish_decision=draft
```

5. Interactive run (the runtime asks "publish" or keep as draft at the end):

```bash
.venv/bin/python run.py configs/medium_markdown_story_publish.yaml --account main_medium \
  --set markdown_path="/absolute/path/story.md" \
  --set cover_image_path="/absolute/path/cover.png"
```

6. Publish without the prompt, when the user explicitly asks for it:

```bash
.venv/bin/python run.py configs/medium_markdown_story_publish.yaml --account main_medium \
  --set markdown_path="/absolute/path/story.md" \
  --set cover_image_path="/absolute/path/cover.png" \
  --set topics="automation, python" \
  --set publish_decision=publish
```

7. Skip the cover image with `--set cover_image_path=skip`.
8. Keep Medium's paywall on with `--set paywall=yes`.

9. Return the resulting URL from one of these sources:

- Terminal line `Draft saved: ...` or `Published: ...`
- `output/medium_last_draft_url_<account_name>.txt`
- `output/medium_last_published_url_<account_name>.txt`
- Screenshots in `screenshots/medium_draft_<account>.png`, `screenshots/medium_published_<account>.png`

## How the flow works

- `read_markdown` derives the title from the first H1 and converts the rest to HTML.
- The HTML is loaded into an off-screen holder element, cleaned, and copied to the
  real clipboard, then pasted into the Medium editor with `Control+V`. Medium
  converts the paste into its own blocks, so headings, bullets, numbered lists,
  blockquotes, code blocks, inline code, bold, italic, and links all survive.
- Programmatic DOM writes into the Medium editor do NOT register with Medium's
  document model. Only the clipboard-paste path is reliable. Never replace it
  with `set_content` on the editor itself.
- The cover image is inserted directly under the title, which is what makes it
  Medium's preview/social image. The caret is placed at the end of the title with
  a Range, then `Enter` opens the empty line, then the add-media menu is used and
  the file goes into `input[name="uploadedFile"]` (Medium creates that input only
  after the "Add an image" button is clicked).
- The publish panel is opened with `button.js-publishButton`. Topics go into
  `input[role="combobox"]` (one at a time, `Enter` after each, max five). The
  "Paywall this story" checkbox is checked by default and is unchecked unless
  `paywall=yes`. The final button is
  `button:has-text("Publish"):not(.js-publishButton)`.

## Session handling

- The Medium session lives in the persistent profile `profiles/medium_main`.
- If the editor does not open, the config asks for a Cookie-Editor JSON export
  for `medium.com` and imports it, or accepts `manual` so the user can log in
  in the open browser window.

## Behavior notes

- The story is autosaved as a Medium draft before the confirmation prompt, so a
  cancelled run never loses work.
- Publishing only happens after an explicit `publish` answer or
  `--set publish_decision=publish`.
- Medium may leave one empty block after a blockquote or code block. That is
  Medium's own paste normalization, not a config bug.

## What not to do

- Do not rewrite the article with an LLM unless the user explicitly asks.
- Do not create a second Medium publishing flow if
  `configs/medium_markdown_story_publish.yaml` already fits.
- Do not use `--headless` for this flow: the clipboard paste needs a focused
  real browser window.
- Do not claim the story was published unless a published URL was captured.
