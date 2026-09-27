# AI-Harness

AI-Harness is a local, source-grounded research agent. It accepts a URL or a
topic, uses visible Chromium for web interaction and extraction, and uses a
local Ollama model to produce a professional text deliverable.

## Capabilities

- Direct URL browsing or Google topic search
- CSS-selector extraction for targeted page regions
- Source text limits and browser timing controlled by environment variables
- Local Ollama synthesis with prompt-injection-resistant source boundaries
- Extensible `ToolRegistry` for domain-specific tools
- Human-readable or JSON output for downstream workflows

## Setup

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull llama3.2:3b
python main.py
```

Ollama must be running locally, and Chromium must be available to
`browser-use`.

## Examples

```powershell
python main.py https://example.com
python main.py "renewable energy storage" --selector "main"
python main.py https://example.com --extract-only --json
python main.py https://example.com --request "Create a concise executive briefing"
```

Environment overrides:

```text
OLLAMA_MODEL=llama3.2:3b
BROWSER_HEADLESS=false
BROWSER_WAIT_SECONDS=3
MAX_SOURCE_CHARS=18000
```

## Extending the Agent

`BrowserToolkit` provides browser-facing operations. `ToolRegistry` is the
extension point for additional tools such as structured APIs, file analysis,
or domain-specific workflows. `ResearchAgent` accepts any compatible async
model object through its `model` argument, so an alternative local or open
source provider can be integrated without changing the CLI. Keep tool outputs
structured and pass only source material into synthesis. Treat all external
content as untrusted data, not as executable instructions.# agent-1212
