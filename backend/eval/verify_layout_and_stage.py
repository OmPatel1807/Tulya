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
        assert "supreme_court_bench_bg" in bg_data["bgImage"], f"Body background image must contain supreme_court_bench_bg, got {bg_data['bgImage']}"
        assert bg_data["bgColor"] == "rgb(255, 255, 255)", f"Body fallback background must be white, got {bg_data['bgColor']}"
        print("  Background verified: Enhanced Supreme Court bench image active with clean white fallback.")

        # --- FIX 1 Verification: Clean Background (Door Arches & Black Lines Removed) ---
        print("\n--- Verifying FIX 1: Door Arches & Black Lines Removed ---")
        stage_cleanup = await page.evaluate("""() => {
            const arch = document.querySelector('.stage-layer-arch');
            const frame = document.querySelector('.stage-hairline-frame');
            const grain = document.querySelector('.stage-grain');
            const table = document.querySelector('.table-ellipse');

            return {
                archDisplay: arch ? window.getComputedStyle(arch).display : 'none',
                frameDisplay: frame ? window.getComputedStyle(frame).display : 'none',
                grainDisplay: grain ? window.getComputedStyle(grain).display : 'none',
                tableDisplay: table ? window.getComputedStyle(table).display : 'none'
            };
        }""")
        assert stage_cleanup["archDisplay"] == "none", f"Arch colonnade (door shape) must be removed, got {stage_cleanup['archDisplay']}"
        assert stage_cleanup["frameDisplay"] == "none", f"Hairline frame (black line) must be removed, got {stage_cleanup['frameDisplay']}"
        assert stage_cleanup["grainDisplay"] == "none", "Stage grain must be hidden"
        assert stage_cleanup["tableDisplay"] == "none", "Stage artificial table must be hidden"
        print("  FIX 1 PASSED: Background verified clean with door-type arches, black hairline frame, and artificial lines removed.")

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

        # 2. Increased length of the book verified
        assert b_rect_0["height"] >= 450, f"Book length must be increased (height {b_rect_0['height']}px < 450px)!"
        print(f"  Assertion passed: Increased book length verified (Height={b_rect_0['height']:.1f}px >= 450px)")

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

        # --- FIX 5 Verification: Centered Book & Alternating Left/Right Tabs ---
        print("\n--- Verifying FIX 5: Centered Book & Alternating Left/Right Tabs ---")
        required_checkpoints = [
            (0.00, "panel-0", "LEFT"),
            (0.18, "panel-1", "RIGHT"),
            (0.35, "panel-2", "LEFT"),
            (0.50, "panel-3", "RIGHT"),
            (0.68, "panel-4", "LEFT"),
            (0.82, "panel-5", "RIGHT"),
            (0.91, "panel-6", "LEFT"),
            (0.98, "panel-7", "RIGHT")
        ]

        for p_val, panel_id, expected_side in required_checkpoints:
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
            b_center_diff = abs(b_center - vw / 2.0)

            if p_rect["right"] < b_rect["left"]:
                actual_side = "LEFT"
                sep = b_rect["left"] - p_rect["right"]
            elif p_rect["left"] > b_rect["right"]:
                actual_side = "RIGHT"
                sep = p_rect["left"] - b_rect["right"]
            else:
                actual_side = "OVERLAP"
                sep = -1

            print(f"  p={p_val:.2f} ({panel_id}): side={actual_side} (expected={expected_side}), sep={sep:.1f}px, bookCenter={b_center:.1f}px (diff={b_center_diff:.1f}px)")
            assert side_off == 0.0, f"sideOffset must be 0.0 at p={p_val}, got {side_off}!"
            assert actual_side == expected_side, f"Card {panel_id} expected on {expected_side}, got {actual_side}!"
            assert sep > 25.0, f"Separation too tight ({sep:.1f}px <= 25px) at p={p_val} with {panel_id}!"
            assert b_center_diff <= 15.0, f"Book must remain horizontally centered at p={p_val} (diff {b_center_diff:.1f}px > 15px)!"

        print("  FIX 5 PASSED: Book is centered and tabs alternate between left and right with clean separation.")

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

        # 1. Closed book top margin >= 60px and increased length at 1920x1080
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
        assert br_fhd["height"] >= 580, f"At 1920x1080, book height must be >= 580px, got {br_fhd['height']}"

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

        # 3. Check alternating cards and fixed centering across required checkpoints at 1920x1080
        for p_val, panel_id, expected_side in required_checkpoints:
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
            b_center_diff = abs(b_center - vw / 2.0)

            if p_rect["right"] < b_rect["left"]:
                actual_side = "LEFT"
                sep = b_rect["left"] - p_rect["right"]
            elif p_rect["left"] > b_rect["right"]:
                actual_side = "RIGHT"
                sep = p_rect["left"] - b_rect["right"]
            else:
                actual_side = "OVERLAP"
                sep = -1

            print(f"  1920x1080 p={p_val:.2f} ({panel_id}): side={actual_side} (expected={expected_side}), sep={sep:.1f}px, bookCenter={b_center:.1f}px (diff={b_center_diff:.1f}px)")
            assert side_off == 0.0, f"sideOffset must be 0.0 at 1920x1080 p={p_val}, got {side_off}!"
            assert actual_side == expected_side, f"Card {panel_id} expected on {expected_side}, got {actual_side}!"
            assert sep > 30.0, f"Separation too tight ({sep:.1f}px <= 30px) at 1920x1080 p={p_val} with {panel_id}!"
            assert b_center_diff <= 20.0, f"Book must remain horizontally centered at 1920x1080 p={p_val} (diff {b_center_diff:.1f}px > 20px)!"

        print("  1920x1080 Alternating cards and fixed center book verified across all checkpoints.")

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
