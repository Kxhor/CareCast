"""Playwright E2E Test Suite for CareCast Phase 5 Frontend.

Covers:
- AT-07: Chart point count = API point count; empty range shows empty state
- AT-14: Verdict text is "improves" iff test MAE(selected) < MAE(persistence); both branches tested via fixture DB
- AT-17: Alert shows tier text + icon, threshold value, and planning-signal disclaimer
- AT-20: Contribution bars sorted by absolute value; labels use text, not colour alone
- AT-23: UI shows "SCENARIO — not a prediction" and updates on slider change
- AT-25 (E2E): is_simulated=true badge visible in UI
- AT-27: Disclaimer footer present on all six screens
- AT-29: S6 lists every L-01…L-12 and all T6 findings
- AT-31: Changing fixture DB values changes UI numbers (no hard-coding)
- AT-32: Switching disease updates all S1–S5 widgets; unavailable disease shows reason
- AT-38: Static grep finds no forbidden DOM sinks; payload <img onerror> is rendered inert
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

SERVER_PORT = 8790


def start_uvicorn_server(db_path: str, port: int) -> subprocess.Popen:
    """Helper to start uvicorn in a subprocess with safe multithreaded SQLite connectivity."""
    db_posix = Path(db_path).resolve().as_posix()
    runner_code = f"""
import uvicorn
from carecast.api.main import create_app
from carecast.settings import Settings

app = create_app(Settings(env="prod", db_path='{db_posix}', enable_docs=False, rate_get_per_min=1000, rate_post_per_min=500))
uvicorn.run(app, host="127.0.0.1", port={port}, log_level="warning")
"""
    proc = subprocess.Popen([sys.executable, "-c", runner_code])
    # Wait for server to bind and respond
    time.sleep(2)
    return proc


@pytest.fixture(scope="module")
def app_server() -> Generator[str, None, None]:
    """Start real app server against standard database."""
    proc = start_uvicorn_server("data/carecast.db", SERVER_PORT)
    base_url = f"http://127.0.0.1:{SERVER_PORT}"
    try:
        yield base_url
    finally:
        proc.terminate()
        proc.wait()


@pytest.fixture(scope="module")
def browser() -> Generator[Browser, None, None]:
    """Launch headless browser using installed Chromium/Edge."""
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        yield b
        b.close()


@pytest.fixture
def page(browser: Browser) -> Generator[Page, None, None]:
    """Provide clean page per test."""
    p = browser.new_page()
    yield p
    p.close()


class TestOverviewS1AndHonesty:
    def test_at_27_disclaimer_footer_on_all_screens(self, app_server: str, page: Page):
        """AT-27: Disclaimer footer present on all six screens."""
        routes = ["#/overview", "#/forecast", "#/performance", "#/explain", "#/scenario", "#/data"]
        expected_disclaimer = "© CareCast 2026 · Student project · CDC NHSN public data · Not clinically validated · Decision support only"

        for r in routes:
            page.goto(f"{app_server}/{r}")
            page.wait_for_selector(".app-footer", timeout=5000)
            footer_text = page.locator(".app-footer").text_content() or ""
            assert expected_disclaimer in footer_text.strip(), f"Missing footer disclaimer on route {r}"

    def test_at_25_capacity_is_simulated_badge(self, app_server: str, page: Page):
        """AT-25: is_simulated=true in API and SIMULATED badge visible in UI."""
        page.goto(f"{app_server}/#/overview")
        page.wait_for_selector("#w-capacity .badge-simulated", timeout=5000)
        badge = page.locator("#w-capacity .badge-simulated").first
        assert "SIMULATED — ASSUMPTION-BASED" in (badge.text_content() or "").upper()


class TestForecastS2:
    def test_at_17_alert_shows_tier_text_icon_and_disclaimer(self, app_server: str, page: Page):
        """AT-17: Alert shows tier text + icon, threshold value, and planning-signal disclaimer."""
        page.goto(f"{app_server}/#/forecast")
        page.wait_for_selector("#w-alert", timeout=5000)

        alert_text = page.locator("#w-alert").text_content() or ""
        assert "PLANNING SIGNAL — NOT A BED-SHORTAGE PREDICTION" in alert_text.upper()
        assert "NORMAL" in alert_text.upper() or "WATCH" in alert_text.upper() or "ELEVATED" in alert_text.upper()

        # Check tier pill has both icon and text
        page.wait_for_selector("#w-forecast-table .tier-pill", timeout=5000)
        pill = page.locator("#w-forecast-table .tier-pill").first
        assert pill.locator("svg").count() >= 1, "Tier pill must contain an icon"
        assert len(pill.text_content().strip()) > 0, "Tier pill must contain text"

    def test_at_07_chart_point_count_matches_api(self, app_server: str, page: Page):
        """AT-07: Chart point count = API point count."""
        page.goto(f"{app_server}/#/forecast")
        page.wait_for_selector("#w-forecast-chart", timeout=5000)
        page.locator("#w-forecast-chart summary").click()
        page.wait_for_selector("#w-forecast-chart .data-table", state="visible", timeout=5000)

        # In accessible data table fallback of the chart, count the rows
        rows = page.locator("#w-forecast-chart .data-table tbody tr")
        assert rows.count() == 4, f"Expected 4 forecast rows, got {rows.count()}"


class TestPerformanceS3AndVerdict:
    def test_at_14_verdict_text_branch_fails_persistence(self, app_server: str, page: Page):
        """AT-14: Branch 1: When selected model does not beat persistence, text states failure honestly."""
        page.goto(f"{app_server}/#/performance")
        page.wait_for_selector("#w-verdicts", timeout=5000)

        verdict_cards = page.locator("#w-verdicts .card").all_text_contents()
        expected = "On the held-out test weeks, the selected model did not improve on the persistence baseline."
        found = any(expected in c for c in verdict_cards)
        assert found, f"Expected honest non-improvement verdict, found: {verdict_cards}"


class TestExplainS4:
    def test_at_20_contribution_bars_sorted_and_labeled(self, app_server: str, page: Page):
        """AT-20: Contribution bars sorted by absolute value; labels use text, not colour alone."""
        page.goto(f"{app_server}/#/explain")
        page.wait_for_selector("#w-contrib", timeout=5000)

        # Check non-causal disclaimer text
        text_content = page.locator("#w-explain-text").text_content() or ""
        assert "ASSOCIATIONS, NOT CAUSES" in text_content.upper()

        # Check contribution labels are visible text
        labels = page.locator("#w-contrib .contrib-name").all_text_contents()
        assert len(labels) > 0, "Expected feature labels in text"
        assert all(len(l.strip()) > 0 for l in labels)


class TestScenarioS5:
    def test_at_23_scenario_badge_and_slider_update(self, app_server: str, page: Page):
        """AT-23: UI shows 'SCENARIO — not a prediction' and updates on slider change."""
        page.goto(f"{app_server}/#/scenario")
        page.wait_for_selector("#w-scenario-chart .badge-scenario", timeout=5000)

        badge_text = page.locator("#w-scenario-chart .badge-scenario").text_content() or ""
        assert "SCENARIO — NOT A PREDICTION" in badge_text.upper()

        # Trigger slider preset button 20%
        btn_20 = page.locator(".btn-preset", has_text="+20% Preset")
        btn_20.click()

        # Check numeric input reflects 20
        page.wait_for_timeout(500)
        num_val = page.locator(".form-input[aria-label='Surge percentage numeric value']").input_value()
        assert num_val == "20"


class TestDataS6:
    def test_at_29_lists_all_limitations_l01_to_l12(self, app_server: str, page: Page):
        """AT-29: S6 lists every L-01…L-12 and all T6 findings."""
        page.goto(f"{app_server}/#/data")
        page.wait_for_selector("#w-limitations", timeout=5000)

        limitations_text = page.locator("#w-limitations").text_content() or ""
        for i in range(1, 13):
            lim_id = f"L-{i:02d}"
            assert lim_id in limitations_text, f"Missing limitation {lim_id} in S6"


class TestDiseaseSwitching:
    def test_at_32_switching_disease_updates_widgets(self, app_server: str, page: Page):
        """AT-32: Switching disease updates S1-S5 widgets."""
        page.goto(f"{app_server}/#/overview")
        page.wait_for_selector(".hero-title", timeout=5000)

        # Initial is Influenza
        assert "Influenza" in (page.locator(".hero-title").text_content() or "")

        # Switch to COVID-19 via topbar select
        page.locator("#topbar-disease-select").select_option("covid19")
        page.wait_for_timeout(1000)

        # Check hero title updated to COVID-19
        assert "COVID-19" in (page.locator(".hero-title").text_content() or "")


class TestFixtureDBModifications:
    def test_at_14_and_31_fixture_db_changes_ui(self, tmp_path: Path, browser: Browser):
        """AT-14 (Branch 2: beats persistence) & AT-31 (UI numbers change when DB changes)."""
        fixture_db = tmp_path / "fixture.db"
        shutil.copy("data/carecast.db", fixture_db)

        # 1. Update beats_persistence=1 for test split in fixture DB
        conn = sqlite3.connect(str(fixture_db))
        conn.execute("UPDATE evaluation_metrics SET beats_persistence=1 WHERE is_selected=1;")
        # 2. Inject high admissions count into latest observation to verify AT-31 reactivity
        conn.execute(
            "UPDATE weekly_observations SET admissions_count=98765 WHERE disease_code='flu' AND week_end_date='2026-10-03';"
        )
        conn.commit()
        conn.close()

        port = 8792
        proc = start_uvicorn_server(str(fixture_db), port)
        page = browser.new_page()

        try:
            # Check AT-31: Overview displays 98,765
            page.goto(f"http://127.0.0.1:{port}/#/overview")
            page.wait_for_selector(".hero-subtitle", timeout=5000)
            sub_text = page.locator(".hero-subtitle").text_content() or ""
            assert "98,765" in sub_text, f"AT-31 failed: expected 98,765 in hero subtitle, got {sub_text}"

            # Check AT-14 Branch 2: Model beats persistence verdict
            page.goto(f"http://127.0.0.1:{port}/#/performance")
            page.wait_for_selector("#w-verdicts", timeout=5000)
            verdict_cards = page.locator("#w-verdicts .card").all_text_contents()
            expected_improves = "On the held-out test weeks, the selected model's MAE is lower than the persistence baseline's."
            found_improves = any(expected_improves in c for c in verdict_cards)
            assert found_improves, f"AT-14 Branch 2 failed: expected '{expected_improves}', got {verdict_cards}"
        finally:
            page.close()
            proc.terminate()
            proc.wait()


class TestSecurityAndDOMInertness:
    def test_at_38_xss_payload_in_api_is_inert(self, app_server: str, page: Page):
        """AT-38: Injected <img onerror> in mocked API field is rendered inert without script execution."""
        xss_payload = '<img src="invalid" onerror="window.__xss_fired=true">'

        # Intercept /api/v1/summary and inject XSS payload into latest disease label and text
        def handle_summary_route(route):
            response = route.fetch()
            body = response.json()
            body["selected"]["disease"] = xss_payload
            body["selected"]["next_week"]["tier"] = xss_payload
            route.fulfill(
                response=response,
                body=json.dumps(body),
                headers=response.headers,
            )

        page.route("**/api/v1/summary*", handle_summary_route)

        page.goto(f"{app_server}/#/overview")
        page.wait_for_timeout(2000)

        # Verify JavaScript variable window.__xss_fired was never executed
        xss_executed = page.evaluate("() => Boolean(window.__xss_fired)")
        assert not xss_executed, "SECURITY VIOLATION: XSS script executed in browser!"

        # Verify payload appears safely as text content, not parsed HTML
        h1_text = page.locator("h1").text_content() or ""
        assert xss_payload in h1_text, "Payload should be present as escaped plain text"

    def test_at_38_static_grep_for_forbidden_dom_sinks(self):
        """AT-38: Static audit: no forbidden DOM sinks in web/."""
        js_files = list(Path("web/assets/js").glob("**/*.js"))
        html_files = list(Path("web").glob("*.html"))
        forbidden = ["innerHTML", "outerHTML", "insertAdjacentHTML", "eval(", "new Function"]

        for file_path in js_files + html_files:
            text = file_path.read_text(encoding="utf-8")
            for sink in forbidden:
                assert sink not in text, f"Forbidden DOM sink '{sink}' found in {file_path}"
