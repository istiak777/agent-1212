import argparse
import asyncio
import json

from agent import ResearchAgent
from output_display import present_result


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a natural-language personal assistant with browser tools, memory, and permission-aware execution."
    )
    parser.add_argument(
        "command",
        nargs="?",
        help="A normal-language command like 'Open example.com and summarize it' or 'Download this image after approval'.",
    )
    parser.add_argument(
        "--request",
        help="What you want done with the page, e.g. 'Summarize the main points'.",
    )
    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Do not offer voice input or spoken prompts (typing only).",
    )
    parser.add_argument(
        "--source",
        help="Optional direct source URL or page to use when the command references a page.",
    )
    parser.add_argument(
        "--selector",
        help="Optional selector to focus extraction on a specific area of a page.",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Proceed with sensitive actions without prompting for permission.",
    )
    parser.add_argument(
        "--session-name",
        default="default",
        help="Session storage name for browser state and workflow memory.",
    )
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Legacy mode: print extracted source text only.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable result.",
    )
    return parser.parse_args()


async def run(args):
    command = args.command or ""
    if args.request:
        command = f"{args.request} {command}".strip()
    command = command or input("Enter your command: ").strip()
    if not command and not args.extract_only:
        raise SystemExit("Please provide a command.")

    agent = ResearchAgent(session_name=args.session_name, voice=not args.no_voice)

    if args.extract_only:
        source = args.source or input("Paste a link or enter a topic: ").strip()
        if not source:
            raise SystemExit("Please provide a link or topic.")

        print("Researching the source in Chromium...")
        document = await agent.research(source, selector=args.selector)
        if not document.text.strip():
            raise SystemExit("The selected page did not contain readable text.")

        result = {
            "requested_source": document.requested_source,
            "url": document.url,
            "title": document.title,
            "text": document.text,
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"\n--- {document.title} ---\n{document.text}")
        return

    source = args.source
    result = await agent.execute_command(
        command,
        source=source,
        selector=args.selector,
        auto_approve=args.approve,
        interactive=not args.json,  # --json is for scripts, so it never stops to ask
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["status"] == "awaiting_permission":
            print(f"\nPermission required: {result['message']}")
            print(f"Action: {result['action']}")
            if result.get("source"):
                print(f"Source: {result['source']}")
        elif result["status"] == "denied":
            print(f"\n{result['message']}")
        else:
            print(f"\nStatus: {result['status']}")
            print(f"Action: {result['action']}")
            present_result(result, interactive=not args.json)


if __name__ == "__main__":
    asyncio.run(run(parse_args()))