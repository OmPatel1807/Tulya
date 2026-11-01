"""
backend/eval/measure_smoothness.py
Playwright Script for Measuring Frame Times, P95, and Long Tasks during Scripted Scroll.
"""

import sys
import time
import numpy as np
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"

def measure_scroll_performance(duration_sec=5.0, throttle_cpu_rate=1):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--enable-webgl",
                "--ignore-gpu-blocklist",
                "--use-gl=angle",
                "--use-angle=gl",
                "--disable-frame-rate-limit"
            ]
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        if throttle_cpu_rate > 1:
            cdp = context.new_cdp_session(page)
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": throttle_cpu_rate})

        page.goto(f"{BASE_URL}/")
        page.wait_for_selector("#story-canvas")
        page.wait_for_timeout(1000)

        # Inject performance instrumentation
        page.evaluate("""
            window.__frameTimes = [];
            window.__longTasks = 0;
            let lastT = performance.now();
            
            // Monitor long tasks
            if ('PerformanceObserver' in window) {
                try {
                    const observer = new PerformanceObserver((list) => {
                        window.__longTasks += list.getEntries().length;
                    });
                    observer.observe({ entryTypes: ['longtask'] });
                } catch(e) {}
            }

            // Frame timing recorder
            function recordFrame(now) {
                const dt = now - lastT;
                lastT = now;
                if (window.__recordingActive) {
                    window.__frameTimes.push(dt);
                }
                requestAnimationFrame(recordFrame);
            }
            requestAnimationFrame(recordFrame);
        """)

        # Start recording and perform continuous smooth scroll down inside browser rAF
        page.evaluate(f"""
            window.__recordingActive = true;
            new Promise((resolve) => {{
                const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
                const duration = {duration_sec} * 1000;
                const start = performance.now();
                function step(now) {{
                    const elapsed = now - start;
                    const p = Math.min(1.0, elapsed / duration);
                    window.scrollTo(0, maxScroll * p);
                    if (p < 1.0) {{
                        requestAnimationFrame(step);
                    }} else {{
                        window.__recordingActive = false;
                        resolve();
                    }}
                }}
                requestAnimationFrame(step);
            }});
        """)
        
        # Wait for duration
        page.wait_for_timeout(int(duration_sec * 1000) + 600)

        # Retrieve measurements
        data = page.evaluate("""() => {
            return {
                frameTimes: window.__frameTimes,
                longTasks: window.__longTasks
            };
        }""")

        browser.close()

        frame_times = np.array(data["frameTimes"])
        # Drop the first frame if it's an outlier initialization spike
        if len(frame_times) > 10:
            frame_times = frame_times[1:]

        p50 = float(np.percentile(frame_times, 50))
        p95 = float(np.percentile(frame_times, 95))
        p99 = float(np.percentile(frame_times, 99))
        mean_ft = float(np.mean(frame_times))
        max_ft = float(np.max(frame_times))
        fps = 1000.0 / mean_ft if mean_ft > 0 else 0
        frames_over_33 = int(np.sum(frame_times > 33.33))
        frames_over_50 = int(np.sum(frame_times > 50.0))
        total_frames = len(frame_times)

        results = {
            "total_frames": total_frames,
            "avg_fps": round(fps, 1),
            "mean_ms": round(mean_ft, 2),
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "p99_ms": round(p99, 2),
            "max_ms": round(max_ft, 2),
            "frames_over_33ms": frames_over_33,
            "frames_over_50ms": frames_over_50,
            "long_tasks": data["longTasks"]
        }
        return results

if __name__ == "__main__":
    throttle = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(f"Measuring scroll performance (CPU throttle: {throttle}x)...")
    res = measure_scroll_performance(duration_sec=6.0, throttle_cpu_rate=throttle)
    print("\n--- RESULTS ---")
    for k, v in res.items():
        print(f"  {k}: {v}")

