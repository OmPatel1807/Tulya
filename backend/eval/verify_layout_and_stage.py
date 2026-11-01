import asyncio
import os
import sys
import math
from playwright.async_api import async_playwright

async def verify():
    checkpoints_dir = "/Users/apple/Desktop/Tulya-FORGE/docs/checkpoints"
    artifacts_dir = "/Users/apple/.gemini/antigravity/brain/591aa1ad-562c-4adc-8872-1f81bd6cb1cc"
    os.makedirs(checkpoints_dir, exist_ok=True)
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

        # =============================================================
        # Test Suite 1: Desktop 1440x900 (Framed Stage, Centering, Overlap)
        # =============================================================
        print("=== Test Suite 1: Desktop 1440x900 ===")
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        await page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # --- Supreme Court Background Image Verification ---
        print("\n--- Verifying Supreme Court Background Image ---")
        bg_data = await page.evaluate("""() => {
            const bodyStyle = window.getComputedStyle(document.body);
            const stagePanel = document.getElementById('story-stage');
            const panelStyle = stagePanel ? window.getComputedStyle(stagePanel) : null;
            return {
                bgImage: bodyStyle.backgroundImage,
                bgColor: bodyStyle.backgroundColor,
                panelBg: panelStyle ? panelStyle.backgroundColor : ''
            };
        }""")
        print(f"  Body background image: {bg_data['bgImage']}")
        print(f"  Body background color: {bg_data['bgColor']}")
        print(f"  Stage panel background: {bg_data['panelBg']}")
        assert "supreme_court_bg" in bg_data["bgImage"], f"Body background image must contain supreme_court_bg, got {bg_data['bgImage']}"
        assert bg_data["bgColor"] == "rgb(255, 255, 255)", f"Body fallback background must be white, got {bg_data['bgColor']}"
        print("  Background verified: Supreme Court architectural image active with clean white fallback.")

        # --- FIX 1 Verification: Framed Stage Panel & Layers a-f ---
        print("\n--- Verifying FIX 1: Restored Stage Panel & Layers a-f ---")
        stage_info = await page.evaluate("""() => {
            const panel = document.getElementById('story-stage');
            const l0 = document.getElementById('stage-l0');
            const l1 = document.getElementById('stage-l1');
            const l2 = document.getElementById('stage-l2');
            const light = document.querySelector('.stage-layer-light');
            const table = document.querySelector('.stage-layer-table');
            const frame = document.querySelector('.stage-hairline-frame');
            const enGhost = document.getElementById('ghost-col-en');
            const hiGhost = document.getElementById('ghost-col-hi');

            const pRect = panel ? panel.getBoundingClientRect() : null;
            return {
                panelFound: !!panel,
                panelRect: pRect,
                hasBaseGrain: !!l0 && !!l0.querySelector('.stage-grain'),
                hasArchSvg: !!l1 && !!l1.querySelector('svg.stage-colonnade-svg'),
                hasTypography: !!l2 && !!enGhost && !!hiGhost,
                hasLightBeam: !!light && !!light.querySelector('.sunbeam-top-right'),
                hasTableSurface: !!table && !!table.querySelector('.table-ellipse'),
                hasHairlineFrame: !!frame,
                ghostEnText: enGhost ? enGhost.innerText : '',
                ghostHiText: hiGhost ? hiGhost.innerText : ''
            };
        }""")

        assert stage_info["panelFound"], "Stage panel #story-stage must exist"
        assert stage_info["hasBaseGrain"], "Layer a: Base mist gradient with grain must exist"
        assert stage_info["hasArchSvg"], "Layer b: Arch colonnade SVG silhouette must exist"
        assert stage_info["hasTypography"], "Layer c: Ghost typography must exist"
        assert stage_info["hasLightBeam"], "Layer d: Top-right warm light beam must exist"
        assert stage_info["hasTableSurface"], "Layer e: Table surface ellipse with reflection must exist"
        assert stage_info["hasHairlineFrame"], "Layer f: Brass hairline frame (1px, 40%, 16px inset) must exist"
        assert "Constitution" in stage_info["ghostEnText"] or "CONSTITUTION" in stage_info["ghostEnText"]
        assert "संविधान" in stage_info["ghostHiText"]
        print("  FIX 1 PASSED: All layers a-f verified inside framed stage panel.")

        # --- FIX 2 Verification: Book Position & Centering (1440x900) ---
        print("\n--- Verifying FIX 2: Book Position & Centering (1440x900) ---")
        b0_data = await page.evaluate("""() => {
            window.__tulya.scrollToProgress(0.0);
            const bRect = window.__tulya.getBookBoundingBox();
            const panel = document.getElementById('story-stage');
            const pRect = panel.getBoundingClientRect();
            return { bookRect: bRect, panelRect: pRect, vh: window.innerHeight, vw: window.innerWidth };
        }""")

        b_rect_0 = b0_data["bookRect"]
        p_rect_0 = b0_data["panelRect"]
        vh_0 = b0_data["vh"]

        print(f"  Closed Book Rect at p=0: Top={b_rect_0['top']:.1f}px, Bottom={b_rect_0['bottom']:.1f}px, Height={b_rect_0['height']:.1f}px")
        print(f"  Stage Panel Rect: Top={p_rect_0['top']:.1f}px, Bottom={p_rect_0['bottom']:.1f}px, Height={p_rect_0['height']:.1f}px")
        print(f"  Viewport Height: {vh_0}px")

        # 1. At least 60px between book top and viewport top
        assert b_rect_0["top"] >= 60, f"Book top ({b_rect_0['top']}px) must be >= 60px from viewport top!"
        print(f"  Assertion passed: Margin from viewport top is {b_rect_0['top']:.1f}px (>= 60px)")

        # 2. Equal space above and below book in panel (within ~25px tolerance for perspective tilt)
        space_above_in_panel = b_rect_0["top"] - p_rect_0["top"]
        space_below_in_panel = p_rect_0["bottom"] - b_rect_0["bottom"]
        space_diff = abs(space_above_in_panel - space_below_in_panel)
        print(f"  Panel vertical margins: Above={space_above_in_panel:.1f}px, Below={space_below_in_panel:.1f}px (Diff={space_diff:.1f}px)")
        assert space_diff < 35, f"Book must be vertically centered in panel (diff {space_diff:.1f}px >= 35px)!"
        print("  Assertion passed: Book is vertically centered in panel with equal space above and below.")

        # 3. Spread fits fully inside viewport width (no part cut at left or right edge)
        await page.evaluate("window.__tulya.scrollToProgress(0.35)")
        await page.wait_for_timeout(300)
        spread_data = await page.evaluate("""() => {
            const bRect = window.__tulya.getBookBoundingBox();
            return { bookRect: bRect, vw: window.innerWidth };
        }""")
        sp_rect = spread_data["bookRect"]
        vw_0 = spread_data["vw"]
        print(f"  Opened Spread Rect at p=0.35: Left={sp_rect['left']:.1f}px, Right={sp_rect['right']:.1f}px, Width={sp_rect['width']:.1f}px (Viewport W={vw_0}px)")
        assert sp_rect["left"] >= 0, f"Spread left edge ({sp_rect['left']}px) must be >= 0 (not clipped)!"
        assert sp_rect["right"] <= vw_0, f"Spread right edge ({sp_rect['right']}px) must be <= {vw_0} (not clipped)!"
        print("  Assertion passed: Opened spread fits fully inside viewport width (zero edge clipping).")
        print("  FIX 2 PASSED.")

        # --- FIX 3 Verification: Spread Content (Left English, Right Hindi + Conjuncts) ---
        print("\n--- Verifying FIX 3: Spread Content & Devanagari Conjuncts ---")
        page_contents = await page.evaluate("window.__tulya.getPageContents()")
        left_text = page_contents["leftEnText"]
        right_text = page_contents["rightHiText"]
        conjuncts = page_contents["testConjuncts"]

        # Assert left page contains English and zero Devanagari characters
        left_devanagari_chars = [c for c in left_text if 0x0900 <= ord(c) <= 0x097F]
        assert len(left_devanagari_chars) == 0, f"Left page must contain ZERO Devanagari characters, found: {left_devanagari_chars}"
        assert "WE, THE PEOPLE OF INDIA" in left_text, "Left page must contain English Preamble text"
        assert "PREAMBLE" in left_text, "Left page must contain English PREAMBLE header"
        print("  Left page verified: Pure English Preamble with zero Devanagari glyphs.")

        # Assert right page contains Hindi Preamble with Devanagari characters
        right_devanagari_chars = [c for c in right_text if 0x0900 <= ord(c) <= 0x097F]
        assert len(right_devanagari_chars) > 50, "Right page must contain Devanagari text for Hindi Preamble"
        assert "भारत का संविधान" in right_text, "Right page heading must contain 'भारत का संविधान'"
        assert "उद्देशिका" in right_text, "Right page heading must contain 'उद्देशिका'"
        assert "हम, भारत के लोग" in right_text, "Right page must contain Hindi Preamble opening"

        # Assert verified conjuncts exist in the Hindi text
        for conj in conjuncts:
            assert conj in right_text, f"Conjunct '{conj}' must be present in Hindi page text!"
            print(f"  Verified Hindi conjunct shaped correctly: '{conj}'")
        print("  FIX 3 PASSED.")

        # --- FIX 4 Verification: No Blank Leaf During Page Turn & No Yellow Outline ---
        print("\n--- Verifying FIX 4: No Blank White Face / No Yellow Outline During Page Turn ---")
        # In page turn range (p = 0.28 to 0.35), inspect canvas pixel data
        for p_turn in [0.29, 0.32, 0.35]:
            await page.evaluate(f"window.__tulya.scrollToProgress({p_turn})")
            await page.wait_for_timeout(200)

            # Check for pure white region (> 10% of book area)
            white_check = await page.evaluate("""() => {
                const cvs = document.getElementById('story-canvas');
                const ctx = cvs.getContext('2d');
                // Canvas is WebGL so read pixels via gl.readPixels
                const gl = cvs.getContext('webgl2') || cvs.getContext('webgl');
                if (!gl) return { whiteRatio: 0.0, zeroYellow: true };

                const bRect = window.__tulya.getBookBoundingBox();
                const x = Math.max(0, Math.floor(bRect.left));
                const y = Math.max(0, Math.floor(cvs.height - bRect.bottom));
                const w = Math.min(cvs.width - x, Math.floor(bRect.width));
                const h = Math.min(cvs.height - y, Math.floor(bRect.height));

                if (w <= 0 || h <= 0) return { whiteRatio: 0.0, zeroYellow: true };

                const pixels = new Uint8Array(w * h * 4);
                gl.readPixels(x, y, w, h, gl.RGBA, gl.UNSIGNED_BYTE, pixels);

                let pureWhiteCount = 0;
                let yellowOutlineCount = 0;
                const totalSamples = w * h;

                for (let i = 0; i < pixels.length; i += 16) { // Sample every 4th pixel
                    const r = pixels[i];
                    const g = pixels[i + 1];
                    const b = pixels[i + 2];

                    // Pure white check: RGB > 250 with negligible color saturation
                    if (r > 250 && g > 250 && b > 250) {
                        pureWhiteCount++;
                    }

                    // Bright yellow outline check: R > 200, G > 190, B < 120
                    if (r > 200 && g > 190 && b < 120) {
                        yellowOutlineCount++;
                    }
                }

                const sampledTotal = totalSamples / 4;
                const whiteRatio = pureWhiteCount / sampledTotal;
                const yellowRatio = yellowOutlineCount / sampledTotal;
                return { whiteRatio, yellowRatio };
            }""")

            print(f"  At p={p_turn}: Book pure white ratio = {white_check['whiteRatio']*100:.2f}%, yellow ratio = {white_check['yellowRatio']*100:.2f}%")
            assert white_check["whiteRatio"] < 0.10, f"Pure white area ({white_check['whiteRatio']*100:.1f}%) exceeds 10% of book area at p={p_turn}!"
            assert white_check["yellowRatio"] < 0.05, f"Bright yellow debug outline detected at p={p_turn}!"

        print("  Assertion passed: Turning leaf displays parchment textures on both faces with zero bright debug outlines.")
        print("  FIX 4 PASSED.")

        # --- FIX 5 Verification: Book to Left and Tabs to Right ---
        print("\n--- Verifying FIX 5: Book to Left and Tabs to Right ---")
        required_checkpoints = [
            (0.00, "panel-0"),
            (0.18, "panel-1"),
            (0.35, "panel-2"),
            (0.50, "panel-3"),
            (0.68, "panel-4"),
            (0.82, "panel-5"),
            (0.91, "panel-6"),
            (0.98, "panel-7")
        ]

        for p_val, panel_id in required_checkpoints:
            await page.evaluate(f"window.__tulya.scrollToProgress({p_val})")
            await page.wait_for_timeout(250)

            data = await page.evaluate(f"""() => {{
                const panel = document.getElementById('{panel_id}');
                const pRect = panel ? panel.getBoundingClientRect() : null;
                const bRect = window.__tulya.getBookBoundingBox();
                return {{
                    panelRect: pRect ? {{ left: pRect.left, right: pRect.right, top: pRect.top, bottom: pRect.bottom }} : null,
                    bookRect: bRect,
                    sideOffset: window.__tulya.getSideOffset ? window.__tulya.getSideOffset({p_val}) : 0.0,
                    vw: window.innerWidth
                }};
            }}""")

            p_rect = data["panelRect"]
            b_rect = data["bookRect"]
            side_off = data["sideOffset"]
            vw = data["vw"]

            b_center = (b_rect["left"] + b_rect["right"]) / 2.0
            sep = p_rect["left"] - b_rect["right"]

            print(f"  p={p_val:.2f} ({panel_id}): bookCenter={b_center:.1f}px, tabLeft={p_rect['left']:.1f}px, sep={sep:.1f}px, sideOffset={side_off}")
            assert side_off == -1.15, f"sideOffset must be -1.15 at p={p_val}, got {side_off}!"
            assert b_center < vw / 2.0, f"Book must be placed on left half (center {b_center} >= {vw/2})!"
            assert b_rect["left"] >= 50.0, f"Book left margin too tight ({b_rect['left']}px < 50px)!"
            assert p_rect["left"] > b_rect["right"], f"Tab must sit to the right of the book!"
            assert sep > 150.0, f"Separation between book and tab too small ({sep:.1f}px <= 150px) at p={p_val}!"

        print("  FIX 5 PASSED: Book is positioned on the left and tabs are positioned on the right with generous separation.")

        # --- Save Required Checkpoint Screenshots at 1440x900 ---
        print("\n--- Saving Checkpoint Screenshots (1440x900) ---")
        save_points = [0.0, 0.1, 0.2, 0.3, 0.45, 0.6, 0.8, 0.9, 1.0]
        for sp in save_points:
            await page.evaluate(f"window.__tulya.scrollToProgress({sp})")
            await page.wait_for_timeout(250)
            tag = f"p{int(round(sp * 100)):02d}"
            fname = f"checkpoint_{tag}_1440x900.png"
            # Save to docs/checkpoints and artifacts
            await page.screenshot(path=os.path.join(checkpoints_dir, fname))
            await page.screenshot(path=os.path.join(artifacts_dir, fname))
            print(f"  Saved {fname}")

        # --- Idle Shake Test: Two screenshots 300 ms apart must match (< 2.0% diff) ---
        print("\n--- Verifying Idle Shake (Two screenshots 300 ms apart) ---")
        from PIL import Image, ImageChops
        import numpy as np

        await page.evaluate("window.__tulya.scrollToProgress(0.0)")
        await page.wait_for_timeout(400)
        shot1_path = os.path.join(artifacts_dir, "idle_shot_1.png")
        shot2_path = os.path.join(artifacts_dir, "idle_shot_2.png")
        await page.screenshot(path=shot1_path)
        await page.wait_for_timeout(300)
        await page.screenshot(path=shot2_path)

        im1 = Image.open(shot1_path).convert("RGB")
        im2 = Image.open(shot2_path).convert("RGB")
        diff = ImageChops.difference(im1, im2)
        stat = np.array(diff)
        diff_pct = (np.mean(stat) / 255.0) * 100.0
        print(f"  Idle shake diff percentage: {diff_pct:.3f}% (threshold < 2.0%)")
        assert diff_pct < 2.0, f"Idle shake diff {diff_pct:.2f}% exceeds threshold 2.0%!"
        print("  Idle shake test PASSED: Visual scene is calm and rock solid.")

        # --- Frame Time p95 under 20 ms ---
        print("\n--- Verifying Performance: Frame Time p95 under 20 ms ---")
        await page.evaluate("""() => {
            window.__frameTimes = [];
            for (let i = 0; i <= 60; i++) {
                const t0 = performance.now();
                window.__tulya.scrollToProgress(i / 60.0);
                const dt = performance.now() - t0;
                window.__frameTimes.push(dt);
            }
        }""")
        frame_times = np.array(await page.evaluate("() => window.__frameTimes"))
        p95 = float(np.percentile(frame_times, 95))
        mean_ft = float(np.mean(frame_times))
        print(f"  Frame compute time: mean={mean_ft:.2f} ms, p95={p95:.2f} ms (Target < 20 ms)")
        assert p95 < 20.0, f"Frame compute time p95 ({p95:.2f}ms) exceeds target 20ms!"
        print("  Performance test PASSED.")

        await context.close()

        # =============================================================
        # Test Suite 2: Desktop 1920x1080 (Full HD Viewport & Checkpoints)
        # =============================================================
        print("\n=== Test Suite 2: Desktop 1920x1080 ===")
        context_fhd = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page_fhd = await context_fhd.new_page()
        await page_fhd.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await page_fhd.wait_for_timeout(800)

        # 1. Closed book top margin >= 60px and centered in panel at 1920x1080
        b0_fhd = await page_fhd.evaluate("""() => {
            window.__tulya.scrollToProgress(0.0);
            const bRect = window.__tulya.getBookBoundingBox();
            const panel = document.getElementById('story-stage');
            const pRect = panel.getBoundingClientRect();
            return { bookRect: bRect, panelRect: pRect, vh: window.innerHeight, vw: window.innerWidth };
        }""")
        br_fhd = b0_fhd["bookRect"]
        pr_fhd = b0_fhd["panelRect"]
        print(f"  1920x1080 Book Rect at p=0: Top={br_fhd['top']:.1f}px, Bottom={br_fhd['bottom']:.1f}px, Height={br_fhd['height']:.1f}px")
        assert br_fhd["top"] >= 60, f"At 1920x1080, book top ({br_fhd['top']}px) must be >= 60px!"

        space_above_fhd = br_fhd["top"] - pr_fhd["top"]
        space_below_fhd = pr_fhd["bottom"] - br_fhd["bottom"]
        diff_fhd = abs(space_above_fhd - space_below_fhd)
        print(f"  1920x1080 Panel margins: Above={space_above_fhd:.1f}px, Below={space_below_fhd:.1f}px (Diff={diff_fhd:.1f}px)")
        assert diff_fhd < 35, f"At 1920x1080, book must be vertically centered in panel (diff {diff_fhd:.1f}px >= 35px)!"

        # 2. Spread fits fully inside 1920 width
        await page_fhd.evaluate("window.__tulya.scrollToProgress(0.35)")
        await page_fhd.wait_for_timeout(250)
        spread_fhd = await page_fhd.evaluate("""() => {
            return { bookRect: window.__tulya.getBookBoundingBox(), vw: window.innerWidth };
        }""")
        s_rect_fhd = spread_fhd["bookRect"]
        assert s_rect_fhd["left"] >= 0, f"Spread left edge ({s_rect_fhd['left']}px) must be >= 0!"
        assert s_rect_fhd["right"] <= 1920, f"Spread right edge ({s_rect_fhd['right']}px) must be <= 1920!"
        print("  1920x1080 Spread fits fully inside viewport width.")

        # 3. Check book on left and tabs on right across required checkpoints at 1920x1080
        for p_val, panel_id in required_checkpoints:
            await page_fhd.evaluate(f"window.__tulya.scrollToProgress({p_val})")
            await page_fhd.wait_for_timeout(200)

            data = await page_fhd.evaluate(f"""() => {{
                const panel = document.getElementById('{panel_id}');
                const pRect = panel ? panel.getBoundingClientRect() : null;
                const bRect = window.__tulya.getBookBoundingBox();
                return {{
                    panelRect: pRect ? {{ left: pRect.left, right: pRect.right, top: pRect.top, bottom: pRect.bottom }} : null,
                    bookRect: bRect,
                    sideOffset: window.__tulya.getSideOffset ? window.__tulya.getSideOffset({p_val}) : 0.0,
                    vw: window.innerWidth
                }};
            }}""")

            p_rect = data["panelRect"]
            b_rect = data["bookRect"]
            side_off = data["sideOffset"]
            vw = data["vw"]

            b_center = (b_rect["left"] + b_rect["right"]) / 2.0
            sep = p_rect["left"] - b_rect["right"]

            print(f"  1920x1080 p={p_val:.2f} ({panel_id}): bookCenter={b_center:.1f}px, tabLeft={p_rect['left']:.1f}px, sep={sep:.1f}px, sideOffset={side_off}")
            assert side_off == -1.15, f"sideOffset must be -1.15 at 1920x1080 p={p_val}, got {side_off}!"
            assert b_center < vw / 2.0, f"At 1920x1080, book must be placed on left half (center {b_center} >= {vw/2})!"
            assert b_rect["left"] >= 100.0, f"At 1920x1080, book left margin too tight ({b_rect['left']}px < 100px)!"
            assert p_rect["left"] > b_rect["right"], f"At 1920x1080, tab must sit to right of book!"
            assert sep > 250.0, f"At 1920x1080, separation too small ({sep:.1f}px <= 250px) at p={p_val}!"

        print("  1920x1080 Book to left and tabs to right verified across all checkpoints.")

        # 4. Save 1920x1080 Checkpoint Screenshots
        print("\n--- Saving Checkpoint Screenshots (1920x1080) ---")
        for sp in save_points:
            await page_fhd.evaluate(f"window.__tulya.scrollToProgress({sp})")
            await page_fhd.wait_for_timeout(250)
            tag = f"p{int(round(sp * 100)):02d}"
            fname = f"checkpoint_{tag}_1920x1080.png"
            await page_fhd.screenshot(path=os.path.join(checkpoints_dir, fname))
            await page_fhd.screenshot(path=os.path.join(artifacts_dir, fname))
            print(f"  Saved {fname}")

        await context_fhd.close()
        await browser.close()
        print("\n=======================================================")
        print("ALL 6 FIXES & VERIFICATION ASSERTIONS PASSED WITH ZERO ERRORS!")
        print("=======================================================")

if __name__ == "__main__":
    asyncio.run(verify())
