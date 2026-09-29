import tempfile
import unittest

from agent import ResearchAgent
from automation import CommandQueue, PersistentSessionManager
from browser_tools import BrowserActionExecutor, FileDownloadManager, SourceDocument
from memory import WorkflowMemory


class FakeModel:
    def __init__(self):
        self.last_prompt = None

    async def ainvoke(self, messages):
        self.last_prompt = messages[0].content if messages else ""

        class Response:
            completion = "The task is complete."

        return Response()


class FakeToolkit:
    async def fetch(self, source, selector=None):
        return SourceDocument(
            requested_source=source,
            url="https://example.com",
            title="Example",
            text="Example page content about a company and services.",
        )

    async def search(self, query):
        return await self.fetch(query)


class AgentBehaviorTests(unittest.TestCase):
    def test_default_prompt_is_generic_for_user_commands(self):
        model = FakeModel()
        agent = ResearchAgent(toolkit=FakeToolkit(), model=model)

        import asyncio

        asyncio.run(
            agent.answer(
                "https://example.com",
                request="Book a meeting and send a reply.",
            )
        )

        self.assertIn("Keep the answer concise, factual, and aligned with the request.", model.last_prompt)
        self.assertIn("Start with a SOURCE line", model.last_prompt)
        self.assertNotIn("SHORT EXPLANATION:", model.last_prompt)
        self.assertNotIn("HASHTAGS:", model.last_prompt)

    def test_writeup_request_uses_aligned_content_package(self):
        model = FakeModel()
        agent = ResearchAgent(toolkit=FakeToolkit(), model=model)

        import asyncio

        asyncio.run(
            agent.answer(
                "https://example.com",
                request="Draft a social media writeup with hashtags from this page",
            )
        )

        self.assertIn("SHORT EXPLANATION:", model.last_prompt)
        self.assertIn("HASHTAGS:", model.last_prompt)
        self.assertIn("SOURCE:", model.last_prompt)
        self.assertIn("https://example.com", model.last_prompt)

    def test_command_router_requires_permission_for_sensitive_actions(self):
        agent = ResearchAgent(toolkit=FakeToolkit(), model=FakeModel())

        import asyncio

        result = asyncio.run(
            agent.execute_command(
                "Open the page and post a reply to my audience.",
                source="https://example.com",
                auto_approve=False,
            )
        )

        self.assertEqual(result["status"], "awaiting_permission")
        self.assertEqual(result["action"], "post")

    def test_browser_action_executor_and_download_manager_are_available(self):
        executor = BrowserActionExecutor()
        downloader = FileDownloadManager("./downloads")

        self.assertTrue(hasattr(executor, "click"))
        self.assertTrue(hasattr(executor, "type_text"))
        self.assertTrue(hasattr(executor, "extract_links"))
        self.assertTrue(hasattr(downloader, "download"))

    def test_workflow_memory_records_and_suggests_activities(self):
        memory = WorkflowMemory(path="./test_memory.json")
        memory.record("Check emails", "browse", "completed", notes="first")
        memory.record("Download a report", "download", "completed", notes="second")

        self.assertGreater(len(memory.recent()), 0)
        self.assertIn("browse", memory.suggest())
        self.assertIn("download", memory.suggest())

    def test_session_manager_persists_browser_state(self):
        with tempfile.TemporaryDirectory() as td:
            manager = PersistentSessionManager("demo-session", storage_dir=td)
            manager.save({"logged_in": True, "site": "example.com"})

            reloaded = PersistentSessionManager("demo-session", storage_dir=td)
            self.assertTrue(reloaded.get("logged_in"))
            self.assertEqual(reloaded.get("site"), "example.com")

    def test_command_queue_runs_approved_tasks_in_order(self):
        queue = CommandQueue()
        queue.enqueue("open dashboard")
        queue.enqueue("download report")

        executed = []
        while not queue.empty():
            executed.append(queue.dequeue())

        self.assertEqual(executed, ["open dashboard", "download report"])


if __name__ == "__main__":
    unittest.main()
