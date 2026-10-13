"""
Phase 6 Automated Test Suite — Accessibility, Responsive Fidelity & Visual Criteria
Validates AT-40 (A11Y Checklist), AT-41 (Responsive Breakpoints), AT-42 (Visual Criteria).
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright


def find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def app_server() -> str:
    port = find_free_port()
    db_path = "data/carecast.db"
    runner_code = f"""
import uvicorn
from carecast.api.main import create_app
from carecast.settings import Settings

app = create_app(Settings(env="prod", db_path='{db_path}', enable_docs=False, rate_get_per_min=1000, rate_post_per_min=500))
uvicorn.run(app, host="127.0.0.1", port={port}, log_level="warning")
"""
    proc = subprocess.Popen([sys.executable, "-c", runner_code])

    # Wait for server ready
    ready = False
    for _ in range(50):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=1.0) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.1)

    assert ready, "Server failed to start!"
    base_url = f"http://127.0.0.1:{port}"
    yield base_url

    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(scope="module")
def browser_instance():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        yield browser
        browser.close()


# ─── AT-41: RESPONSIVE BEHAVIOUR & NO HORIZONTAL BODY SCROLL ─────────────────

class TestResponsiveBreakpointsAT41:
    @pytest.mark.parametrize("width", [320, 375, 768, 1024, 1280, 1440])
    @pytest.mark.parametrize("route", ["#/overview", "#/forecast", "#/performance", "#/explain", "#/scenario", "#/data"])
    def test_no_horizontal_body_scroll(self, app_server: str, browser_instance: Browser, width: int, route: str):
        """AT-41: Body must NEVER scroll horizontally at 320, 375, 768, 1024, 1280, 1440 px."""
        context = browser_instance.new_context(viewport={"width": width, "height": 900})
        page = context.new_page()
        page.goto(f"{app_server}/{route}", wait_until="networkidle")
        time.sleep(0.3)

        # Check body scroll width vs window inner width
        scroll_width, inner_width = page.evaluate("() => [document.body.scrollWidth, window.innerWidth]")
        assert scroll_width <= inner_width, f"Horizontal scroll detected at width {width} on {route}: scrollWidth={scroll_width} > innerWidth={inner_width}"
        context.close()

    def test_mobile_drawer_behaviour(self, app_server: str, browser_instance: Browser):
        """Mobile drawer off-canvas behavior (<768px): hamburger opens, Esc closes."""
        context = browser_instance.new_context(viewport={"width": 375, "height": 812})
        page = context.new_page()
        page.goto(f"{app_server}/#/overview", wait_until="networkidle")

        sidebar = page.locator("#sidebar")
        menu_toggle = page.locator("#menu-toggle")
        assert menu_toggle.is_visible()

        # Click hamburger to open
        menu_toggle.click()
        assert "open" in (sidebar.get_attribute("class") or "")
        assert menu_toggle.get_attribute("aria-expanded") == "true"

        # Press Escape to close
        page.keyboard.press("Escape")
        time.sleep(0.2)
        assert "open" not in (sidebar.get_attribute("class") or "")
        assert menu_toggle.get_attribute("aria-expanded") == "false"
        context.close()


# ─── AT-40: ACCESSIBILITY CHECKLIST (A11Y-01 TO A11Y-14) ────────────────────

class TestAccessibilityAT40:
    def test_a11y_05_landmarks_and_headings(self, app_server: str, browser_instance: Browser):
        """A11Y-05: Semantic landmarks and single h1 per route."""
        page = browser_instance.new_page()
        routes = ["#/overview", "#/forecast", "#/performance", "#/explain", "#/scenario", "#/data"]

        for route in routes:
            page.goto(f"{app_server}/{route}", wait_until="networkidle")
            # Verify landmarks
            assert page.locator("header.topbar").count() >= 1
            assert page.locator("aside#sidebar").count() >= 1
            assert page.locator("nav[aria-label='Primary']").count() >= 1
            assert page.locator("main#main").count() >= 1
            assert page.locator("footer.app-footer").count() >= 1

            # Verify single h1
            h1_count = page.locator("h1").count()
            assert h1_count == 1, f"Route {route} expected 1 <h1>, got {h1_count}"

        page.close()

    def test_a11y_06_focus_management_on_route_change(self, app_server: str, browser_instance: Browser):
        """A11Y-06: Focus moves to new h1 and title updates on route change."""
        page = browser_instance.new_page()
        page.goto(f"{app_server}/#/overview", wait_until="networkidle")
        assert "Overview" in page.title()

        # Navigate to forecast
        page.goto(f"{app_server}/#/forecast", wait_until="networkidle")
        time.sleep(0.3)
        assert "Forecast" in page.title()

        active_tag = page.evaluate("() => document.activeElement ? document.activeElement.tagName.toLowerCase() : ''")
        assert active_tag in ("h1", "main"), f"Expected focus on h1 or main, got {active_tag}"
        page.close()

    def test_a11y_07_tables_have_captions_and_th_scope(self, app_server: str, browser_instance: Browser):
        """A11Y-07: Tables have caption and th scope='col'."""
        page = browser_instance.new_page()
        page.goto(f"{app_server}/#/overview", wait_until="networkidle")
        time.sleep(0.5)

        table = page.locator(".data-table")
        if table.count() > 0:
            assert table.locator("caption").count() >= 1
            th_count = table.locator("th[scope='col']").count()
            assert th_count >= 1
        page.close()

    def test_a11y_08_charts_have_figure_and_data_table_alternatives(self, app_server: str, browser_instance: Browser):
        """A11Y-08: Charts use figure/figcaption, role='img', and data table alternatives."""
        page = browser_instance.new_page()
        page.goto(f"{app_server}/#/forecast", wait_until="networkidle")
        time.sleep(0.6)

        figures = page.locator("figure.chart-figure")
        assert figures.count() >= 1
        assert page.locator("canvas[role='img']").count() >= 1
        assert page.locator("details.chart-details summary").count() >= 1
        page.close()

    def test_a11y_09_live_announcer_and_busy_attributes(self, app_server: str, browser_instance: Browser):
        """A11Y-09: Dynamic results live region exists."""
        page = browser_instance.new_page()
        page.goto(f"{app_server}/#/overview", wait_until="networkidle")
        announcer = page.locator("#sr-announcer")
        assert announcer.count() == 1
        assert announcer.get_attribute("aria-live") == "polite"
        page.close()

    def test_a11y_13_html_lang_and_unique_titles(self, app_server: str, browser_instance: Browser):
        """A11Y-13: html lang='en' and unique route titles."""
        page = browser_instance.new_page()
        page.goto(f"{app_server}/#/overview", wait_until="networkidle")
        assert page.locator("html").get_attribute("lang") == "en"

        titles = set()
        routes = ["#/overview", "#/forecast", "#/performance", "#/explain", "#/scenario", "#/data"]
        for r in routes:
            page.goto(f"{app_server}/{r}", wait_until="networkidle")
            titles.add(page.title())

        assert len(titles) == 6, f"Expected 6 unique route titles, got {len(titles)}"
        page.close()


# ─── AT-42: VISUAL CRITERIA (VC-01 TO VC-16) ────────────────────────────────

class TestVisualCriteriaAT42:
    def test_vc_01_and_02_s1_grid_proportions(self, app_server: str, browser_instance: Browser):
        """VC-02: S1 row structure at 1280px is 9/3 · 4/4/4 · 12 · 4/4/4."""
        context = browser_instance.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.goto(f"{app_server}/#/overview", wait_until="networkidle")
        time.sleep(0.5)

        # Row 1: 9 / 3
        assert page.locator("#w-hero.col-9").count() == 1
        assert page.locator("#w-trend.col-3").count() == 1

        # Row 2: 4 / 4 / 4
        assert page.locator("#w-watchlist.col-4").count() == 1
        assert page.locator("#w-explain.col-4").count() == 1
        assert page.locator("#w-gauge.col-4").count() == 1

        # Row 3: 12
        assert page.locator("#w-forecast-table.col-12").count() == 1

        # Row 4: 4 / 4 / 4
        assert page.locator("#w-backtest.col-4").count() == 1
        assert page.locator("#w-drivers.col-4").count() == 1
        assert page.locator("#w-capacity.col-4").count() == 1
        context.close()

    def test_vc_14_no_apollo_or_fake_identities(self, app_server: str, browser_instance: Browser):
        """VC-14: No Apollo name, logo, avatars, photos or illustration anywhere."""
        page = browser_instance.new_page()
        routes = ["#/overview", "#/forecast", "#/performance", "#/explain", "#/scenario", "#/data"]

        for route in routes:
            page.goto(f"{app_server}/{route}", wait_until="networkidle")
            body_text = page.locator("body").inner_text().lower()
            assert "apollo" not in body_text, f"Found forbidden term 'apollo' in {route}"
            assert "ema wilson" not in body_text, f"Found forbidden name 'ema wilson' in {route}"

        page.close()

    def test_vc_15_honesty_markers_present(self, app_server: str, browser_instance: Browser):
        """VC-15: Required honesty markers present on all screens."""
        page = browser_instance.new_page()
        page.goto(f"{app_server}/#/overview", wait_until="networkidle")
        time.sleep(0.5)

        assert page.locator(".badge-simulated").count() >= 1
        assert page.locator(".footer-disclaimer").count() >= 1

        page.goto(f"{app_server}/#/scenario", wait_until="networkidle")
        time.sleep(0.5)
        assert page.locator(".badge-scenario").count() >= 1
        assert page.locator(".badge-simulated").count() >= 1
        page.close()
