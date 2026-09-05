from __future__ import annotations

import argparse
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNTIME_DEST = Path.home() / ".open-automation-creator"
DEFAULT_BUNDLES = [
    "automation-creator-builder",
    "facebook-group-poster",
    "linkedin-markdown-article-publisher",
    "medium-markdown-story-publisher",
    "pastebin",
]
EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "output",
    "screenshots",
}
EXCLUDED_FILES = {
    ".DS_Store",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Install the Open Automation Creator runtime plus bundled skills into "
            "Codex, Claude Code, OpenCode, and agent-compatible homes."
        )
    )
    parser.add_argument(
        "--target",
        nargs="+",
        choices=["codex", "claude", "opencode", "agents", "all"],
        default=["all"],
        help="Which targets to install. Defaults to all.",
    )
    parser.add_argument(
        "--bundle",
        nargs="+",
        default=["all"],
        help=(
            "Which bundled skills to install. Use bundle names from bundles/ "
            "or 'all'. Defaults to all."
        ),
    )
    parser.add_argument(
        "--runtime-dest",
        default=str(DEFAULT_RUNTIME_DEST),
        help=(
            "Destination directory for the installed Open Automation Creator "
            "runtime. Defaults to ~/.open-automation-creator."
        ),
    )
    parser.add_argument(
        "--source",
        default=str(REPO_ROOT),
        help="Source Open Automation Creator repo path. Defaults to this repo.",
    )
    parser.add_argument(
        "--skip-profiles",
        action="store_true",
        help="Do not copy the profiles/ directory into the installed runtime.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without writing files.",
    )
    return parser.parse_args()


def render_template(template_path: Path, runtime_root: Path) -> str:
    return template_path.read_text(encoding="utf-8").replace(
        "{{RUNTIME_ROOT}}",
        str(runtime_root),
    )


def ensure_dir(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_file(source: Path, dest: Path, dry_run: bool) -> None:
    if dry_run:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def copy_runtime(source_root: Path, runtime_root: Path, skip_profiles: bool, dry_run: bool) -> None:
    if source_root.resolve() == runtime_root.resolve():
        print("Runtime copy: skipped (already installed at the destination)")
        return
    for item in source_root.iterdir():
        if item.name in EXCLUDED_FILES:
            continue
        if item.is_dir():
            if item.name in EXCLUDED_DIRS:
                continue
            if skip_profiles and item.name == "profiles":
                continue
            copy_tree(item, runtime_root / item.name, dry_run)
        else:
            copy_file(item, runtime_root / item.name, dry_run)


def copy_tree(source: Path, dest: Path, dry_run: bool) -> None:
    for item in source.iterdir():
        if item.name in EXCLUDED_FILES:
            continue
        if item.is_dir():
            if item.name in EXCLUDED_DIRS:
                continue
            copy_tree(item, dest / item.name, dry_run)
        else:
            copy_file(item, dest / item.name, dry_run)


def normalize_targets(raw_targets: list[str]) -> list[str]:
    if "all" in raw_targets:
        return ["codex", "claude", "opencode", "agents"]
    ordered = []
    for target in raw_targets:
        if target not in ordered:
            ordered.append(target)
    return ordered


def available_bundles() -> list[str]:
    bundle_root = REPO_ROOT / "bundles"
    return sorted(path.name for path in bundle_root.iterdir() if path.is_dir())


def normalize_bundles(raw_bundles: list[str]) -> list[str]:
    known = available_bundles()
    if "all" in raw_bundles:
        return [bundle for bundle in DEFAULT_BUNDLES if bundle in known]
    ordered: list[str] = []
    for bundle in raw_bundles:
        if bundle not in known:
            raise SystemExit(
                f"Unknown bundle '{bundle}'. Available bundles: {', '.join(known)}"
            )
        if bundle not in ordered:
            ordered.append(bundle)
    return ordered


def install_skill_dir(bundle_name: str, dest_root: Path, runtime_root: Path, dry_run: bool) -> Path:
    template_root = REPO_ROOT / "bundles" / bundle_name
    skill_dir = dest_root / bundle_name
    ensure_dir(skill_dir / "agents", dry_run)
    write_text(
        skill_dir / "SKILL.md",
        render_template(template_root / "SKILL.template.md", runtime_root),
        dry_run,
    )
    copy_file(
        template_root / "agents" / "openai.yaml",
        skill_dir / "agents" / "openai.yaml",
        dry_run,
    )
    return skill_dir


def install_claude_agent(bundle_name: str, dest_root: Path, runtime_root: Path, dry_run: bool) -> Path:
    template_root = REPO_ROOT / "bundles" / bundle_name
    ensure_dir(dest_root, dry_run)
    agent_path = dest_root / f"{bundle_name}.md"
    write_text(
        agent_path,
        render_template(template_root / "claude-agent.template.md", runtime_root),
        dry_run,
    )
    return agent_path


def target_roots() -> dict[str, Path]:
    home = Path.home()
    return {
        "codex": home / ".codex" / "skills",
        "opencode": home / ".config" / "opencode" / "skills",
        "agents": home / ".agents" / "skills",
        "claude_skills": home / ".claude" / "skills",
        "claude_agents": home / ".claude" / "agents",
    }


def main() -> int:
    args = parse_args()
    source_root = Path(args.source).expanduser().resolve()
    runtime_root = Path(args.runtime_dest).expanduser().resolve()
    targets = normalize_targets(args.target)
    bundles = normalize_bundles(args.bundle)
    roots = target_roots()

    if not (source_root / "run.py").exists():
        raise SystemExit(f"Source repo does not look like Open Automation Creator: {source_root}")

    print(f"Source runtime: {source_root}")
    print(f"Install runtime: {runtime_root}")
    print(f"Targets: {', '.join(targets)}")
    print(f"Bundles: {', '.join(bundles)}")
    if args.skip_profiles:
        print("Profiles: skipped")
    else:
        print("Profiles: included")
    if args.dry_run:
        print("Mode: dry-run")

    if not args.dry_run:
        runtime_root.mkdir(parents=True, exist_ok=True)
    copy_runtime(source_root, runtime_root, args.skip_profiles, args.dry_run)

    installed_paths: list[tuple[str, Path]] = [("runtime", runtime_root)]

    for bundle_name in bundles:
        if "codex" in targets:
            installed_paths.append(
                (f"codex skill ({bundle_name})", install_skill_dir(bundle_name, roots["codex"], runtime_root, args.dry_run))
            )
        if "opencode" in targets:
            installed_paths.append(
                (f"opencode skill ({bundle_name})", install_skill_dir(bundle_name, roots["opencode"], runtime_root, args.dry_run))
            )
        if "agents" in targets:
            installed_paths.append(
                (f"agent skill ({bundle_name})", install_skill_dir(bundle_name, roots["agents"], runtime_root, args.dry_run))
            )
        if "claude" in targets:
            installed_paths.append(
                (f"claude agent ({bundle_name})", install_claude_agent(bundle_name, roots["claude_agents"], runtime_root, args.dry_run))
            )
            installed_paths.append(
                (
                    f"claude-compatible skill ({bundle_name})",
                    install_skill_dir(bundle_name, roots["claude_skills"], runtime_root, args.dry_run),
                )
            )

    print("")
    print("Installed:")
    for label, path in installed_paths:
        print(f"- {label}: {path}")

    print("")
    print("Next steps:")
    print(f"- Install dependencies in {runtime_root} with: python -m pip install -r requirements.txt")
    print("- Restart Codex, Claude Code, and OpenCode to pick up new skills or agents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
