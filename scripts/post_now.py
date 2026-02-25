#!/usr/bin/env python3
"""
post_now.py — Post all clips from 2.25_publish to TikTok + Instagram
Launches a visible browser. Log in when prompted, then it runs automatically.

Run: /opt/anaconda3/bin/python3 scripts/post_now.py
"""
import os, time
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

PUBLISH_DIR   = Path("/Users/terry/Desktop/crowdlisten_files/crowdlisten_marketing/published/2.25_publish")
INTERVAL_SECS = 3 * 60 * 60
HASHTAGS      = "#ProductManagement #SiliconValley #StartupLife #TechHumor #AI #PMlife #EngineerLife #SaaS #crowdlisten"

CAPTIONS = {
    "01_making_the_world_a_better_place": f"our pitch deck, in 22 seconds 😂 {HASHTAGS}",
    "02_asshole_vacuum":                  f"leadership advice nobody asked for 💀 {HASHTAGS}",
    "02_vendor_says_another_buyer":       f"when the vendor says 'another buyer is interested' 😅 {HASHTAGS}",
    "03_pulled_out_of_nosedive":          f"VC energy after the bridge round closes 🎯 {HASHTAGS}",
    "06_smart_fridge":                    f"when the eng team wants a new $14k tool 💸 {HASHTAGS}",
    "06_stakeholder_no_context":          f"when stakeholders give zero context 🙃 {HASHTAGS}",
    "07_this_guy_fucks":                  f"investors meeting the founding team 😂 {HASHTAGS}",
    "08_less_than_a_cd":                  f"VC explaining ROI to LPs 📉 {HASHTAGS}",
    "09_new_internet":                    f"founder after reading one Paul Graham essay 🚀 {HASHTAGS}",
    "10_36_icos":                         f"me after my crypto strategy 😭 {HASHTAGS}",
    "11_ghost_like_features":             f"new hire on day one at a startup 👻 {HASHTAGS}",
    "12_driverless_car":                  f"when AI takes over your calendar 🤖 {HASHTAGS}",
    "12_need_a_push":                     f"when the release needs just one more push 😤 {HASHTAGS}",
}

SESSION_DIR = Path("/tmp/crowdlisten_browser_session")
SESSION_DIR.mkdir(exist_ok=True)

def wait_for_login(page, url, check_selector, platform):
    page.goto(url, timeout=30000)
    print(f"\n👉 Log into {platform} in the browser window, then come back here.")
    print(f"   Waiting for login", end="", flush=True)
    while True:
        try:
            page.wait_for_selector(check_selector, timeout=5000)
            print(" ✅ Logged in!")
            return
        except:
            print(".", end="", flush=True)

def post_tiktok(page, clip, caption):
    print(f"\n  📤 TikTok: {clip.name}")
    page.goto("https://www.tiktok.com/upload", wait_until="domcontentloaded", timeout=30000)
    time.sleep(4)

    # Upload via file input
    file_input = page.query_selector("input[type='file']")
    if file_input:
        file_input.set_input_files(str(clip))
    else:
        with page.expect_file_chooser() as fc:
            page.click("[class*='upload-btn'], [class*='select-video'], button:has-text('Upload')")
        fc.value.set_files(str(clip))

    print("    Uploading video...", end="", flush=True)
    # Wait for upload progress to disappear
    try:
        page.wait_for_selector("[class*='caption'], div[contenteditable='true']", timeout=60000)
    except:
        time.sleep(20)
    print(" done")

    # Caption
    try:
        caption_el = page.query_selector("div[contenteditable='true'], [class*='caption-input']")
        if caption_el:
            caption_el.click()
            page.keyboard.press("Control+a")
            time.sleep(0.5)
            caption_el.type(caption, delay=20)
    except Exception as e:
        print(f"    ⚠️  Caption error: {e}")

    time.sleep(2)

    # Post button
    try:
        btn = page.query_selector("button:has-text('Post'), button[class*='post-btn']")
        if btn:
            btn.click()
            print("    ✅ TikTok posted!")
            time.sleep(5)
        else:
            print("    ⚠️  Post button not found — check browser")
    except Exception as e:
        print(f"    ❌ {e}")

def post_instagram(page, clip, caption):
    print(f"\n  📤 Instagram: {clip.name}")
    page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    try:
        # New post button
        with page.expect_file_chooser(timeout=10000) as fc:
            create = page.query_selector("svg[aria-label='New post']") or \
                     page.query_selector("[aria-label='New post']")
            if create:
                create.click()
            else:
                page.click("[data-testid='new-post-button']")
        fc.value.set_files(str(clip))
    except Exception as e:
        print(f"    ⚠️  Upload error: {e}")
        return

    print("    Uploading video...", end="", flush=True)
    time.sleep(8)
    print(" done")

    # Click through Next buttons
    for label in ["Next", "Next"]:
        try:
            btn = page.query_selector(f"button:has-text('{label}')")
            if btn:
                btn.click()
                time.sleep(2)
        except:
            pass

    # Caption
    try:
        cap = page.query_selector("textarea[aria-label*='caption'], textarea[placeholder*='Write']")
        if cap:
            cap.fill(caption)
        time.sleep(2)
    except Exception as e:
        print(f"    ⚠️  Caption error: {e}")

    # Share
    try:
        share = page.query_selector("button:has-text('Share')")
        if share:
            share.click()
            print("    ✅ Instagram posted!")
            time.sleep(5)
        else:
            print("    ⚠️  Share button not found — check browser")
    except Exception as e:
        print(f"    ❌ {e}")

def main():
    clips = sorted(PUBLISH_DIR.glob("*.mp4"))
    if not clips:
        print("❌ No clips in publish folder."); return

    print(f"Found {len(clips)} clips:")
    for i, c in enumerate(clips):
        eta = datetime.now() + timedelta(seconds=i * INTERVAL_SECS)
        print(f"  [{i+1:02d}] {c.stem} → posts at {eta.strftime('%H:%M')}")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            str(SESSION_DIR),
            headless=False,
            args=["--start-maximized"],
            no_viewport=True,
        )
        page = browser.new_page()

        # Login checks
        wait_for_login(page, "https://www.tiktok.com/upload",
                       "[class*='upload-btn'], [class*='upload-card']", "TikTok")
        wait_for_login(page, "https://www.instagram.com/",
                       "svg[aria-label='New post'], [aria-label='New post']", "Instagram")

        print(f"\n🚀 Starting to post {len(clips)} clips at 3-hour intervals...")

        for i, clip in enumerate(clips):
            if i > 0:
                next_time = datetime.now() + timedelta(seconds=INTERVAL_SECS)
                print(f"\n⏳ Next post at {next_time.strftime('%H:%M:%S')} — sleeping 3 hours...")
                time.sleep(INTERVAL_SECS)

            caption = CAPTIONS.get(clip.stem, f"{clip.stem.replace('_',' ')} {HASHTAGS}")
            print(f"\n[{i+1}/{len(clips)}] {clip.stem}")

            try: post_tiktok(page, clip, caption)
            except Exception as e: print(f"  TikTok error: {e}")

            try: post_instagram(page, clip, caption)
            except Exception as e: print(f"  IG error: {e}")

        print("\n🎉 All done!")
        browser.close()

if __name__ == "__main__":
    main()
