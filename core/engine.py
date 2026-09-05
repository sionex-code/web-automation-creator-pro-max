"""
Automation Engine — The core executor that runs config-driven automation flows.

Processes each step in the config, interacts with the browser via Patchright,
takes snapshots for LLM analysis, handles user input, and supports
conditional logic, loops, and verification.
"""

import asyncio
import json
import time
import re
import math
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.console import console
from core.browser import BrowserManager
from core.snapshot import PageSnapshot
from core.config_loader import AutomationConfig, load_config
from core.interactive import InteractiveSession
from core.account_manager import Account
from core.markdown_tools import parse_markdown_article


MISSING = object()


class AutomationEngine:
    """
    Executes config-driven automation flows step by step.
    
    Supports:
    - Navigation, clicking, typing, scrolling
    - Page snapshots fed to LLM for decision-making
    - User input prompts mid-flow
    - Conditional branching and loops
    - Verification & error handling
    - Variable interpolation in all string fields
    """

    def __init__(
        self,
        config: AutomationConfig,
        account: Optional[Account] = None,
        headless: bool = False,
        interactive: Optional[InteractiveSession] = None,
        start_step: int = 0,
        end_step: Optional[int] = None,
        runtime_variables: Optional[dict[str, Any]] = None,
    ):
        self.config = config
        self.account = account
        self.headless = headless
        self.interactive = interactive or InteractiveSession()
        self.start_step = start_step
        self.end_step = end_step
        self.runtime_variables = runtime_variables or {}
        
        # Runtime state
        self.variables: dict[str, Any] = {}
        self.browser: Optional[BrowserManager] = None
        self.snapshot: Optional[PageSnapshot] = None
        self.step_results: list[dict] = []
        self.current_step: str = "0"
        self._start_time: float = 0

    # ── Variable Interpolation ─────────────────────────────────────────────

    def _lookup_path(self, data: Any, key: str) -> Any:
        """Resolve dotted paths like current_group.url against nested data."""
        current = data
        for part in key.split("."):
            if isinstance(current, dict):
                if part not in current:
                    return MISSING
                current = current[part]
                continue

            if isinstance(current, list):
                try:
                    index = int(part)
                except ValueError:
                    return MISSING
                if index < 0 or index >= len(current):
                    return MISSING
                current = current[index]
                continue

            return MISSING
        return current

    def _get_variable_value(self, key: str) -> Any:
        """Resolve a variable from runtime, config, or account scopes."""
        for source in (
            self.variables,
            self.config.variables,
            self.account.variables if self.account else None,
        ):
            if not source:
                continue
            if key in source:
                return source[key]
            resolved = self._lookup_path(source, key)
            if resolved is not MISSING:
                return resolved
        return MISSING

    def _resolve(self, value: Any) -> Any:
        """Replace {{variable}} placeholders in strings."""
        if not isinstance(value, str):
            return value

        pattern = re.compile(r"\{\{(.+?)\}\}")
        resolved_value = value

        for _ in range(5):
            changed = False

            def replacer(match):
                nonlocal changed
                key = match.group(1).strip()
                resolved = self._get_variable_value(key)
                if resolved is MISSING:
                    return match.group(0)
                changed = True
                return str(resolved)

            resolved_value = pattern.sub(replacer, resolved_value)
            if not changed:
                break

        return resolved_value

    def _select_top_level_steps(self) -> tuple[list[dict], list[str]]:
        """Return the requested top-level step slice and their display labels."""
        total_steps = len(self.config.steps)
        if total_steps == 0:
            return [], []

        start = self.start_step
        end = total_steps - 1 if self.end_step is None else self.end_step

        if start < 0 or start >= total_steps:
            raise ValueError(f"start_step {start} is outside 0..{total_steps - 1}")
        if end < start or end >= total_steps:
            raise ValueError(f"end_step {end} is outside {start}..{total_steps - 1}")

        selected_steps = self.config.steps[start:end + 1]
        labels = [str(i) for i in range(start, end + 1)]
        return selected_steps, labels

    # ── Main Execution ─────────────────────────────────────────────────────

    async def run(self) -> dict:
        """Execute the full automation flow."""
        self._start_time = time.time()
        
        # Merge variables
        self.variables = {**self.config.variables, **self.runtime_variables}
        if self.account:
            self.variables.update(self.account.variables)
            self.variables["_account_name"] = self.account.name
            self.variables["_account_platform"] = self.account.platform

        # Display config
        self.config.display()
        selected_steps, step_labels = self._select_top_level_steps()
        if step_labels and (self.start_step != 0 or self.end_step is not None):
            console.print(Panel(
                f"Executing top-level steps {step_labels[0]} through {step_labels[-1]}",
                title="Partial Run",
                border_style="cyan",
            ))
        
        if not self.interactive.confirm(
            f"Run automation **{self.config.name}** with {len(step_labels) or len(self.config.steps)} step(s)?"
        ):
            return {"status": "cancelled"}

        # Launch browser
        profile = self.account.profile_dir if self.account else self.config.settings.get("profile", "default")
        proxy = self.account.proxy if self.account else self.config.settings.get("proxy")
        
        async with BrowserManager(
            headless=self.headless,
            slow_mo=self.config.settings.get("slow_mo", 50),
            profile_name=profile,
            proxy=proxy,
        ) as browser:
            self.browser = browser
            self.snapshot = PageSnapshot(browser.page)

            try:
                await self._execute_steps(selected_steps or self.config.steps, step_labels=step_labels or None)
            except Exception as e:
                self.interactive.show_error(f"Automation failed at step {self.current_step}: {e}")
                if self.config.on_error == "pause":
                    self.interactive.pause("Error occurred. Press Enter to close browser…")
                raise

        elapsed = time.time() - self._start_time
        result = {
            "status": "completed",
            "steps_executed": len(self.step_results),
            "elapsed_seconds": round(elapsed, 1),
            "variables": self.variables,
        }
        
        console.print()
        console.print(Panel(
            f"✅ Completed {len(self.step_results)} steps in {elapsed:.1f}s",
            title=f"🎯 {self.config.name}",
            border_style="green",
        ))
        
        return result

    # ── Step Router ────────────────────────────────────────────────────────

    async def _execute_steps(self, steps: list[dict], step_labels: Optional[list[str]] = None):
        """Execute a list of steps sequentially."""
        for i, step in enumerate(steps):
            self.current_step = step_labels[i] if step_labels else str(i)
            action = step.get("action", "unknown")
            description = step.get("description", "")
            
            self.interactive.show_step(self.current_step, action, description)

            handler = getattr(self, f"_step_{action}", None)
            if not handler:
                self.interactive.show_error(f"Unknown action: {action}")
                continue

            result = await handler(step)
            self.step_results.append({"step": self.current_step, "action": action, "result": result})

            # Post-step delay
            delay = step.get("delay", 0)
            if delay:
                await asyncio.sleep(delay / 1000)  # delay in ms

    # ── Step Handlers ──────────────────────────────────────────────────────

    async def _step_goto(self, step: dict):
        url = self._resolve(step["url"])
        wait_until = step.get("wait_until", "domcontentloaded")
        await self.browser.goto(url, wait_until=wait_until)
        return {"url": url}

    async def _step_click(self, step: dict):
        selector = self._resolve(step["selector"])
        timeout = step.get("timeout", 10000)
        
        try:
            el = self.browser.page.locator(selector).first
            await el.wait_for(state="visible", timeout=timeout)
            await el.click()
            console.print(f"  [green]✓[/green] Clicked: {selector}")
            return {"clicked": selector}
        except Exception as e:
            console.print(f"  [red]✗[/red] Click failed on {selector}: {e}")
            if step.get("optional"):
                return {"skipped": str(e)}
            raise

    async def _step_type(self, step: dict):
        selector = self._resolve(step["selector"])
        text = self._resolve(step.get("text", ""))
        clear = step.get("clear", True)
        
        el = self.browser.page.locator(selector).first
        await el.wait_for(state="visible", timeout=step.get("timeout", 10000))
        
        if clear:
            await el.fill("")
        
        if step.get("human_like", False):
            # Type character by character with small delays
            for char in text:
                await el.type(char, delay=50)
        else:
            await el.fill(text)
        
        console.print(f"  [green]✓[/green] Typed into {selector}: \"{text[:50]}{'…' if len(text)>50 else ''}\"")
        return {"typed": text[:100]}

    async def _step_wait(self, step: dict):
        if step.get("selector"):
            selector = self._resolve(step["selector"])
            state = step.get("state", "visible")
            timeout = step.get("timeout", 30000)
            await self.browser.page.locator(selector).first.wait_for(state=state, timeout=timeout)
            console.print(f"  [green]✓[/green] Element ready: {selector}")
        elif step.get("timeout"):
            await asyncio.sleep(step["timeout"] / 1000)
            console.print(f"  [green]✓[/green] Waited {step['timeout']}ms")
        elif step.get("network_idle"):
            await self.browser.page.wait_for_load_state("networkidle")
            console.print(f"  [green]✓[/green] Network idle")
        return {}

    async def _step_snapshot(self, step: dict):
        mode = step.get("mode", "full")
        save_to = step.get("save_to_variable", "_last_snapshot")
        
        if mode == "quick":
            text = await self.snapshot.quick_as_text()
        else:
            text = await self.snapshot.full_as_text()
        
        self.variables[save_to] = text
        
        if step.get("display", True):
            console.print(Panel(text[:2000], title="📸 Page Snapshot", border_style="blue"))
        
        return {"snapshot_length": len(text)}

    async def _step_screenshot(self, step: dict):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_step = self.current_step.replace(".", "_")
        path = self._resolve(step.get("path", f"screenshots/step_{safe_step}_{ts}.png"))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        full_page = step.get("full_page", False)
        await self.browser.screenshot(path, full_page=full_page)
        return {"path": path}

    async def _step_read_markdown(self, step: dict):
        """Load a local markdown file and expose title/body variables."""
        path = self._resolve(step["path"])
        data = parse_markdown_article(path)

        title_var = step.get("save_title_to", "article_title")
        markdown_var = step.get("save_markdown_to", "article_body_markdown")
        html_var = step.get("save_html_to", "article_body_html")
        preview_var = step.get("save_preview_to", "article_preview_text")
        meta_var = step.get("save_meta_to", "article_meta")

        self.variables[title_var] = data["title"]
        self.variables[markdown_var] = data["body_markdown"]
        self.variables[html_var] = data["body_html"]
        self.variables[preview_var] = data["preview_text"]
        self.variables[meta_var] = {
            "path": data["path"],
            "word_count": data["word_count"],
        }

        if step.get("display", True):
            preview = data["preview_text"][:300] + ("..." if len(data["preview_text"]) > 300 else "")
            console.print(Panel(
                f"Title: {data['title']}\nWords: {data['word_count']}\nSource: {data['path']}\n\n{preview}",
                title="Markdown Article",
                border_style="green",
            ))

        return {
            "path": data["path"],
            "title": data["title"],
            "word_count": data["word_count"],
        }

    async def _step_import_cookies(self, step: dict):
        """Import cookies from Cookie-Editor JSON text, file, or parsed objects."""
        source_data = None
        if step.get("source_variable"):
            source_data = self.variables.get(step["source_variable"])
        elif "source" in step:
            source_data = self._resolve(step["source"])

        if source_data in (None, ""):
            raise Exception("No cookie data provided")

        if isinstance(source_data, str):
            trimmed = source_data.strip()
            if Path(trimmed).exists():
                source_data = Path(trimmed).read_text(encoding="utf-8")
            else:
                source_data = trimmed

        if isinstance(source_data, str):
            try:
                parsed = json.loads(source_data)
            except json.JSONDecodeError as exc:
                raise Exception(f"Invalid cookie JSON: {exc}") from exc
        else:
            parsed = source_data

        if isinstance(parsed, dict) and "cookies" in parsed:
            parsed = parsed["cookies"]

        if not isinstance(parsed, list):
            raise Exception("Cookie import expects a JSON array or an object with a 'cookies' array")

        normalized = []
        for cookie in parsed:
            if not isinstance(cookie, dict) or "name" not in cookie or "value" not in cookie:
                continue

            item = {
                "name": str(cookie["name"]),
                "value": str(cookie["value"]),
            }

            domain = cookie.get("domain")
            path = cookie.get("path") or "/"
            url = cookie.get("url")

            if url:
                item["url"] = str(url)
            elif domain:
                normalized_domain = str(domain)
                item["domain"] = normalized_domain
                item["path"] = str(path)
            else:
                continue

            expires_raw = cookie.get("expires", cookie.get("expirationDate"))
            if expires_raw not in (None, "", -1):
                try:
                    expires_value = float(expires_raw)
                    if math.isfinite(expires_value):
                        item["expires"] = expires_value
                except Exception:
                    pass

            if "httpOnly" in cookie:
                item["httpOnly"] = bool(cookie["httpOnly"])
            if "secure" in cookie:
                item["secure"] = bool(cookie["secure"])
            same_site = cookie.get("sameSite")
            if isinstance(same_site, str):
                normalized_same_site = same_site.strip()
                lowered_same_site = normalized_same_site.lower()
                if lowered_same_site == "no_restriction":
                    item["sameSite"] = "None"
                elif lowered_same_site == "none":
                    item["sameSite"] = "None"
                elif lowered_same_site == "lax":
                    item["sameSite"] = "Lax"
                elif lowered_same_site == "strict":
                    item["sameSite"] = "Strict"

            normalized.append(item)

        if not normalized:
            raise Exception("No valid cookies found in the provided Cookie-Editor export")

        await self.browser.context.add_cookies(normalized)
        save_to = step.get("save_to_variable", "imported_cookies_count")
        self.variables[save_to] = len(normalized)
        console.print(f"  [green]✓[/green] Imported {len(normalized)} cookie(s)")
        return {"count": len(normalized)}

    async def _step_set_content(self, step: dict):
        """Set plain text or HTML into an editable element."""
        selector = self._resolve(step["selector"])
        timeout = step.get("timeout", 10000)
        clear = step.get("clear", True)

        text = None
        if "text" in step:
            text = self._resolve(step["text"])
        elif step.get("text_variable"):
            text = str(self.variables.get(step["text_variable"], ""))

        html = None
        if "html" in step:
            html = self._resolve(step["html"])
        elif step.get("html_variable"):
            html = str(self.variables.get(step["html_variable"], ""))

        locator = self.browser.page.locator(selector).first
        await locator.wait_for(state="visible", timeout=timeout)

        if html is not None:
            result = await locator.evaluate(
                """(el, payload) => {
                    const dispatch = (type) => el.dispatchEvent(new Event(type, { bubbles: true, cancelable: true }));
                    const isInput = el.tagName === 'INPUT' || el.tagName === 'TEXTAREA';
                    const isEditable = isInput || el.isContentEditable || el.getAttribute('contenteditable') === 'true';

                    if (!isEditable) {
                        throw new Error('Target element is not editable');
                    }

                    el.focus();

                    if (isInput) {
                        if (payload.clear !== false) {
                            el.value = '';
                        }
                        el.value = payload.text || '';
                        dispatch('input');
                        dispatch('change');
                        return { mode: 'input', length: el.value.length };
                    }

                    if (payload.clear !== false) {
                        el.innerHTML = '';
                    }

                    try {
                        const selection = window.getSelection();
                        const range = document.createRange();
                        range.selectNodeContents(el);
                        range.collapse(true);
                        selection.removeAllRanges();
                        selection.addRange(range);
                        const inserted = document.execCommand('insertHTML', false, payload.html);
                        if (!inserted) {
                            el.innerHTML = payload.html;
                        }
                    } catch (error) {
                        el.innerHTML = payload.html;
                    }

                    dispatch('input');
                    dispatch('change');
                    return { mode: 'html', length: (el.innerText || '').length };
                }""",
                {"html": html, "text": text or "", "clear": clear},
            )
        else:
            if text is None:
                text = ""

            element_info = await locator.evaluate(
                """(el) => ({
                    tag: el.tagName,
                    isContentEditable: el.isContentEditable || el.getAttribute('contenteditable') === 'true'
                })"""
            )

            if element_info["tag"] in {"INPUT", "TEXTAREA"}:
                if clear:
                    await locator.fill("")
                if step.get("human_like", False):
                    for char in text:
                        await locator.type(char, delay=50)
                else:
                    await locator.fill(text)
                result = {"mode": "text", "length": len(text)}
            elif element_info["isContentEditable"]:
                result = await locator.evaluate(
                    """(el, payload) => {
                        const dispatch = (type) => el.dispatchEvent(new Event(type, { bubbles: true, cancelable: true }));
                        el.focus();
                        if (payload.clear !== false) {
                            el.textContent = '';
                        }
                        el.textContent = payload.text;
                        dispatch('input');
                        dispatch('change');
                        return { mode: 'contenteditable', length: (el.innerText || '').length };
                    }""",
                    {"text": text, "clear": clear},
                )
            else:
                raise Exception(f"Element is not editable: {selector}")

        console.print(f"  [green]✓[/green] Set content in {selector}")
        return result

    async def _step_save_json(self, step: dict):
        """Save structured data or JSON text to disk."""
        data_key = step["variable"]
        file_path = self._resolve(step.get("path", f"output/{data_key}.json"))
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        data = self.variables.get(data_key)
        with open(file_path, "w", encoding="utf-8") as f:
            if isinstance(data, str):
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    f.write(data)
                else:
                    json.dump(parsed, f, indent=2, ensure_ascii=False)
            else:
                json.dump(data, f, indent=2, ensure_ascii=False)

        console.print(f"  [green]✓[/green] JSON saved to {file_path}")
        return {"path": file_path}

    async def _step_load_json(self, step: dict):
        """Load structured JSON from disk into a runtime variable."""
        file_path = Path(self._resolve(step["path"]))
        if not file_path.exists():
            raise Exception(f"JSON file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        root_key = step.get("root_key")
        if root_key:
            if not isinstance(data, dict):
                raise Exception("load_json 'root_key' requires a top-level JSON object")
            if root_key not in data:
                raise Exception(f"load_json could not find root_key '{root_key}' in {file_path}")
            data = data[root_key]

        save_to = step.get("save_to_variable")
        if not save_to:
            save_to = file_path.stem.replace("-", "_")

        self.variables[save_to] = data

        if step.get("display", False):
            preview = json.dumps(data, indent=2, ensure_ascii=False)[:2000]
            console.print(Panel(preview, title=f"Loaded JSON -> ${save_to}", border_style="green"))

        count = len(data) if isinstance(data, (list, dict)) else None
        console.print(f"  [green]ok[/green] Loaded JSON from {file_path} into ${save_to}")
        return {"path": str(file_path), "variable": save_to, "count": count}

    async def _step_console_log(self, step: dict):
        """Print a resolved message for debugging or explicit user feedback."""
        message = self._resolve(step.get("message", ""))
        console.print(f"  [blue]i[/blue] {message}")
        return {"message": message}

    async def _step_extract_published_link(self, step: dict):
        """Extract the published article/post link from the page."""
        save_to = step.get("save_to_variable", "published_link")
        optional = step.get("optional", False)
        link = await self.browser.page.evaluate(
            """(patterns) => {
                const candidates = [];
                const add = (href) => {
                    if (href && typeof href === 'string' && !candidates.includes(href)) {
                        candidates.push(href);
                    }
                };

                add(document.querySelector('link[rel="canonical"]')?.href || null);
                add(document.querySelector('meta[property="og:url"]')?.content || null);
                add(location.href);

                document.querySelectorAll('a[href]').forEach((a) => add(a.href));

                const isLikelyPublished = (href) => {
                    if (!href || !href.startsWith('https://www.linkedin.com/')) return false;
                    if (/\\/uas\\/login|\\/feed\\/?$|\\/post\\/new|\\/sharing\\/share-offsite/i.test(href)) return false;
                    return patterns.some((pattern) => href.includes(pattern));
                };

                return candidates.find(isLikelyPublished) || '';
            }""",
            step.get("patterns", ["/pulse/", "/posts/", "/feed/update/", "/article/"]),
        )

        if not link and not optional:
            raise Exception("Could not extract a published link from the current page")

        self.variables[save_to] = link
        console.print(f"  [green]✓[/green] Published link: {link or '(not found)'}")
        return {"link": link}

    async def _step_llm_generate(self, step: dict):
        """Generate content using LLM (prints prompt for the calling agent to handle)."""
        prompt = self._resolve(step.get("prompt", ""))
        save_to = step.get("save_to_variable", "_llm_output")
        
        # If snapshot context is requested, include it
        if step.get("include_snapshot", False):
            snapshot_text = await self.snapshot.full_as_text()
            prompt = f"{prompt}\n\nCurrent page context:\n{snapshot_text}"
        
        console.print(Panel(prompt, title="🧠 LLM Prompt", border_style="magenta"))
        
        # In agent-driven mode, the agent provides the output
        # In standalone mode, ask the user
        response = self.interactive.ask(
            f"LLM Generation needed. Provide the output (or let the agent handle it):",
            default=step.get("default", "")
        )
        
        self.variables[save_to] = response
        console.print(f"  [green]✓[/green] Generated content saved to ${save_to}")
        return {"variable": save_to, "length": len(response)}

    async def _step_llm_decide(self, step: dict):
        """Ask LLM to make a decision based on page snapshot."""
        question = self._resolve(step.get("question", ""))
        choices = step.get("choices", [])
        save_to = step.get("save_to_variable", "_llm_decision")
        
        snapshot_text = await self.snapshot.quick_as_text()
        
        full_prompt = f"{question}\n\nPage State:\n{snapshot_text}"
        if choices:
            full_prompt += f"\n\nChoices: {', '.join(choices)}"
        
        console.print(Panel(full_prompt[:2000], title="🤔 LLM Decision", border_style="yellow"))
        
        if choices:
            decision = self.interactive.choose(question, choices)
        else:
            decision = self.interactive.ask(question)
        
        self.variables[save_to] = decision
        return {"decision": decision}

    async def _step_user_input(self, step: dict):
        question = self._resolve(step.get("prompt", "Enter value:"))
        save_to = step.get("save_to_variable", "_user_input")
        default = self._resolve(step.get("default", ""))

        existing_value = self.variables.get(save_to)
        if existing_value not in (None, ""):
            console.print(f"  [green]✓[/green] Using preset value for ${save_to}")
            return {"variable": save_to, "value": existing_value, "source": "preset"}
        
        value = self.interactive.ask(question, default=default or None)
        self.variables[save_to] = value
        return {"variable": save_to, "value": value}

    async def _step_verify(self, step: dict):
        """Verify something exists on the page."""
        check_type = step.get("check", "selector_exists")
        
        if check_type == "selector_exists":
            selector = self._resolve(step["selector"])
            timeout = step.get("timeout", 5000)
            try:
                await self.browser.page.locator(selector).first.wait_for(state="visible", timeout=timeout)
                console.print(f"  [green]✓[/green] Verified: {selector} exists")
                self.variables["_verify_result"] = True
                return {"verified": True}
            except:
                console.print(f"  [red]✗[/red] Verification failed: {selector} not found")
                self.variables["_verify_result"] = False
                if not step.get("optional"):
                    raise Exception(f"Verification failed: {selector}")
                return {"verified": False}
        
        elif check_type == "text_contains":
            expected = self._resolve(step["text"])
            content = await self.browser.page.content()
            found = expected.lower() in content.lower()
            console.print(f"  {'[green]✓[/green]' if found else '[red]✗[/red]'} Text '{expected}' {'found' if found else 'NOT found'}")
            self.variables["_verify_result"] = found
            return {"verified": found}
        
        elif check_type == "url_contains":
            expected = self._resolve(step["url"])
            current = self.browser.page.url
            found = expected in current
            console.print(f"  {'[green]✓[/green]' if found else '[red]✗[/red]'} URL check: {expected}")
            self.variables["_verify_result"] = found
            return {"verified": found}
        
        return {"verified": False}

    async def _step_js_eval(self, step: dict):
        """Execute JavaScript on the page."""
        code = self._resolve(step["code"])
        save_to = step.get("save_to_variable")
        
        result = await self.browser.page.evaluate(code)
        
        if save_to:
            self.variables[save_to] = result
        
        console.print(f"  [green]✓[/green] JS executed" + (f", result saved to ${save_to}" if save_to else ""))
        return {"result": str(result)[:200] if result else None}

    async def _step_scroll(self, step: dict):
        direction = step.get("direction", "down")
        amount = step.get("amount", 500)
        
        if direction == "down":
            await self.browser.page.evaluate(f"window.scrollBy(0, {amount})")
        elif direction == "up":
            await self.browser.page.evaluate(f"window.scrollBy(0, -{amount})")
        elif direction == "bottom":
            await self.browser.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        elif direction == "top":
            await self.browser.page.evaluate("window.scrollTo(0, 0)")
        
        console.print(f"  [green]✓[/green] Scrolled {direction}")
        return {"direction": direction}

    async def _step_press(self, step: dict):
        key = step.get("key", "Enter")
        selector = step.get("selector")
        
        if selector:
            await self.browser.page.locator(self._resolve(selector)).first.press(key)
        else:
            await self.browser.page.keyboard.press(key)
        
        console.print(f"  [green]✓[/green] Pressed: {key}")
        return {"key": key}

    async def _step_select(self, step: dict):
        selector = self._resolve(step["selector"])
        value = self._resolve(step["value"])
        await self.browser.page.locator(selector).first.select_option(value)
        console.print(f"  [green]✓[/green] Selected: {value}")
        return {"value": value}

    async def _step_upload(self, step: dict):
        selector = self._resolve(step["selector"])
        file_path = self._resolve(step["file"])
        await self.browser.page.locator(selector).first.set_input_files(file_path)
        console.print(f"  [green]✓[/green] Uploaded: {file_path}")
        return {"file": file_path}

    async def _step_extract(self, step: dict):
        """Extract data from page into a variable."""
        selector = self._resolve(step["selector"])
        attribute = step.get("attribute", "innerText")
        save_to = step.get("save_to_variable", "_extracted")
        
        if attribute == "innerText":
            value = await self.browser.page.locator(selector).first.inner_text()
        elif attribute == "innerHTML":
            value = await self.browser.page.locator(selector).first.inner_html()
        elif attribute == "value":
            value = await self.browser.page.locator(selector).first.input_value()
        else:
            value = await self.browser.page.locator(selector).first.get_attribute(attribute)
        
        self.variables[save_to] = value
        console.print(f"  [green]✓[/green] Extracted → ${save_to}: \"{str(value)[:80]}\"")
        return {"variable": save_to, "value": str(value)[:200]}

    async def _step_save_data(self, step: dict):
        """Save variable data to a file."""
        data_key = step.get("variable", "_extracted")
        file_path = self._resolve(step.get("path", f"output/{data_key}.txt"))
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = self.variables.get(data_key, "")
        with open(file_path, "w", encoding="utf-8") as f:
            if isinstance(data, (dict, list)):
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                f.write(str(data))
        
        console.print(f"  [green]✓[/green] Saved to {file_path}")
        return {"path": file_path}

    async def _step_conditional(self, step: dict):
        """If/else branching based on variable values."""
        condition = step.get("condition", "")
        resolved = self._resolve(condition)
        
        # Simple condition evaluation
        result = self._eval_condition(resolved)
        
        if result and step.get("then"):
            console.print(f"  [green]→[/green] Condition TRUE, executing 'then' branch")
            await self._execute_steps(
                step["then"],
                step_labels=[f"{self.current_step}.then.{i}" for i in range(len(step["then"]))],
            )
        elif not result and step.get("else"):
            console.print(f"  [yellow]→[/yellow] Condition FALSE, executing 'else' branch")
            await self._execute_steps(
                step["else"],
                step_labels=[f"{self.current_step}.else.{i}" for i in range(len(step["else"]))],
            )
        
        return {"condition": condition, "result": result}

    async def _step_loop(self, step: dict):
        """Repeat steps N times or until a condition is met."""
        times = step.get("times", 1)
        until_condition = step.get("until")
        loop_steps = step.get("steps", [])
        completed_iterations = 0
        parent_step = self.current_step
        
        for iteration in range(times):
            completed_iterations = iteration + 1
            console.print(f"  [blue]↻[/blue] Loop iteration {iteration + 1}/{times}")
            await self._execute_steps(
                loop_steps,
                step_labels=[f"{parent_step}.loop{iteration + 1}.{i}" for i in range(len(loop_steps))],
            )
            self.current_step = parent_step
            
            if until_condition:
                resolved = self._resolve(until_condition)
                if self._eval_condition(resolved):
                    console.print(f"  [green]✓[/green] Loop condition met, breaking")
                    break
        
        return {"iterations": completed_iterations}

    # ── Helpers ────────────────────────────────────────────────────────────

    async def _step_for_each(self, step: dict):
        """Iterate over a list variable and execute nested steps for each item."""
        items_value = self.variables.get(step["items_variable"])
        if isinstance(items_value, str):
            try:
                items = json.loads(items_value)
            except json.JSONDecodeError as exc:
                raise Exception(
                    f"for_each expected {step['items_variable']} to contain JSON or a list"
                ) from exc
        else:
            items = items_value

        if not isinstance(items, list):
            raise Exception(
                f"for_each expected {step['items_variable']} to be a list, got {type(items).__name__}"
            )

        item_variable = step.get("item_variable", "item")
        index_variable = step.get("index_variable", f"{item_variable}_index")
        results_variable = step.get("save_results_to", f"{item_variable}_results")
        continue_on_error = step.get("continue_on_error", False)
        flatten_keys = step.get("flatten_keys", True)
        nested_steps = step.get("steps", [])
        parent_step = self.current_step

        tracked_previous: dict[str, Any] = {}
        results: list[dict[str, Any]] = []

        def remember_var(name: str) -> None:
            if name not in tracked_previous:
                tracked_previous[name] = self.variables.get(name, MISSING)

        for index, item in enumerate(items):
            remember_var(item_variable)
            remember_var(index_variable)
            self.variables[item_variable] = item
            self.variables[index_variable] = index

            per_item_variables: list[str] = []
            if isinstance(item, dict) and flatten_keys:
                for raw_key, raw_value in item.items():
                    safe_key = re.sub(r"[^a-zA-Z0-9_]+", "_", str(raw_key)).strip("_")
                    if not safe_key:
                        continue
                    derived_name = f"{item_variable}_{safe_key}"
                    remember_var(derived_name)
                    self.variables[derived_name] = raw_value
                    per_item_variables.append(derived_name)
            elif not isinstance(item, dict):
                derived_name = f"{item_variable}_value"
                remember_var(derived_name)
                self.variables[derived_name] = item
                per_item_variables.append(derived_name)

            console.print(f"  [blue]>>[/blue] Iteration {index + 1}/{len(items)}")

            try:
                await self._execute_steps(
                    nested_steps,
                    step_labels=[f"{parent_step}.each{index + 1}.{i}" for i in range(len(nested_steps))],
                )
                self.current_step = parent_step
                results.append({"index": index, "status": "completed"})
            except Exception as exc:
                self.current_step = parent_step
                results.append({"index": index, "status": "failed", "error": str(exc)})
                if not continue_on_error:
                    raise
                console.print(
                    f"  [yellow]![/yellow] Iteration {index + 1} failed but continuing: {exc}"
                )
            finally:
                for name in per_item_variables:
                    previous = tracked_previous.get(name, MISSING)
                    if previous is MISSING:
                        self.variables.pop(name, None)
                    else:
                        self.variables[name] = previous

        for name, previous in tracked_previous.items():
            if previous is MISSING:
                self.variables.pop(name, None)
            else:
                self.variables[name] = previous

        self.variables[results_variable] = results
        self.variables[f"{results_variable}_completed"] = sum(
            1 for result in results if result["status"] == "completed"
        )
        self.variables[f"{results_variable}_failed"] = sum(
            1 for result in results if result["status"] == "failed"
        )
        return {
            "iterations": len(items),
            "completed": self.variables[f"{results_variable}_completed"],
            "failed": self.variables[f"{results_variable}_failed"],
        }

    def _eval_condition(self, condition: str) -> bool:
        """Evaluate a simple condition string."""
        if condition.lower() in ("true", "yes", "1"):
            return True
        if condition.lower() in ("false", "no", "0", "", "none"):
            return False
        
        # Check variable existence
        if condition.startswith("exists:"):
            var_name = condition[7:].strip()
            return var_name in self.variables and bool(self.variables[var_name])
        
        # Check equality
        if "==" in condition:
            left, right = condition.split("==", 1)
            return self._resolve(left.strip()) == self._resolve(right.strip())
        
        if "!=" in condition:
            left, right = condition.split("!=", 1)
            return self._resolve(left.strip()) != self._resolve(right.strip())
        
        return bool(condition)


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------

async def run_automation(
    config_path: str,
    account_name: Optional[str] = None,
    headless: bool = False,
    auto_mode: bool = False,
    start_step: int = 0,
    end_step: Optional[int] = None,
    runtime_variables: Optional[dict[str, Any]] = None,
) -> dict:
    """Load config and run automation — convenience function."""
    from core.account_manager import AccountManager
    from core.config_loader import load_accounts
    
    config = load_config(config_path)
    interactive = InteractiveSession(auto_mode=auto_mode)
    
    accounts_data = load_accounts()
    account_manager = AccountManager(accounts_data)
    account = None
    if account_name:
        account = account_manager.get(account_name)
        if account:
            console.print(f"[green]✓[/green] Using account: [cyan]{account.name}[/cyan]")
        else:
            raise ValueError(f"Account not found: {account_name}")
    else:
        account_platform = config.settings.get("account_platform")
        if account_platform:
            platform_accounts = account_manager.get_by_platform(account_platform)
            if len(platform_accounts) == 1:
                account = platform_accounts[0]
                console.print(
                    f"[green]✓[/green] Auto-selected only {account_platform} account: [cyan]{account.name}[/cyan]"
                )
            elif len(platform_accounts) > 1:
                account_names = ", ".join(acc.name for acc in platform_accounts)
                raise ValueError(
                    f"Multiple {account_platform} accounts found. Re-run with --account and choose one of: {account_names}"
                )
    
    engine = AutomationEngine(
        config=config,
        account=account,
        headless=headless,
        interactive=interactive,
        start_step=start_step,
        end_step=end_step,
        runtime_variables=runtime_variables,
    )
    
    return await engine.run()
