# Web scraping + Claude Code tooling stack (installed 22–23 Aug 2026)

Prathap's default web-data + agent-efficiency stack. All installed on the Windows
PC; the Mac (excoboard) mirrors it. **Obscura is the shared stealth browser; the
scrapers route through it.**

## The tools

| Tool | What it does | How to run / use |
|---|---|---|
| **Obscura** | Rust stealth headless browser (fingerprint randomisation, tracker blocking). The shared browser backend. | Docker: `docker run -d --name obscura -p 127.0.0.1:9222:9222 obscura:local`. CDP endpoint: **`ws://127.0.0.1:9222/devtools/browser`** (HTTP discovery: `http://127.0.0.1:9222/json/version`). |
| **Scrapling** | Adaptive Python scraper (anti-bot, fast parse). MCP: `scrapling`. | Python/CLI fetchers (`DynamicFetcher`, `StealthyFetcher`) take **`cdp_url=`** — pass Obscura's CDP to scrape THROUGH the stealth browser. MCP server has no cdp flag (own browser for simple pages). |
| **Firecrawl** (self-host) | URL → clean markdown / structured JSON for LLMs. MCP: `firecrawl`. | Self-host stack: `cd ~/tools/firecrawl && docker compose up -d`; API at **`http://localhost:3002`** (`POST /v1/scrape {"url":..,"formats":["markdown"]}`). Runs its OWN browser — NOT CDP-wired to Obscura without patching apps/playwright-service-ts. |
| **codeburn** | Token/usage baseline tracker. | `npx codeburn` / `codeburn web`. |
| **rtk** | Compresses noisy command output for the agent. | `rtk` (in `~/.local/bin`). |
| **serena** | Code symbol search/edit assistant. MCP: `serena`. | `uv tool` install; MCP `serena start-mcp-server --context claude-code`. |
| **brain** | Durable-decisions store (Open Project Brain Standard). | CLI `brain`; brain data lives in the alpha-finance repo (`brain/`), git-synced cross-machine. See the repo's `knowledge-sources` brain page. |

## The wiring (Obscura as the shared stealth browser)

- **Obscura CDP** = `ws://127.0.0.1:9222/devtools/browser`. It is a drop-in headless-Chrome that Playwright-based tools connect to via `connectOverCDP`.
- **Scrapling → Obscura: WIRED + PROVEN.** For tough / anti-bot sites, fetch through Obscura:
  ```python
  from scrapling.fetchers import DynamicFetcher   # or StealthyFetcher
  page = DynamicFetcher.fetch('https://target', cdp_url='ws://127.0.0.1:9222/devtools/browser')
  ```
  (Verified 23-Aug: example.com fetched status 200 via Obscura.)
- **Firecrawl → Obscura: NOT wired.** Firecrawl's playwright-service launches its own Chromium and exposes no external-CDP env; routing it through Obscura needs a code patch to `apps/playwright-service-ts`. Left standalone for now.

## MCP servers (in `~/.claude.json` → top-level `mcpServers`)
`context7` (pre-existing), `scrapling`, `serena`, `firecrawl` (pointed at the local self-host `http://localhost:3002`). **New MCP servers only load after a Claude Code restart.**

## Choosing a tool
- Clean text/markdown from a URL, or a crawl → **Firecrawl**.
- Adaptive scrape / anti-bot / a site that fights back → **Scrapling via Obscura** (`cdp_url`).
- Need a raw stealth browser for another Playwright/CDP tool → **Obscura** (`ws://127.0.0.1:9222`).

## Persistence note
Firecrawl (compose) and Obscura (`docker run`) are started manually — they do NOT
auto-start on reboot unless a `--restart unless-stopped` policy is added. After a
machine restart, bring them back up with the run commands above.
