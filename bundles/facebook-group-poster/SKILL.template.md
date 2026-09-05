---
name: facebook-group-poster
description: Discover Facebook groups, save them to reusable JSON, select relevant groups for a topic or post, and publish content with the Open Automation Creator runtime at {{RUNTIME_ROOT}}. Use when the user wants Facebook group discovery, saved group catalogs, relevance-based group selection, or repeated posting to previously discovered groups.
---

# Facebook Group Poster

Use the Open Automation Creator runtime installed at `{{RUNTIME_ROOT}}`.

Before changing selectors or claiming the flow is verified, read:

`{{RUNTIME_ROOT}}/skill.md`

Follow that guide's discovery and verification rules.

## What this skill covers

- Discover Facebook groups from a live Facebook search or listing page
- Save the discovered groups to JSON for later reuse
- Select the most relevant saved groups for a new post
- Open those groups and attempt to publish the provided content

## Inputs to confirm

Confirm only what you need:

- Which Facebook account from `configs/accounts.yaml` should be used
- Whether the user wants to discover groups or post to previously saved groups
- The saved groups JSON path, if discovery already happened
- The post content or topic for relevance matching
- Whether the batch should stop before public posting or publish after confirmation

If there is no Facebook account in `configs/accounts.yaml`, ask the user to add one or confirm that the default profile should be used for discovery only. Do not invent an account entry.

## Discovery workflow

Use this config:

`configs/facebook_group_discovery.yaml`

Run it like this:

```bash
cd "{{RUNTIME_ROOT}}"
.venv/bin/python run.py configs/facebook_group_discovery.yaml --account FACEBOOK_ACCOUNT --set discovered_groups_path="~/facebook_groups.json"
```

What to do during the run:

- Log in to Facebook if needed
- Open the exact Facebook group search or listing page to capture
- Scroll until the desired groups are visible
- Let the runtime extract the visible group cards and save them to JSON

The saved JSON contains a `groups` array with `name`, `url`, `privacy`, `description`, and `slug`.

## Relevance selection workflow

After discovery, narrow the saved catalog to the groups that best match the new post:

```bash
.venv/bin/python scripts/select_facebook_groups.py --groups "~/facebook_groups.json" --text "POST OR TOPIC HERE" --output "~/facebook_groups.selected.json" --limit 5
```

Review the selected JSON if the topic is broad or ambiguous.

## Posting workflow

Use this config:

`configs/facebook_group_post_to_saved_groups.yaml`

Run it like this:

```bash
.venv/bin/python run.py configs/facebook_group_post_to_saved_groups.yaml --account FACEBOOK_ACCOUNT --set groups_json_path="~/facebook_groups.selected.json" --set post_content="POST CONTENT HERE" --set publish_batch=post-all
```

Behavior notes:

- The runtime loads the selected `groups` array from JSON
- The runtime asks for one final confirmation before any public posting
- It attempts to open each group, open the composer, insert the content, and click Post
- If a group's composer is missing, it skips that group and continues
- It saves preview and post-action screenshots for each attempted group

## Verification rules

- Do not claim the Facebook posting flow is fully verified unless the account was logged in and you tested against the live Facebook UI
- Use discovery snapshots and selector checks before changing the Facebook selectors
- Expect Facebook UI variations across accounts, locales, and membership states

## Return

When you finish, return:

- The account used
- The discovery JSON path or selected-groups JSON path
- The exact command that was run
- Which groups were targeted or skipped
- Whether Facebook posting was live-verified or only prepared structurally
