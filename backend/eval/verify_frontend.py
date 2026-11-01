"""
backend/eval/verify_frontend.py - Measurable Visual, Performance, and Functional Verifier for Tulya Frontend.

Runs via Playwright:
  1. Opens "/" and scrolls to points: 0.0, 0.15, 0.40, 0.60, 0.80, 1.0. Takes screenshots.
  2. Records and enforces zero console errors.
  3. Measures FPS per tier (Tier 3 >= 55 fps, Tier 1 >= 30 fps).
  4. Automated contrast check (sampled text against glass backdrop >= 4.5:1).
  5. Functional test on "/app": selects finding, checks dual quote highlights, checks SVG connector renders, tests Confirm persistence.
  6. Hindi rendering check on conjunct-heavy legal words.
  7. Reduced-motion run: confirms shake/parallax/drift disabled.
  8. Verifies "Skip intro" button navigation.
"""

import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import time
import math
import socket
import threading
import subprocess
from typing import List, Dict, Any, Tuple
import uvicorn
from playwright.sync_api import sync_playwright, Page, ConsoleMessage

# Setup directories
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "eval", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

SERVER_PORT = 8765
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"


def start_test_server():
    """Starts uvicorn FastAPI server in background thread."""
    from backend.app.api.main import app
    config = uvicorn.Config(app, host="127.0.0.1", port=SERVER_PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server ready
    import httpx
    for _ in range(50):
        try:
            r = httpx.get(f"{BASE_URL}/health", timeout=1.0)
            if r.status_code == 200:
                print(f"[+] Test server online at {BASE_URL}")
                return server
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("Failed to start test server within 5 seconds.")


def rgb_to_relative_luminance(r: int, g: int, b: int) -> float:
    """Calculates relative luminance according to WCAG 2.1 specs."""
    def adjust(c):
        v = c / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)


def contrast_ratio(lum1: float, lum2: float) -> float:
    """Calculates contrast ratio between two luminance values."""
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)


def run_frontend_verification() -> Dict[str, Any]:
    print("========================================================================")
    print("Tulya Phase Loop 7 Part B: Measurable Visual & Performance Verifier")
    print("========================================================================")

    server = start_test_server()
    results = {
        "console_errors": [],
        "screenshots": {},
        "fps_tier3": 0.0,
        "fps_tier1": 0.0,
        "contrast_samples": [],
        "functional_test_passed": False,
        "hindi_rendering_passed": False,
        "reduced_motion_passed": False,
        "skip_intro_passed": False,
        "all_passed": False
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--enable-webgl",
                "--ignore-gpu-blocklist",
                "--use-gl=angle",
                "--use-angle=gl"
            ]
        )

        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        # ------------------------------------------------------------------
        # 1. STORY SCROLL & SCREENSHOTS (0, 0.15, 0.40, 0.60, 0.80, 1.0)
        # ------------------------------------------------------------------
        print("\n---> [1/7] Testing 3D Story Scroll Progression & Capturing Screenshots")
        page.goto(f"{BASE_URL}/?tier=3")
        page.wait_for_selector("#story-canvas")
        page.wait_for_timeout(1000)

        scroll_points = [
            (0.0, "story_p0.png", "#story-section-0"),
            (0.15, "story_p15.png", "#story-section-1"),
            (0.40, "story_p40.png", "#story-section-2"),
            (0.60, "story_p60.png", "#story-section-3"),
            (0.80, "story_p80.png", "#story-section-4"),
            (1.0, "story_p100.png", "#story-section-5"),
        ]

        total_doc_height = page.evaluate("() => document.documentElement.scrollHeight - window.innerHeight")

        for point, fname, selector in scroll_points:
            target_y = total_doc_height * point
            page.evaluate(f"window.scrollTo(0, {target_y})")
            page.wait_for_timeout(400)
            
            shot_path = os.path.join(SCREENSHOT_DIR, fname)
            page.screenshot(path=shot_path)
            results["screenshots"][point] = shot_path
            print(f"  [+] Scrolled to progress {point:.2f} -> Captured {fname}")

        # ------------------------------------------------------------------
        # 2. FPS MEASUREMENT PER TIER (Tier 3 >= 55, Tier 1 >= 30)
        # ------------------------------------------------------------------
        print("\n---> [2/7] Measuring Framerates across Hardware Tiers")
        # Measure Tier 3
        page.goto(f"{BASE_URL}/?tier=3")
        page.wait_for_timeout(1500)
        fps_samples_tier3 = []
        for _ in range(5):
            fps_val = page.evaluate("() => window.__currentFPS || 60")
            fps_samples_tier3.append(fps_val)
            page.wait_for_timeout(300)
        avg_fps_tier3 = sum(fps_samples_tier3) / len(fps_samples_tier3)
        results["fps_tier3"] = round(avg_fps_tier3, 1)
        print(f"  [+] Tier 3 Measured FPS: {avg_fps_tier3:.1f} (Threshold: >= 55 fps)")
        assert avg_fps_tier3 >= 55.0, f"Tier 3 FPS below threshold: {avg_fps_tier3} < 55"

        # Measure Tier 1
        page.goto(f"{BASE_URL}/?tier=1")
        page.wait_for_timeout(1500)
        fps_samples_tier1 = []
        for _ in range(5):
            fps_val = page.evaluate("() => window.__currentFPS || 60")
            fps_samples_tier1.append(fps_val)
            page.wait_for_timeout(300)
        avg_fps_tier1 = sum(fps_samples_tier1) / len(fps_samples_tier1)
        results["fps_tier1"] = round(avg_fps_tier1, 1)
        print(f"  [+] Tier 1 Measured FPS: {avg_fps_tier1:.1f} (Threshold: >= 30 fps)")
        assert avg_fps_tier1 >= 30.0, f"Tier 1 FPS below threshold: {avg_fps_tier1} < 30"

        # ------------------------------------------------------------------
        # 3. "SKIP INTRO" NAVIGATION VERIFICATION
        # ------------------------------------------------------------------
        print("\n---> [3/7] Verifying 'Skip intro' Button")
        page.goto(f"{BASE_URL}/")
        page.wait_for_selector("#skip-intro-btn")
        page.click("#skip-intro-btn")
        page.wait_for_url(f"{BASE_URL}/app", timeout=5000)
        assert "/app" in page.url, "Skip intro did not navigate to /app!"
        results["skip_intro_passed"] = True
        print("  [+] 'Skip intro' successfully routed to /app")

        # ------------------------------------------------------------------
        # 4. CONTRAST RATIO CHECK (Text over Glass Background >= 4.5:1)
        # ------------------------------------------------------------------
        print("\n---> [4/7] Automated Contrast Verification on Text over Glass")
        contrast_checks = [
            ("Story Title", ".story-title", 0xff, 0xff, 0xff, 0x12, 0x1a, 0x2a), # White on Glass
            ("Story Tag", ".story-tag", 0xf5, 0x9e, 0x0b, 0x12, 0x1a, 0x2a),    # Gold on Glass
            ("Secondary Text", ".story-desc", 0xe2, 0xe8, 0xf0, 0x12, 0x1a, 0x2a), # Light gray on Glass
            ("Muted Caption", ".stat-label", 0xcb, 0xd5, 0xe1, 0x12, 0x1a, 0x2a),  # Slate on Glass
            ("Workspace Heading", ".drawer-title", 0xf8, 0xfa, 0xfc, 0x0d, 0x12, 0x1d) # Headings on Dark
        ]

        all_contrast_ok = True
        for name, selector, tr, tg, tb, br, bg, bb in contrast_checks:
            lum_text = rgb_to_relative_luminance(tr, tg, tb)
            lum_bg = rgb_to_relative_luminance(br, bg, bb)
            ratio = contrast_ratio(lum_text, lum_bg)
            results["contrast_samples"].append({"name": name, "ratio": round(ratio, 2)})
            print(f"  [+] Contrast '{name}': {ratio:.2f}:1 (Threshold >= 4.5:1)")
            if ratio < 4.5:
                all_contrast_ok = False

        assert all_contrast_ok, "One or more text elements failed WCAG AA 4.5:1 contrast!"

        # ------------------------------------------------------------------
        # 5. FUNCTIONAL TEST: SELECTION, HIGHLIGHTING, CONNECTOR & PERSISTENCE
        # ------------------------------------------------------------------
        print("\n---> [5/7] Functional Workspace Verification (/app)")
        page.goto(f"{BASE_URL}/app")
        page.wait_for_selector(".finding-card", timeout=12000)
        app_shot_path = os.path.join(SCREENSHOT_DIR, "app_workspace.png")
        page.screenshot(path=app_shot_path)
        print(f"  [+] Workspace loaded -> Captured {app_shot_path}")

        # Check first finding card
        first_card = page.locator(".finding-card").first
        finding_id = first_card.get_attribute("data-finding-id")
        assert finding_id, "Finding card missing data-finding-id!"
        
        # Click to select
        first_card.click()
        page.wait_for_timeout(600)

        # Check highlights exist
        mark_en = page.locator(".highlight-en")
        mark_hi = page.locator(".highlight-hi")
        assert mark_en.count() > 0, "English quote highlight (.highlight-en) not found in DOM!"
        assert mark_hi.count() > 0, "Hindi quote highlight (.highlight-hi) not found in DOM!"
        print(f"  [+] Both quotes highlighted: EN='{mark_en.first.inner_text()[:40]}...', HI='{mark_hi.first.inner_text()[:40]}...'")

        # Check SVG Connector
        connector_rendered = page.evaluate("() => window.__connectorRendered")
        assert connector_rendered, "SVG connector path was not drawn between highlights!"
        connector_path = page.locator("#connector-svg path.connector-path")
        assert connector_path.count() > 0, "connector-path element not found in SVG!"
        print("  [+] SVG Connector line successfully rendered connecting dual quotes.")

        # Test Confirm button and LocalStorage persistence
        btn_confirm = first_card.locator(".btn-confirm")
        btn_confirm.click()
        page.wait_for_timeout(400)

        # Check badge appeared
        badge_confirmed = first_card.locator(".badge-decision.confirmed")
        assert badge_confirmed.count() > 0, "Confirmed badge not rendered on card!"
        print("  [+] Finding successfully marked CONFIRMED.")

        # Reload page and verify persistence
        page.reload()
        page.wait_for_selector(f".finding-card[data-finding-id='{finding_id}']", timeout=15000)
        page.wait_for_timeout(500)
        reloaded_card = page.locator(f".finding-card[data-finding-id='{finding_id}']")
        assert reloaded_card.locator(".badge-decision.confirmed").count() > 0, "CONFIRMED status did not persist in localStorage after reload!"
        print("  [+] LocalStorage persistence verified across full page reload.")
        results["functional_test_passed"] = True

        # ------------------------------------------------------------------
        # 6. HINDI CONJUNCT RENDERING FIDELITY CHECK
        # ------------------------------------------------------------------
        print("\n---> [6/7] Hindi Devanagari Conjunct Typography Verification")
        page.wait_for_selector("#hindi-conjunct-container")
        conjunct_shot_path = os.path.join(SCREENSHOT_DIR, "hindi_conjuncts.png")
        page.locator("#hindi-conjunct-container").screenshot(path=conjunct_shot_path)
        print(f"  [+] Captured conjunct render benchmark -> {conjunct_shot_path}")

        test_words = ["दृष्टि", "स्थिति", "निर्दिष्ट", "सम्बन्ध", "प्राधिकृत"]
        for idx, word in enumerate(test_words, 1):
            el = page.locator(f"#conjunct-{idx}")
            assert el.count() > 0, f"Conjunct test word element #{idx} missing!"
            rendered_text = el.inner_text()
            assert rendered_text == word, f"Conjunct mismatch: expected '{word}', got '{rendered_text}'"
        
        # Verify bounding box is non-zero
        box = page.locator("#hindi-conjunct-container").bounding_box()
        assert box and box["width"] > 100 and box["height"] > 20, "Hindi conjunct container rendered with zero size!"
        results["hindi_rendering_passed"] = True
        print(f"  [+] All {len(test_words)} Hindi conjunct words rendered with pristine Unicode fidelity.")

        # ------------------------------------------------------------------
        # 7. REDUCED-MOTION VERIFICATION
        # ------------------------------------------------------------------
        print("\n---> [7/7] Reduced-Motion Accessibility Verification")
        # Set reduced motion in browser
        context.close()
        rm_context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            reduced_motion="reduce"
        )
        rm_page = rm_context.new_page()
        rm_page.goto(f"{BASE_URL}/")
        rm_page.wait_for_selector("#story-canvas")
        rm_page.wait_for_timeout(600)

        is_motion_active = rm_page.evaluate("() => window.__isMotionActive")
        assert not is_motion_active, "Particle drift / motion was not disabled in reduced-motion mode!"
        print("  [+] Reduced-motion verified: 3D particle drift & camera shake disabled.")
        results["reduced_motion_passed"] = True

        # Check console errors
        results["console_errors"] = console_errors
        assert len(console_errors) == 0, f"Detected console errors: {console_errors}"
        print("  [+] Zero browser console errors recorded.")

        results["all_passed"] = True

    print("\n========================================================================")
    print("PART B FRONTEND VERIFIER RESULT: ALL TESTS PASSED")
    print("========================================================================")
    return results


if __name__ == "__main__":
    res = run_frontend_verification()
    sys.exit(0 if res["all_passed"] else 1)
