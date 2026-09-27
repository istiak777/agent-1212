import asyncio
import json
import os
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from browser_use import BrowserSession

from config import AgentConfig


@dataclass(frozen=True)
class SourceDocument:
    requested_source: str
    url: str
    title: str
    text: str


class FileDownloadManager:
    """Download media or files from the internet into a workspace directory."""

    def __init__(self, base_directory="downloads"):
        self.base_directory = Path(base_directory)
        self.base_directory.mkdir(parents=True, exist_ok=True)

    def download(self, url, filename=None):
        if not url:
            raise ValueError("A download URL is required.")

        destination = self.base_directory / (filename or os.path.basename(url) or "download.bin")
        urllib.request.urlretrieve(url, destination)
        return str(destination)


class BrowserActionExecutor:
    """Execute browser-level actions for personal assistant workflows."""

    def __init__(self, config=None):
        self.config = config or AgentConfig.from_environment()

    async def open(self, url):
        session = BrowserSession(headless=self.config.headless)
        await session.start()
        try:
            page = await session.get_current_page()
            await page.goto(url)
            await asyncio.sleep(self.config.wait_seconds)
            return page
        finally:
            await session.kill()

    async def click(self, selector, url=None):
        session = BrowserSession(headless=self.config.headless)
        await session.start()
        try:
            page = await session.get_current_page()
            if url:
                await page.goto(url)
            await asyncio.sleep(self.config.wait_seconds)
            await page.evaluate(f"document.querySelector({json.dumps(selector)}).click()")
            return True
        finally:
            await session.kill()

    async def type_text(self, selector, text, url=None):
        session = BrowserSession(headless=self.config.headless)
        await session.start()
        try:
            page = await session.get_current_page()
            if url:
                await page.goto(url)
            await asyncio.sleep(self.config.wait_seconds)
            await page.evaluate(
                f"""
                const element = document.querySelector({json.dumps(selector)});
                if (element) {{
                    element.focus();
                    element.value = {json.dumps(text)};
                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                """
            )
            return True
        finally:
            await session.kill()

    async def submit(self, selector, url=None):
        return await self.click(selector, url=url)

    async def extract_links(self, url=None):
        session = BrowserSession(headless=self.config.headless)
        await session.start()
        try:
            page = await session.get_current_page()
            if url:
                await page.goto(url)
            await asyncio.sleep(self.config.wait_seconds)
            return await page.evaluate(
                """
                Array.from(document.querySelectorAll('a')).map((link) => ({
                    href: link.href,
                    text: link.innerText.trim()
                })).filter((item) => item.href)
                """
            )
        finally:
            await session.kill()


class BrowserToolkit:
    """Reusable browser tools that can be called by any workflow."""

    def __init__(self, config=None):
        self.config = config or AgentConfig.from_environment()
        self.actions = BrowserActionExecutor(self.config)

    @staticmethod
    def resolve_source(source):
        if re.match(r"^https?://", source, re.IGNORECASE):
            return source
        return f"https://www.google.com/search?q={quote_plus(source)}"

    async def fetch(self, source, selector=None, browser_path=None):
        url = self.resolve_source(source)
        session_args = {"headless": self.config.headless}
        if browser_path:  # Chrome / Edge / Brave chosen by the user
            session_args["executable_path"] = browser_path
        session = BrowserSession(**session_args)
        await session.start()
        try:
            page = await session.get_current_page()
            await page.goto(url)
            await asyncio.sleep(self.config.wait_seconds)
            title = await page.get_title()
            text = await self._extract_text(page, selector)
            return SourceDocument(
                requested_source=source,
                url=url,
                title=title or source,
                text=text[: self.config.max_source_chars],
            )
        finally:
            await session.kill()

    async def _extract_text(self, page, selector=None):
        if selector:
            selector_json = json.dumps(selector)
            script = (
                "() => { const node = document.querySelector(%s); "
                "return node ? node.innerText : ''; }" % selector_json
            )
        else:
            script = "() => document.body ? document.body.innerText : ''"
        return await page.evaluate(script)

    async def search(self, query):
        """Search the web and return the visible search-result document."""
        return await self.fetch(query)

    async def click(self, selector, url=None):
        return await self.actions.click(selector, url=url)

    async def type_text(self, selector, text, url=None):
        return await self.actions.type_text(selector, text, url=url)

    async def submit(self, selector, url=None):
        return await self.actions.submit(selector, url=url)

    async def extract_links(self, url=None):
        return await self.actions.extract_links(url=url)

    async def download(self, url, filename=None):
        manager = FileDownloadManager("downloads")
        return manager.download(url, filename=filename)