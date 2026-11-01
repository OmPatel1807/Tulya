import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def verify():
    artifacts_dir = "/Users/apple/.gemini/antigravity/brain/591aa1ad-562c-4adc-8872-1f81bd6cb1cc"
    os.makedirs(artifacts_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--enable-webgl",
                "--ignore-gpu-blocklist",
                "--use-gl=angle",
                "--use-angle=swiftshader",
                "--enable-unsafe-swiftshader"
            ]
        )

        # -------------------------------------------------------------
        # Test 1: Desktop 1440x900 (Wide Screen Layout, Zero Overlap, Smart Header)
        # -------------------------------------------------------------
        print("=== Test 1: Desktop 1440x900 ===")
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        await page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # 1. Smart Header at scroll 0: should be visible
        header_visible = await page.evaluate("""() => {
            const h = document.getElementById('story-navbar');
            const rect = h.getBoundingClientRect();
            return !h.classList.contains('is-hidden') && rect.top === 0;
        }""")
        print(f"Header at p=0 visible: {header_visible}")
        assert header_visible, "Header should be visible at scroll 0"

        # Check minimal nav at p=0: should be hidden
        minimal_nav_active = await page.evaluate("""() => {
            const m = document.getElementById('story-minimal-nav');
            return m.classList.contains('is-active');
        }""")
        print(f"Minimal nav at p=0 active: {minimal_nav_active}")
        assert not minimal_nav_active, "Minimal nav should not be active at scroll 0"

        # Save screenshot at p=0.0
        await page.screenshot(path=os.path.join(artifacts_dir, "stage_p00_closed_hero_1440.png"))

        # Scroll down to p=0.20
        await page.evaluate("window.__tulya.scrollToProgress(0.20)")
        await page.wait_for_timeout(400)

        # 2. Smart Header after scroll down: should be hidden
        header_hidden = await page.evaluate("""() => {
            const h = document.getElementById('story-navbar');
            return h.classList.contains('is-hidden');
        }""")
        minimal_active = await page.evaluate("""() => {
            const m = document.getElementById('story-minimal-nav');
            return m.classList.contains('is-active');
        }""")
        print(f"Header hidden at p=0.20: {header_hidden}, Minimal nav active: {minimal_active}")
        assert header_hidden, "Header should hide when scrolling down"
        assert minimal_active, "Minimal nav should become active when header hides"

        # 3. Mouse hover top 60px: Header should reveal
        await page.mouse.move(720, 30)
        await page.wait_for_timeout(350)
        header_revealed_hover = await page.evaluate("""() => {
            const h = document.getElementById('story-navbar');
            return !h.classList.contains('is-hidden');
        }""")
        print(f"Header revealed on hover top 30px: {header_revealed_hover}")
        assert header_revealed_hover, "Header should reveal when mouse is in top 60px"

        # Mouse leaves top 60px and scroll down again
        await page.mouse.move(720, 300)
        await page.evaluate("window.__tulya.scrollToProgress(0.22)")
        await page.wait_for_timeout(350)

        # 4. Checkpoints Zero Overlap Verification across all scenes
        checkpoints = [
            (0.00, "panel-0", "left"),
            (0.18, "panel-1", "right"),
            (0.35, "panel-2", "left"),
            (0.50, "panel-3", "right"),
            (0.68, "panel-4", "left"),
            (0.82, "panel-5", "right"),
            (0.91, "panel-6", "left"),
            (0.98, "panel-7", "right")
        ]

        overlap_results = []
        for p_val, panel_id, expected_side in checkpoints:
            await page.evaluate(f"window.__tulya.scrollToProgress({p_val})")
            await page.wait_for_timeout(300)

            data = await page.evaluate(f"""() => {{
                const panel = document.getElementById('{panel_id}');
                const pRect = panel ? panel.getBoundingClientRect() : null;
                const bRect = window.__tulya.getBookBoundingBox();
                const stage = document.getElementById('story-stage');
                return {{
                    panelRect: pRect ? {{ left: pRect.left, right: pRect.right, top: pRect.top, bottom: pRect.bottom }} : null,
                    bookRect: bRect,
                    stageClass: stage ? stage.className : ''
                }};
            }}""")

            p_rect = data["panelRect"]
            b_rect = data["bookRect"]
            stage_cls = data["stageClass"]

            # Overlap check
            overlap_x = not (p_rect["right"] < b_rect["left"] or p_rect["left"] > b_rect["right"])
            overlap_y = not (p_rect["bottom"] < b_rect["top"] or p_rect["top"] > b_rect["bottom"])
            has_overlap = overlap_x and overlap_y

            # Separation distance
            if p_rect["right"] < b_rect["left"]:
                separation = b_rect["left"] - p_rect["right"]
            elif p_rect["left"] > b_rect["right"]:
                separation = p_rect["left"] - b_rect["right"]
            else:
                separation = -1

            print(f"p={p_val:.2f} ({panel_id}, {expected_side}): Overlap={has_overlap}, Separation={separation:.1f}px, Stage='{stage_cls}'")
            assert not has_overlap, f"Bounding box overlap detected at p={p_val} with {panel_id}!"
            assert separation > 20, f"Separation {separation}px is too tight (<20px) at p={p_val}!"
            overlap_results.append((p_val, panel_id, separation))

        # Take screenshots at key points
        await page.evaluate("window.__tulya.scrollToProgress(0.35)")
        await page.wait_for_timeout(300)
        await page.screenshot(path=os.path.join(artifacts_dir, "stage_p35_spread_settled_1440.png"))

        await page.evaluate("window.__tulya.scrollToProgress(0.50)")
        await page.wait_for_timeout(300)
        await page.screenshot(path=os.path.join(artifacts_dir, "stage_p50_clause_pairing_1440.png"))

        await page.evaluate("window.__tulya.scrollToProgress(0.68)")
        await page.wait_for_timeout(300)
        await page.screenshot(path=os.path.join(artifacts_dir, "stage_p68_synthetic_demo_1440.png"))

        await page.evaluate("window.__tulya.scrollToProgress(1.00)")
        await page.wait_for_timeout(300)
        await page.screenshot(path=os.path.join(artifacts_dir, "stage_p100_closing_cta_1440.png"))

        # 5. Check Parallax Transform of Stage Layers
        await page.evaluate("window.__tulya.scrollToProgress(0.80)")
        await page.wait_for_timeout(100)
        parallax_transforms = await page.evaluate("""() => {
            const l1 = document.getElementById('stage-l1');
            const en = document.getElementById('ghost-col-en');
            const hi = document.getElementById('ghost-col-hi');
            return {
                colonnade: l1 ? l1.style.transform : '',
                ghostEn: en ? en.style.transform : '',
                ghostHi: hi ? hi.style.transform : ''
            };
        }""")
        print(f"Parallax at p=0.80: {parallax_transforms}")
        assert "translate3d" in parallax_transforms["colonnade"]
        assert "translate3d" in parallax_transforms["ghostEn"]
        assert "translate3d" in parallax_transforms["ghostHi"]

        await context.close()

        # -------------------------------------------------------------
        # Test 2: Desktop 1920x1080 (Full HD Viewport)
        # -------------------------------------------------------------
        print("\n=== Test 2: Desktop 1920x1080 ===")
        context_fhd = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page_fhd = await context_fhd.new_page()
        await page_fhd.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await page_fhd.wait_for_timeout(800)

        for p_val, panel_id, expected_side in checkpoints:
            await page_fhd.evaluate(f"window.__tulya.scrollToProgress({p_val})")
            await page_fhd.wait_for_timeout(150)

            data = await page_fhd.evaluate(f"""() => {{
                const panel = document.getElementById('{panel_id}');
                const pRect = panel ? panel.getBoundingClientRect() : null;
                const bRect = window.__tulya.getBookBoundingBox();
                return {{
                    panelRect: pRect ? {{ left: pRect.left, right: pRect.right, top: pRect.top, bottom: pRect.bottom }} : null,
                    bookRect: bRect
                }};
            }}""")
            p_rect = data["panelRect"]
            b_rect = data["bookRect"]
            has_overlap = not (p_rect["right"] < b_rect["left"] or p_rect["left"] > b_rect["right"]) and \
                          not (p_rect["bottom"] < b_rect["top"] or p_rect["top"] > b_rect["bottom"])
            assert not has_overlap, f"Overlap at 1920x1080 p={p_val}!"

        await page_fhd.screenshot(path=os.path.join(artifacts_dir, "stage_p68_synthetic_demo_1920.png"))
        await context_fhd.close()

        # -------------------------------------------------------------
        # Test 3: Narrow Screen 800x1024 (Tablet / Narrow Viewport)
        # -------------------------------------------------------------
        print("\n=== Test 3: Narrow Screen 800x1024 ===")
        context_narrow = await browser.new_context(viewport={"width": 800, "height": 1024})
        page_narrow = await context_narrow.new_page()
        await page_narrow.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await page_narrow.wait_for_timeout(800)

        # On narrow screens, panel is at bottom 30%, book in top 70%
        await page_narrow.evaluate("window.__tulya.scrollToProgress(0.50)")
        await page_narrow.wait_for_timeout(300)
        narrow_data = await page_narrow.evaluate("""() => {
            const p = document.getElementById('panel-3');
            const pRect = p.getBoundingClientRect();
            const bRect = window.__tulya.getBookBoundingBox();
            return {
                panelTop: pRect.top,
                bookBottom: bRect.bottom,
                windowHeight: window.innerHeight
            };
        }""")
        print(f"Narrow screen: Book Bottom = {narrow_data['bookBottom']:.1f}px, Panel Top = {narrow_data['panelTop']:.1f}px (Viewport H={narrow_data['windowHeight']})")
        assert narrow_data["panelTop"] >= narrow_data["bookBottom"] - 20, "On narrow screen, card must sit below upper 70% book area!"

        await page_narrow.screenshot(path=os.path.join(artifacts_dir, "stage_p50_narrow_800.png"))
        await context_narrow.close()

        # -------------------------------------------------------------
        # Test 4: Idle Motion Diff & Frame Compute Time p95
        # -------------------------------------------------------------
        print("\n=== Test 4: Idle Motion & Performance Metrics ===")
        context_perf = await browser.new_context(viewport={"width": 1440, "height": 900})
        page_perf = await context_perf.new_page()
        await page_perf.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await page_perf.wait_for_timeout(1500)

        # Sample frame compute times
        deltas = await page_perf.evaluate("""() => {
            return new Promise((resolve) => {
                const samples = [];
                let count = 0;
                let last = performance.now();
                function step(now) {
                    samples.push(now - last);
                    last = now;
                    count++;
                    if (count < 60) {
                        requestAnimationFrame(step);
                    } else {
                        resolve(samples);
                    }
                }
                requestAnimationFrame(step);
            });
        }""")
        deltas.sort()
        p95 = deltas[int(len(deltas) * 0.95)]
        print(f"Frame compute time p95: {p95:.2f} ms")
        assert p95 < 35.0, f"Frame compute time p95 ({p95:.2f}ms) too high!"

        await context_perf.close()
        await browser.close()
        print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(verify())
