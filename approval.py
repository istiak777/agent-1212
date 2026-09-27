"""approval.py - ask the user (typed OR spoken) before the agent acts.

    ask_permission(url)   -> may I open this domain, and in which browser?
    ask_yes_no(question)  -> may I proceed with this sensitive action?

Answer by typing, or press Enter on an empty line and speak.
Examples: "yes chrome", "2", "allow edge always", "no".

Voice is optional (typing always works):
    pip install SpeechRecognition pyttsx3 PyAudio
"""
import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

APPROVED_FILE = Path(__file__).with_name("approved_domains.json")

# browser-use drives Chromium-family browsers only, so Firefox is not listed.
BROWSER_CANDIDATES = {
    "Chrome": [
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
        "google-chrome",
    ],
    "Edge": [
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
        "microsoft-edge",
    ],
    "Brave": [
        r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe",
        "brave-browser",
    ],
}
BUILTIN = "Chromium"  # the browser bundled with browser-use (no path needed)

YES_WORDS = {"yes", "yeah", "yep", "ok", "okay", "allow", "approve", "approved",
             "sure", "proceed", "continue", "go", "permit", "granted"}
NO_WORDS = {"no", "nope", "deny", "denied", "stop", "cancel", "block", "never",
            "dont", "don't", "refuse", "reject"}
ALWAYS_WORDS = {"always", "remember", "forever"}
NUMBER_WORDS = {"one": 1, "first": 1, "two": 2, "second": 2, "three": 3,
                "third": 3, "four": 4, "fourth": 4, "five": 5, "fifth": 5}


@dataclass
class Decision:
    approved: bool
    domain: str = ""
    browser_name: Optional[str] = None
    browser_path: Optional[str] = None  # None -> built-in Chromium
    remember: bool = False


# ---------------------------------------------------------------- browsers
def detect_browsers():
    """Return {name: path} for installed Chromium-family browsers."""
    found = {}
    for name, candidates in BROWSER_CANDIDATES.items():
        for candidate in candidates:
            path = os.path.expandvars(candidate)
            if os.path.isfile(path):
                found[name] = path
                break
            on_path = shutil.which(candidate)
            if on_path:
                found[name] = on_path
                break
    return found


# ------------------------------------------------------------- voice in/out
def speak(text):
    try:
        import pyttsx3

        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass  # spoken prompts are optional


def listen(timeout=8):
    try:
        import speech_recognition as sr
    except ImportError:
        print("(Voice is not installed. Run: pip install SpeechRecognition PyAudio)")
        return None
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("Listening... speak now.")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=8)
        return recognizer.recognize_google(audio)  # needs internet
    except sr.WaitTimeoutError:
        print("(I heard nothing.)")
    except sr.UnknownValueError:
        print("(I could not understand that.)")
    except sr.RequestError as exc:
        print(f"(Speech service error: {exc})")
    except OSError:
        print("(No microphone found.)")
    return None


def get_reply(voice=True):
    """Type an answer, or press Enter on an empty line to speak."""
    hint = "Type your answer (or press Enter to speak): " if voice else "Type your answer: "
    try:
        raw = input(hint).strip()
    except EOFError:
        return ""
    if raw or not voice:
        return raw
    heard = listen()
    if heard:
        print(f'Heard: "{heard}"')
        return heard
    return ""


# ----------------------------------------------------------------- parsing
def _words(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def parse_reply(text, options):
    """Return (approved True/False/None, chosen option or None, remember)."""
    words = _words(text)

    if any(w in NO_WORDS for w in words):  # a "no" always wins
        return False, None, False

    approved = True if any(w in YES_WORDS for w in words) else None
    remember = any(w in ALWAYS_WORDS for w in words)

    chosen = None
    for name in options:  # "chrome", "edge", "chromium"...
        if name.lower() in words:
            chosen = name
    if chosen is None:  # "2", "two", "second"
        for w in words:
            index = int(w) if w.isdigit() else NUMBER_WORDS.get(w)
            if index and 1 <= index <= len(options):
                chosen = options[index - 1]
                break
    if chosen is None and "default" in words:
        chosen = BUILTIN

    if chosen is not None and approved is None:
        approved = True  # picking a browser implies yes
    return approved, chosen, remember


# ------------------------------------------------------- remembered domains
def _load_approved():
    try:
        return json.loads(APPROVED_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_approved(data):
    APPROVED_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _domain(url):
    if "://" not in url:
        url = "https://" + url
    return (urlparse(url).hostname or "").lower()


# ------------------------------------------------------------------ public
def ask_yes_no(question, voice=True):
    """Ask a yes/no question. Anything unclear counts as NO."""
    print(f"\n{question}")
    if voice:
        speak(question)
    for _ in range(3):
        reply = get_reply(voice)
        approved, _, _ = parse_reply(reply, [])
        if approved is not None:
            return approved
        print(f'I didn\'t understand "{reply}". Please say or type yes or no.')
    return False


def ask_permission(url, voice=True):
    """Ask whether this domain may be opened, and in which browser."""
    domain = _domain(url)
    browsers = detect_browsers()
    options = list(browsers) + [BUILTIN]

    saved = _load_approved().get(domain)
    if saved:  # approved earlier with "always"
        name = saved if saved in options else BUILTIN
        return Decision(True, domain, name, browsers.get(name), True)

    print(f"\nThe agent wants to open: {domain}")
    print("This domain is not approved yet. Browsers available:")
    for i, name in enumerate(options, 1):
        label = f"{name} (built-in)" if name == BUILTIN else name
        print(f"  {i}. {label}")
    print('Say or type e.g. "yes chrome", "2", "allow edge always", or "no".')
    if voice:
        speak(f"I want to open {domain}. Do you allow it, and which browser?")

    approved, chosen, remember = None, None, False
    for _ in range(3):
        reply = get_reply(voice)
        a, c, r = parse_reply(reply, options)
        if a is False:
            print("Denied. Nothing was opened.")
            return Decision(False, domain)
        approved = a if a is not None else approved
        chosen = c or chosen
        remember = remember or r
        if approved and chosen:
            break
        if approved:
            print("Which browser? (name or number)")
        else:
            print(f'I didn\'t understand "{reply}". Please say yes or no, and which browser (e.g. "yes chrome").')

    if not approved:
        print("No clear answer. Nothing was opened.")
        return Decision(False, domain)

    chosen = chosen or BUILTIN
    if remember:
        data = _load_approved()
        data[domain] = chosen
        _save_approved(data)
    return Decision(True, domain, chosen, browsers.get(chosen), remember)


if __name__ == "__main__":  # manual test:  python approval.py
    print(ask_permission("https://example.com"))