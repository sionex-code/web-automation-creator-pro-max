from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "we",
    "with",
    "you",
    "your",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Select the most relevant Facebook groups from a saved discovery JSON "
            "using keyword overlap."
        )
    )
    parser.add_argument("--groups", required=True, help="Path to the saved Facebook groups JSON file")
    parser.add_argument("--text", default="", help="Post content or topic used to score relevance")
    parser.add_argument("--text-file", help="Optional file containing the post content")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of groups to keep")
    parser.add_argument("--min-score", type=int, default=1, help="Minimum keyword overlap score")
    parser.add_argument("--output", help="Destination JSON file for the selected groups")
    return parser.parse_args()


def tokenize(value: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]{3,}", value.lower())
    return [token for token in tokens if token not in STOP_WORDS]


def load_groups(path: Path) -> tuple[list[dict], dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    metadata: dict = {}

    if isinstance(raw, dict):
        metadata = {k: v for k, v in raw.items() if k != "groups"}
        groups = raw.get("groups", [])
    elif isinstance(raw, list):
        groups = raw
    else:
        raise SystemExit("Groups JSON must be either a list or an object with a 'groups' key.")

    if not isinstance(groups, list):
        raise SystemExit("The 'groups' value must be a list.")

    normalized = []
    for item in groups:
        if not isinstance(item, dict):
            continue
        if not item.get("url"):
            continue
        normalized.append(item)
    return normalized, metadata


def build_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}.selected.json")


def main() -> int:
    args = parse_args()
    groups_path = Path(args.groups).expanduser().resolve()
    if not groups_path.exists():
        raise SystemExit(f"Groups file not found: {groups_path}")

    content = args.text
    if args.text_file:
        content = Path(args.text_file).expanduser().read_text(encoding="utf-8")
    content = content.strip()
    if not content:
        raise SystemExit("Provide --text or --text-file so the script can score relevance.")

    groups, metadata = load_groups(groups_path)
    query_terms = tokenize(content)
    query_term_set = set(query_terms)

    scored = []
    for group in groups:
        haystack = " ".join(
            str(group.get(field, ""))
            for field in ("name", "description", "privacy", "summary", "keywords")
        )
        group_terms = set(tokenize(haystack))
        matched_terms = sorted(query_term_set & group_terms)
        score = len(matched_terms)
        if score < args.min_score:
            continue

        selected = dict(group)
        selected["match_score"] = score
        selected["matched_terms"] = matched_terms
        scored.append(selected)

    scored.sort(
        key=lambda item: (
            -int(item.get("match_score", 0)),
            item.get("name", "").lower(),
            item.get("url", "").lower(),
        )
    )

    limited = scored[: max(args.limit, 0)]
    output_path = Path(args.output).expanduser().resolve() if args.output else build_output_path(groups_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "source_path": str(groups_path),
        "selected_at": datetime.now().isoformat(timespec="seconds"),
        "selection_query": content[:500],
        "source_metadata": metadata,
        "groups": limited,
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Loaded groups: {len(groups)}")
    print(f"Query terms: {', '.join(query_terms[:20])}")
    print(f"Selected groups: {len(limited)}")
    print(f"Output: {output_path}")
    for index, group in enumerate(limited, start=1):
        print(
            f"{index}. score={group.get('match_score', 0)} "
            f"name={group.get('name', 'Unnamed')} "
            f"url={group.get('url', '')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
