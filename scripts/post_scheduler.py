#!/usr/bin/env python3
"""
post_scheduler.py — Auto-post clips to TikTok and Instagram
Connects to the running Chrome instance via CDP (port 18800).
Posts each clip at 3-hour intervals.

Usage:
    python3 scripts/post_scheduler.py --platform tiktok
    python3 scripts/post_scheduler.py --platform instagram
    python3 scripts/post_scheduler.py --platform both
"""

import os, time, argparse
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

# ── Config ────────────────────────────────────────────────────────────────────
CDP_URL       = "http://127.0.0.1:18800"
PUBLISH_DIR   = Path("/Users/terry/Desktop/crowdlisten_files/crowdlisten_marketing/published/2.25_publish")
INTERVAL_SECS = 3 * 60 * 60   # 3 hours

HASHTAGS = "#ProductManagement #SiliconValley #StartupLife #TechHumor #AI #PMlife #EngineerLife #SaaS #crowdlisten"

# ── Captions per clip ─────────────────────────────────────────────────────────
CAPTIONS = {
    "01_making_the_world_a_better_place": f"our pitch deck, in 22 seconds 😂 {HASHTAGS}",
    "02_asshole_vacuum":                  f"leadership advice nobody asked for 💀 {HASHTAGS}",
    "02_vendor_says_another_buyer":       f"when the vendor says 'another buyer is interested' 😅 {HASHTAGS}",
    "03_pulled_out_of_nosedive":          f"VC energy after the bridge round closes 🎯 {HASHTAGS}",
    "06_smart_fridge":                    f"when the eng team wants a new $14k tool 💸 {HASHTAGS}",
    "06_stakeholder_no_context":          f"when stakeholders give zero context 🙃 {HASHTAGS}",
    "07_this_guy_fucks":                  f"investors meeting the founding team for the first time 😂 {HASHTAGS}",
    "08_less_than_a_cd":                  f"VC explaining ROI to LPs 📉 {HASHTAGS}",
    "09_new_internet":                    f"founder after reading one Paul Graham essay 🚀 {HASHTAGS}",
    "10_36_icos":                         f"me after my crypto strategy 😭 {HASHTAGS}",
    "11_ghost_like_features":             f"new hire on day one at a startup 👻 {HASHTAGS}",
    "12_driverless_car":                  f"when AI takes over your calendar 🤖 {HASHTAGS}",
    "12_need_a_push":                     f"when the release needs just one more push 😤 {HASHTAGS}",
}

# ─────────────────────────────────────────────────────────────────────────────

def get_clips():
    clips = sorted(PUBLISH_DIR.glob("*.mp4"))
    return clips


def post_to_tiktok(page, video_path, caption):
    print(f"  → TikTok: {video_path.name}")
    page.goto("https://www.tiktok.com/upload", wait_until="networkidle", timeout=30000)
    time.sleep(3)

    # Upload file
    with page.expect_file_chooser() as fc_info:
        page.click("input[type='file']") if page.query_selector("input[type='file']") else page.click("[class*='upload']")
    file_chooser = fc_info.value
    file_chooser.set_files(str(video_path))
    print(f"    Uploading...")
    time.sleep(10)

    # Fill caption
    caption_box = page.query_selector("[class*='caption'], [placeholder*='caption'], [contenteditable='true']")
    if caption_box:
        caption_box.click()
        page.keyboard.press("Control+A")
        page.keyboard.type(caption)

    time.sleep(3)

    # Post
    post_btn = page.query_selector("[class*='post-button'], button:has-text('Post'), button:has-text('Upload')")
    if post_btn:
        post_btn.click()
        print(f"    ✅ Posted to TikTok!")
        time.sleep(5)
    else:
        print(f"    ⚠️  Couldn't find Post button — check browser window")


def post_to_instagram(page, video_path, caption):
    print(f"  → Instagram: {video_path.name}")
    page.goto("https://www.instagram.com/", wait_until="networkidle", timeout=30000)
    time.sleep(3)

    # Click create post button
    create_btn = page.query_selector("[aria-label='New post'], svg[aria-label='New post']")
    if create_btn:
        create_btn.click()
    else:
        # Try the + icon
        page.click("a[href='/create/select/']") if page.query_selector("a[href='/create/select/']") else None
    time.sleep(2)

    # Upload file
    with page.expect_file_chooser() as fc_info:
        select_btn = page.query_selector("button:has-text('Select from computer'), input[type='file']")
        if select_btn:
            select_btn.click()
        else:
            page.click("button:has-text('Select')")
    file_chooser = fc_info.value
    file_chooser.set_files(str(video_path))
    print(f"    Uploading...")
    time.sleep(8)

    # Next → Next → Caption
    for _ in range(2):
        next_btn = page.query_selector("button:has-text('Next'), div:has-text('Next')")
        if next_btn:
            next_btn.click()
            time.sleep(2)

    # Fill caption
    caption_area = page.query_selector("textarea[aria-label*='caption'], textarea[placeholder*='caption']")
    if caption_area:
        caption_area.click()
        caption_area.fill(caption)
    time.sleep(2)

    # Share
    share_btn = page.query_selector("button:has-text('Share')")
    if share_btn:
        share_btn.click()
        print(f"    ✅ Posted to Instagram!")
        time.sleep(5)
    else:
        print(f"    ⚠️  Couldn't find Share button — check browser window")


def main(platform):
    clips = get_clips()
    if not clips:
        print("❌ No clips found in publish folder.")
        return

    print(f"\n📋 {len(clips)} clips to post")
    print(f"⏱  Interval: 3 hours between posts")
    print(f"🚀 Platform: {platform}\n")

    now = datetime.now()
    for i, clip in enumerate(clips):
        scheduled = now + timedelta(seconds=i * INTERVAL_SECS)
        name = clip.stem
        caption = CAPTIONS.get(name, f"{name.replace('_',' ')} {HASHTAGS}")
        print(f"[{i+1:02d}] {name}")
        print(f"     Scheduled: {scheduled.strftime('%Y-%m-%d %H:%M')}")

    print("\nStarting in 5 seconds... (Ctrl+C to abort)")
    time.sleep(5)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        for i, clip in enumerate(clips):
            name = clip.stem
            caption = CAPTIONS.get(name, f"{name.replace('_',' ')} {HASHTAGS}")

            if i > 0:
                wait_until = datetime.now() + timedelta(seconds=INTERVAL_SECS)
                print(f"\n⏳ Waiting until {wait_until.strftime('%H:%M')} for next post...")
                time.sleep(INTERVAL_SECS)

            print(f"\n[{i+1}/{len(clips)}] Posting: {name}")

            if platform in ("tiktok", "both"):
                try:
                    post_to_tiktok(page, clip, caption)
                except Exception as e:
                    print(f"    ❌ TikTok error: {e}")

            if platform in ("instagram", "both"):
                try:
                    post_to_instagram(page, clip, caption)
                except Exception as e:
                    print(f"    ❌ Instagram error: {e}")

        print("\n✅ All clips posted!")
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["tiktok", "instagram", "both"], default="both")
    args = parser.parse_args()
    main(args.platform)
