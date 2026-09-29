"""Pretty-print results, save to a file, and copy to the clipboard."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

LAST_OUTPUT_PATH = Path(__file__).with_name("last_output.txt")

SECTION_ORDER = (
    "SOURCE",
    "TITLE",
    "SHORT EXPLANATION",
    "POST",
    "HASHTAGS",
    "COMMENT",
)


def _normalize_heading(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip().upper())


def parse_sections(text: str) -> dict[str, str]:
    """Split model output into labeled sections when headings are present."""
    pattern = re.compile(
        r"^(SOURCE|TITLE|SHORT EXPLANATION|POST|HASHTAGS|COMMENT)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = list(pattern.finditer(text or ""))
    if not matches:
        return {}

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        label = _normalize_heading(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[label] = text[start:end].strip()
    return sections


def build_aligned_text(result: dict) -> str:
    """Return a clean, aligned writeup with SOURCE always visible."""
    body = (result.get("result") or "").strip()
    source = (result.get("source") or "").strip()
    sections = parse_sections(body)

    if not sections:
        lines = []
        if source:
            lines.append(f"SOURCE:\n{source}")
            lines.append("")
        lines.append("RESULT:")
        lines.append(body or "(empty)")
        return "\n".join(lines).strip() + "\n"

    if source and not sections.get("SOURCE"):
        sections["SOURCE"] = source
    elif source:
        sections["SOURCE"] = source

    blocks = []
    for label in SECTION_ORDER:
        value = sections.get(label)
        if value:
            blocks.append(f"{label}:\n{value}")

    for label, value in sections.items():
        if label not in SECTION_ORDER and value:
            blocks.append(f"{label}:\n{value}")

    return "\n\n".join(blocks).strip() + "\n"


def save_output(text: str, path: Path = LAST_OUTPUT_PATH) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def copy_to_clipboard(text: str) -> bool:
    """Copy Unicode text on Windows via PowerShell Set-Clipboard."""
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Set-Clipboard -Value ([Console]::In.ReadToEnd())",
            ],
            input=text,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        return completed.returncode == 0
    except Exception:
        return False


def present_result(result: dict, interactive: bool = True) -> str:
    """Print aligned output, always save a copy file, optionally clipboard-copy."""
    aligned = build_aligned_text(result)
    saved = save_output(aligned)

    print("\n" + "=" * 60)
    print("ALIGNED OUTPUT")
    print("=" * 60)
    print(aligned)
    print("=" * 60)
    print(f"Saved copy: {saved}")
    print("Open that file in any editor if the terminal is hard to copy from.")

    if not interactive:
        return aligned

    print("\nCopy options:")
    print("  c  = copy full output to clipboard")
    print("  p  = copy POST passage only")
    print("  Enter = skip")
    try:
        choice = input("Choose: ").strip().lower()
    except EOFError:
        choice = ""

    if choice == "c":
        if copy_to_clipboard(aligned):
            print("Copied full output to clipboard.")
        else:
            print(f"Clipboard copy failed. Open the saved file instead: {saved}")
    elif choice == "p":
        sections = parse_sections(aligned)
        passage = sections.get("POST") or aligned
        if copy_to_clipboard(passage):
            print("Copied POST passage to clipboard.")
        else:
            print(f"Clipboard copy failed. Open the saved file instead: {saved}")

    return aligned
