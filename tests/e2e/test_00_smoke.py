"""Smoke scenario: proves the E2E harness itself works (CLI, browser, real Claude API).

No ticket functionality is exercised here.
"""
from pathlib import Path

from playwright.sync_api import Page, expect

from ambrogio import __version__, config

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_entrypoint_runs(run_cli):
    proc = run_cli("--version")
    assert proc.stdout.strip() == f"ambrogio {__version__}"


def test_browser_drives_a_page(page: Page, static_server):
    base = static_server(FIXTURES)
    page.goto(f"{base}/smoke.html")
    expect(page).to_have_title("Ambrogio smoke")
    page.get_by_role("button", name="Avanza").click()
    expect(page.locator("#out")).to_have_text("passo 1")


def test_claude_returns_structured_output(claude):
    """One cheap real call with forced tool use; assert on shape, not wording."""
    tool = {
        "name": "report_nil",
        "description": "Report one Milan NIL (Nucleo di Identità Locale) name and a priority.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nil": {"type": "string"},
                "priorita": {"type": "string", "enum": ["alta", "media", "bassa"]},
            },
            "required": ["nil", "priorita"],
        },
    }
    response = claude.messages.create(
        model=config.cheap_model(),
        max_tokens=200,
        tools=[tool],
        tool_choice={"type": "tool", "name": "report_nil"},
        messages=[{"role": "user", "content": "Name any NIL of Milan and give it a priority."}],
    )
    calls = [b for b in response.content if b.type == "tool_use"]
    assert len(calls) == 1
    out = calls[0].input
    assert isinstance(out["nil"], str) and out["nil"].strip()
    assert out["priorita"] in {"alta", "media", "bassa"}
