"""
qc-smart.py — AI-powered "human eyes" QC check for Omni pages.

Uses browser-use to open an Omni page as the read-only QA identity and have an
AI agent look at it like a human tester would: is the layout broken, are labels
cut off, does the data look stale or nonsensical, are buttons missing, is
anything showing raw code or error messages a user should never see?

Usage:
    python qc-smart.py "/dashboard"
    python qc-smart.py "/dashboard" --click "Refresh"
    python qc-smart.py "/hris/leave" "/claims" "/payroll/payslips"

Needs: pip install browser-use
Keys:  OPENAI_API_KEY (reads from C:\\ai-cost-stack\\gateway\\.env if not set)
Token: ~/.omni-qa-token (refreshed by qc-token.sh)
"""
import asyncio
import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime


def load_env_key(name):
    """Load a key from the cost-stack .env if not already in environment."""
    if os.environ.get(name):
        return
    env_path = Path(r"C:\ai-cost-stack\gateway\.env")
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        if line.startswith(f"{name}="):
            os.environ[name] = line.split("=", 1)[1].strip().strip('"').strip("'")
            return


def load_qa_token():
    """Load the read-only QA token."""
    for p in [Path.home() / ".omni-qa-token", Path.home() / ".omni-e2e-token"]:
        if p.exists():
            return p.read_text().strip()
    return os.environ.get("OMNI_TOKEN", "")


def unmangle(p):
    """Undo Git Bash path mangling on Windows."""
    m = re.match(r'^[A-Za-z]:[\\/].*?[\\/]Git[\\/](.*)', p)
    return '/' + m.group(1).replace('\\', '/') if m else p


def parse_args():
    routes = []
    clicks = []
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--click" and i + 1 < len(sys.argv):
            clicks.append(sys.argv[i + 1])
            i += 2
        elif not sys.argv[i].startswith("--"):
            routes.append(unmangle(sys.argv[i]))
            i += 1
        else:
            i += 1
    return routes or ["/dashboard"], clicks


async def run_smart_check(route, clicks, token, base_url):
    """Run browser-use agent on one Omni page."""
    from browser_use import Agent, ChatOpenAI

    click_instructions = ""
    if clicks:
        click_instructions = (
            " Then click these buttons in order: "
            + ", ".join(f'"{c}"' for c in clicks) + "."
        )

    url = f"{base_url}{route}"

    # Navigate to the page and inject the token BEFORE the AI agent starts,
    # using initial_actions so the page is already authenticated.
    initial_actions = [
        {"navigate": {"url": url}},
        {"evaluate": {"code": f"localStorage.setItem('alpha_token', '{token}')"}},
        {"navigate": {"url": url}},  # reload with token set
        {"wait": {"seconds": 3}},
    ]

    task = f"""You are already on {url}, authenticated as a read-only test user.
Act as a quality tester. Look at this page like a real person and report:
1. Did the page load properly or is it blank/spinning/crashed?
2. Is any text cut off, overlapping, or unreadable?
3. Are there any error messages visible on screen?
4. Does the data look reasonable (not obviously wrong dates, impossible numbers, placeholder text)?
5. Are the main buttons and controls visible and properly labelled?
6. Is anything showing that a normal user should never see (raw code, stack traces, debug info)?
{click_instructions}

Write a SHORT plain-English verdict: CLEAN (everything looks good), MINOR (small
cosmetic issues), or PROBLEMS (something is clearly broken). Then list what you found
in bullet points. Be specific - name the exact element or text that is wrong."""

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    agent = Agent(
        task=task,
        llm=llm,
        use_vision=True,
        max_actions_per_step=5,
        initial_actions=initial_actions,
    )

    result = await agent.run(max_steps=10)
    return result.final_result()


async def main():
    load_env_key("OPENAI_API_KEY")
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: No OpenAI key found. Check C:\\ai-cost-stack\\gateway\\.env")
        sys.exit(1)

    token = load_qa_token()
    if not token:
        print("ERROR: No QA token. Run: bash qc-token.sh")
        sys.exit(1)

    routes, clicks = parse_args()
    base_url = os.environ.get("OMNI_BASE", "https://omni.alphadirect.co.bw")

    results = {}
    for route in routes:
        print(f"\n--- Checking {route} ---")
        try:
            verdict = await run_smart_check(route, clicks, token, base_url)
            results[route] = {"verdict": verdict, "error": None}
            print(verdict)
        except Exception as e:
            results[route] = {"verdict": None, "error": str(e)}
            print(f"FAILED: {e}")

    report_path = Path("qc-smart-report.json")
    report = {
        "timestamp": datetime.now().isoformat(),
        "routes": results,
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to {report_path.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
