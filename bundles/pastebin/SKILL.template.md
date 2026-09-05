---
name: pastebin-poster
description: Create Pastebin pastes from supplied text using the Open Automation Creator runtime at {{RUNTIME_ROOT}}.
---

# Pastebin Poster

This skill creates a Pastebin paste for provided text or file content using the
Open Automation Creator runtime installed at `{{RUNTIME_ROOT}}`.

Usage summary:

- Ask the user for a short title, paste visibility (public/unlisted/private),
  optional expiration, and the content to paste.
- Open `https://pastebin.com/`, fill the form, create the paste, and return
  the published paste URL.

Recommended kickoff questions:

1. What is the paste title?
2. Paste visibility: `public`, `unlisted`, or `private`?
3. Expiration (e.g., `10M`, `1H`, `1D`, `N` for never)?
4. Paste content (or provide a local file path).

Do not ask the user for selectors or page internals. Use live discovery if you
need to verify selectors on the Pastebin site before writing a reusable config.

Example run command (discovery):

```bash
cd "{{RUNTIME_ROOT}}"
.venv/bin/python run.py --discover-url "https://pastebin.com/" --account ACCOUNT_NAME --pause --snapshot-mode full
```

When finished, return the paste URL and the discovery artifact paths used.
