#!/usr/bin/env python3
"""
X Scheduler - Schedule posts (text + images/videos) to X/Twitter

Usage:
  python "X Scheduler.py" --time "9PM 29-11-2025" [--interval 1h] [--posts-dir ./posts]
  python "X Scheduler.py" --time "21 29-11-2025" --interval 2h

Post Structure:
  Option 1: Numbered folders (RECOMMENDED - any filenames work)
    posts/1/dkjad.jpg, posts/1/keake.txt
    posts/2/video.mp4, posts/2/description.txt
    posts/3/myphoto.png  (media only)
    posts/4/mytext.txt   (text only)
  
  Option 2: Numbered files in posts directory
    posts/1.png, posts/1.txt
    posts/2.jpg, posts/2.txt
    posts/3.mp4  (media only)
    posts/4.txt  (text only)
  
  Custom schedule per post (optional):
    Create a .txt file with just the schedule time:
    posts/1/schedule.txt containing: 10PM 30-11-2025
    OR
    posts/1.txt containing: 10PM 30-11-2025 (if using Option 2)
    
    Format: 
      12hr: XXPM/AM DD-MM-YYYY (e.g., "10PM 30-11-2025", "9:30AM 25-12-2025")
      24hr: HH DD-MM-YYYY or HH:MM DD-MM-YYYY (e.g., "21 30-11-2025", "14:30 25-12-2025")
  
  Supported media: .png, .jpg, .jpeg, .gif, .mp4, .webp

Dependencies:
  pip install selenium webdriver-manager rich

Requirements:
  - Place cookies.json (Twitter cookies) next to this script
  - Default posts directory is "posts" (in same folder as script)
"""
import os
import sys
import time
import json
import argparse
import traceback
import re
from datetime import datetime, timedelta
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# ---------------- CONFIG ----------------
X_COOKIES = "cookies.json"
SCHEDULE_CONFIRM_WAIT = 15.0
UPLOAD_PREVIEW_WAIT = 25.0
POST_BUTTON_WAIT = 20.0
# ----------------------------------------

console = Console()

# ---------------- Utilities ----------------
def parse_interval(s: str):
    """Parse interval string like '1h', '30m', '24h' into timedelta"""
    if not s:
        return timedelta(hours=1)
    s = s.strip().lower()
    m = re.match(r"^(\d+)\s*(h|hr|hrs|hour|hours)$", s)
    if m:
        return timedelta(hours=int(m.group(1)))
    m = re.match(r"^(\d+)\s*(m|min|mins|minute|minutes)$", s)
    if m:
        return timedelta(minutes=int(m.group(1)))
    m = re.match(r"^(\d+)\s*(s|sec|secs|second|seconds)$", s)
    if m:
        return timedelta(seconds=int(m.group(1)))
    try:
        return timedelta(hours=int(s))
    except Exception:
        return timedelta(hours=1)

def parse_schedule_string(s: str):
    """Parse schedule string in multiple formats:
    - 12hr: '9PM 29-11-2025', '9:30PM 29-11-2025'
    - 24hr: '21 29-11-2025', '21:30 29-11-2025', '14:00 29-11-2025'
    """
    if not s or not s.strip():
        raise ValueError("empty schedule string")
    s = s.strip().replace("/", "-")
    patterns = [
        # 12-hour formats with AM/PM
        r"^(?P<h>\d{1,2}):(?P<m>\d{2})\s*(?P<ampm>AM|PM|am|pm)\s+(?P<d>\d{1,2})-(?P<M>\d{1,2})-(?P<y>\d{4})$",
        r"^(?P<h>\d{1,2})\s*(?P<ampm>AM|PM|am|pm)\s+(?P<d>\d{1,2})-(?P<M>\d{1,2})-(?P<y>\d{4})$",
        # 24-hour formats (no AM/PM)
        r"^(?P<h>\d{1,2}):(?P<m>\d{2})\s+(?P<d>\d{1,2})-(?P<M>\d{1,2})-(?P<y>\d{4})$",
        r"^(?P<h>\d{1,2})\s+(?P<d>\d{1,2})-(?P<M>\d{1,2})-(?P<y>\d{4})$",
    ]
    for p in patterns:
        m = re.match(p, s, flags=re.IGNORECASE)
        if not m:
            continue
        gd = m.groupdict()
        h = int(gd.get("h") or 0)
        mnt = int(gd.get("m") or 0)
        ampm = gd.get("ampm")
        d = int(gd.get("d"))
        M = int(gd.get("M"))
        y = int(gd.get("y"))
        
        # Handle 12-hour format with AM/PM
        if ampm:
            ampm = ampm.lower()
            if ampm == "pm" and h < 12:
                h = h + 12
            if ampm == "am" and h == 12:
                h = 0
        # For 24-hour format, validate hour range
        else:
            if h > 23:
                raise ValueError(f"invalid 24-hour format: hour {h} must be 0-23")
        
        if h < 0 or h > 23 or mnt < 0 or mnt > 59:
            raise ValueError("invalid time")
        return datetime(y, M, d, h, mnt)
    raise ValueError(f"unsupported schedule format: {s}")

def find_posts(posts_dir):
    """Find all posts in the directory. Returns list of (number, media_path, text_content, custom_schedule)"""
    posts = []
    posts_path = Path(posts_dir)
    
    if not posts_path.exists():
        console.print(f"[red]Error: Posts directory '{posts_dir}' not found[/red]")
        return posts
    
    # Supported media extensions
    MEDIA_EXTS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4']
    
    # Look for numbered files or folders
    items = {}
    
    # Check for numbered files (1.png, 1.txt, etc.)
    for file in posts_path.iterdir():
        if file.is_file():
            name = file.stem
            ext = file.suffix.lower()
            if name.isdigit():
                num = int(name)
                if num not in items:
                    items[num] = {"media": None, "text": None, "schedule": None}
                if ext in MEDIA_EXTS:
                    items[num]["media"] = str(file)
                elif ext == '.txt':
                    # Check if it's a schedule file (format: "10PM 30-11-2025")
                    content = file.read_text(encoding='utf-8').strip()
                    # Try to parse as schedule first
                    try:
                        parse_schedule_string(content)
                        items[num]["schedule"] = content
                    except Exception:
                        # Not a schedule, treat as regular text
                        items[num]["text"] = content
    
    # Check for numbered folders (any filenames work inside)
    for folder in posts_path.iterdir():
        if folder.is_dir() and folder.name.isdigit():
            num = int(folder.name)
            if num not in items:
                items[num] = {"media": None, "text": None, "schedule": None}
            
            # Look for ANY media, text, and schedule files in folder
            for file in folder.iterdir():
                if not file.is_file():
                    continue
                ext = file.suffix.lower()
                if ext in MEDIA_EXTS and not items[num]["media"]:
                    items[num]["media"] = str(file)
                elif ext == '.txt' and not items[num]["text"] and not items[num]["schedule"]:
                    # Check if it's a schedule file (format: "10PM 30-11-2025")
                    content = file.read_text(encoding='utf-8').strip()
                    # If content is a single line and looks like a schedule, treat as schedule
                    if '\n' not in content and len(content) < 50:
                        try:
                            parse_schedule_string(content)
                            items[num]["schedule"] = content
                            continue
                        except Exception:
                            pass
                    # Otherwise treat as regular text
                    items[num]["text"] = content
    
    # Convert to sorted list
    for num in sorted(items.keys()):
        post = items[num]
        # Accept posts with media only, text only, or both
        if post["media"] or post["text"]:
            posts.append((num, post["media"], post["text"], post["schedule"]))
    
    return posts

# ---------------- Selenium helpers ----------------
def make_driver():
    """Create Chrome WebDriver instance (non-headless, Twitter detects headless mode)"""
    opts = Options()
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--start-maximized")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(60)
    return driver

def load_cookies(driver, base_url, cookie_file):
    """Load cookies from JSON file into browser"""
    if not os.path.exists(cookie_file):
        raise FileNotFoundError(f"Cookie file not found: {cookie_file}")
    
    with open(cookie_file, "r", encoding="utf8") as f:
        cookies = json.load(f)
    
    try:
        driver.get(base_url)
    except Exception:
        driver.get("about:blank")
        driver.get(base_url)
    
    time.sleep(0.6)
    loaded = 0
    
    for c in cookies:
        c2 = dict(c)
        for k in ("sameSite", "_expires", "expires"):
            c2.pop(k, None)
        try:
            driver.add_cookie(c2)
            loaded += 1
        except Exception:
            try:
                minimal = {"name": c.get("name"), "value": c.get("value"), "path": c.get("path", "/")}
                if c.get("domain"):
                    minimal["domain"] = c.get("domain")
                driver.add_cookie(minimal)
                loaded += 1
            except Exception:
                pass
    
    driver.get(base_url)
    time.sleep(0.8)
    return loaded

def wait_for_upload_preview(driver, timeout=UPLOAD_PREVIEW_WAIT):
    """Wait for image upload preview to appear"""
    console.print("  [dim]Waiting for upload preview...[/dim]")
    start = time.time()
    while time.time() - start < timeout:
        try:
            candidates = [
                "//div[contains(@data-testid,'composer')]/descendant::img",
                "//div[contains(@data-testid,'tweetTextarea')]/descendant::img",
                "//section//img[contains(@src,'pbs.twimg.com') or contains(@src,'data:') or contains(@src,'blob:')]",
            ]
            for xp in candidates:
                els = driver.find_elements(By.XPATH, xp)
                if els:
                    for el in els:
                        try:
                            src = el.get_attribute("src") or ""
                            if src and len(src) > 5:
                                console.print("  [green]✓ Upload preview detected[/green]")
                                return True
                        except Exception:
                            pass
        except Exception:
            pass
        time.sleep(0.6)
    
    console.print("  [red]✗ Upload preview timeout[/red]")
    return False

def find_clickable_post_button(driver, timeout=POST_BUTTON_WAIT):
    """Find the clickable Post/Tweet button"""
    xpaths = [
        "//*[contains(@data-testid,'tweetButton')]",
        "//button[normalize-space(.)='Post']",
        "//button[normalize-space(.)='Tweet']",
        "//div[@role='button' and normalize-space(string(.))='Post']",
    ]
    end = time.time() + timeout
    while time.time() < end:
        try:
            for xp in xpaths:
                els = driver.find_elements(By.XPATH, xp) or []
                for cand in reversed(els):
                    try:
                        if not cand.is_displayed():
                            continue
                        disabled = cand.get_attribute("disabled")
                        aria_disabled = cand.get_attribute("aria-disabled")
                        if disabled and disabled.lower() not in ("false", "0", ""):
                            continue
                        if aria_disabled and aria_disabled.lower() not in ("false", "0", ""):
                            continue
                        return cand
                    except Exception:
                        continue
        except Exception:
            pass
        time.sleep(0.35)
    return None

def aggressive_click_element(driver, el):
    """Try multiple methods to click an element"""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.15)
    except Exception:
        pass
    
    try:
        el.click()
        return True
    except Exception:
        pass
    
    try:
        driver.execute_script("arguments[0].click();", el)
        return True
    except Exception:
        pass
    
    try:
        driver.execute_script("""
            const el = arguments[0];
            const ev = new MouseEvent('click', {view: window, bubbles: true, cancelable: true});
            el.dispatchEvent(ev);
        """, el)
        return True
    except Exception:
        return False

def click_final_schedule_button(driver):
    """Click the final Schedule button to confirm"""
    console.print("  [dim]Looking for final Schedule button...[/dim]")
    time.sleep(1.5)
    
    try:
        final_schedule_btn = None
        try:
            final_schedule_btn = driver.find_element(By.XPATH, "//button[normalize-space(.)='Schedule']")
        except Exception:
            matches = driver.find_elements(By.XPATH, "//*[normalize-space(text())='Schedule' and (@role='button' or self::button)]") or []
            if matches:
                final_schedule_btn = matches[-1]
        
        if not final_schedule_btn:
            console.print("  [red]✗ Final Schedule button not found[/red]")
            return False
        
        ok = aggressive_click_element(driver, final_schedule_btn)
        if not ok:
            return False
        
        console.print("  [green]✓ Clicked final Schedule button[/green]")
        time.sleep(2.0)
        
        # Verify scheduling
        start = time.time()
        while time.time() - start < SCHEDULE_CONFIRM_WAIT:
            try:
                matches = driver.find_elements(By.XPATH, "//*[contains(translate(text(),'WILL SEND ON','will send on'),'will send on') or contains(translate(text(),'SCHEDULED','scheduled'),'scheduled')]")
                if matches:
                    console.print("  [green]✓ Schedule confirmed[/green]")
                    return True
            except Exception:
                pass
            time.sleep(0.4)
        
        console.print("  [yellow]⚠ Schedule button clicked but confirmation not detected[/yellow]")
        return True
    except Exception as e:
        console.print(f"  [red]✗ Error clicking final Schedule: {e}[/red]")
        return False

def open_schedule_dialog_and_set(driver, schedule_dt):
    """Open schedule dialog and set date/time"""
    try:
        console.print("  [dim]Opening schedule dialog...[/dim]")
        
        # Find and click Schedule button
        schedule_btn = None
        try:
            schedule_btn = driver.find_element(By.XPATH, "//button[normalize-space(.)='Schedule' or contains(@aria-label,'Schedule')]")
        except Exception:
            els = driver.find_elements(By.XPATH, "//*[contains(translate(text(),'SCHEDULE','schedule'),'schedule')]") or []
            if els:
                schedule_btn = els[-1]
        
        if not schedule_btn:
            console.print("  [red]✗ Schedule button not found[/red]")
            return False
        
        try:
            schedule_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", schedule_btn)
        
        console.print("  [green]✓ Opened schedule dialog[/green]")
        time.sleep(1.5)
        
        # Wait for dialog
        dialog = None
        start = time.time()
        while time.time() - start < 10:
            try:
                ds = driver.find_elements(By.XPATH, "//div[@role='dialog']") or []
                if ds:
                    dialog = ds[-1]
                    break
            except Exception:
                pass
            time.sleep(0.3)
        
        if not dialog:
            console.print("  [red]✗ Schedule dialog not found[/red]")
            return False
        
        time.sleep(1.5)
        
        # Set date/time
        console.print(f"  [dim]Setting schedule to {schedule_dt.strftime('%Y-%m-%d %I:%M %p')}...[/dim]")
        
        month_num = schedule_dt.month
        day_num = schedule_dt.day
        year_num = schedule_dt.year
        hour_24 = schedule_dt.hour
        hour_12 = hour_24 % 12
        hour_12 = 12 if hour_12 == 0 else hour_12
        minute_num = schedule_dt.minute
        ampm = "am" if hour_24 < 12 else "pm"
        
        try:
            selects = dialog.find_elements(By.XPATH, ".//select")
            
            # Set Month (SELECTOR_1)
            try:
                month_sel = dialog.find_element(By.XPATH, ".//select[@id='SELECTOR_1']")
                driver.execute_script("""
                    const sel = arguments[0];
                    sel.value = arguments[1];
                    sel.dispatchEvent(new Event('change', { bubbles: true }));
                """, month_sel, str(month_num))
                time.sleep(0.3)
            except Exception:
                pass
            
            # Set Day (SELECTOR_2)
            try:
                day_sel = dialog.find_element(By.XPATH, ".//select[@id='SELECTOR_2']")
                driver.execute_script("""
                    const sel = arguments[0];
                    sel.value = arguments[1];
                    sel.dispatchEvent(new Event('change', { bubbles: true }));
                """, day_sel, str(day_num))
                time.sleep(0.3)
            except Exception:
                pass
            
            # Set Year (SELECTOR_3)
            try:
                year_sel = dialog.find_element(By.XPATH, ".//select[@id='SELECTOR_3']")
                driver.execute_script("""
                    const sel = arguments[0];
                    sel.value = arguments[1];
                    sel.dispatchEvent(new Event('change', { bubbles: true }));
                """, year_sel, str(year_num))
                time.sleep(0.3)
            except Exception:
                pass
            
            # Set Hour (SELECTOR_4)
            try:
                hour_sel = dialog.find_element(By.XPATH, ".//select[@id='SELECTOR_4']")
                driver.execute_script("""
                    const sel = arguments[0];
                    sel.value = arguments[1];
                    sel.dispatchEvent(new Event('change', { bubbles: true }));
                """, hour_sel, str(hour_12))
                time.sleep(0.3)
            except Exception:
                pass
            
            # Set Minute (SELECTOR_5)
            try:
                minute_sel = dialog.find_element(By.XPATH, ".//select[@id='SELECTOR_5']")
                driver.execute_script("""
                    const sel = arguments[0];
                    sel.value = arguments[1];
                    sel.dispatchEvent(new Event('change', { bubbles: true }));
                """, minute_sel, str(minute_num))
                time.sleep(0.3)
            except Exception:
                pass
            
            # Set AM/PM (SELECTOR_6)
            try:
                ampm_sel = dialog.find_element(By.XPATH, ".//select[@id='SELECTOR_6']")
                driver.execute_script("""
                    const sel = arguments[0];
                    const targetText = arguments[1];
                    for (let i = 0; i < sel.options.length; i++) {
                        if (sel.options[i].text.toUpperCase() === targetText.toUpperCase()) {
                            sel.selectedIndex = i;
                            sel.value = sel.options[i].value;
                            sel.dispatchEvent(new Event('change', { bubbles: true }));
                            break;
                        }
                    }
                """, ampm_sel, ampm)
                time.sleep(0.3)
            except Exception:
                pass
            
        except Exception as e:
            console.print(f"  [red]✗ Error setting date/time: {e}[/red]")
            return False
        
        console.print("  [green]✓ Date/time set[/green]")
        time.sleep(2.0)
        
        # Click Confirm button
        try:
            confirm_btn = dialog.find_element(By.XPATH, ".//button[normalize-space(.)='Confirm' or normalize-space(.)='OK']")
            confirm_btn.click()
            console.print("  [green]✓ Clicked Confirm[/green]")
            time.sleep(2.0)
        except Exception:
            pass
        
        # Click final Schedule button
        return click_final_schedule_button(driver)
        
    except Exception as e:
        console.print(f"  [red]✗ Exception in scheduling: {e}[/red]")
        return False

# ---------------- Main posting function ----------------
def post_to_x(driver, media_path, text_content, schedule_dt):
    """Post media (image/video) and/or text to X with scheduling"""
    try:
        # Open composer
        driver.execute_script("window.open('https://x.com/compose/tweet', '_blank');")
        time.sleep(0.5)
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(1.0)
        
        # Add text if provided
        if text_content:
            try:
                textarea = WebDriverWait(driver, 10).until(
                    lambda d: d.find_element(By.XPATH, "//div[@role='textbox']")
                )
                textarea.send_keys(text_content)
                console.print(f"  [green]✓ Added text ({len(text_content)} chars)[/green]")
                time.sleep(0.5)
            except Exception as e:
                console.print(f"  [yellow]⚠ Could not add text: {e}[/yellow]")
        
        # Upload media if provided
        if media_path:
            try:
                inp = WebDriverWait(driver, 12).until(
                    lambda d: d.find_element(By.CSS_SELECTOR, "input[type='file']")
                )
                inp.send_keys(os.path.abspath(media_path))
                media_type = "video" if Path(media_path).suffix.lower() == '.mp4' else "image"
                console.print(f"  [green]✓ Uploaded {media_type}: {Path(media_path).name}[/green]")
                
                upload_ok = wait_for_upload_preview(driver, timeout=UPLOAD_PREVIEW_WAIT)
                if not upload_ok:
                    console.print("  [red]✗ Upload preview timeout[/red]")
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    return False
                
                time.sleep(3.0)
            except Exception as e:
                console.print(f"  [red]✗ Upload error: {e}[/red]")
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                return False
        
        # Schedule the post
        console.print(f"  [cyan]Scheduling for {schedule_dt.strftime('%Y-%m-%d %I:%M %p')}[/cyan]")
        ok = open_schedule_dialog_and_set(driver, schedule_dt)
        
        if ok:
            console.print("  [bold green]✓ Post scheduled successfully![/bold green]")
        else:
            console.print("  [bold red]✗ Scheduling failed[/bold red]")
        
        # Close tab
        try:
            driver.close()
            if driver.window_handles:
                driver.switch_to.window(driver.window_handles[0])
        except Exception:
            pass
        
        return ok
        
    except Exception as e:
        console.print(f"  [red]✗ Exception: {e}[/red]")
        try:
            driver.close()
            if driver.window_handles:
                driver.switch_to.window(driver.window_handles[0])
        except Exception:
            pass
        return False

# ---------------- Main ----------------
def main():
    parser = argparse.ArgumentParser(description="Schedule posts to X/Twitter")
    parser.add_argument("--posts-dir", default="posts", help="Directory containing posts (default: posts)")
    parser.add_argument("--time", required=True, help='First schedule time (12hr: "9PM 29-11-2025" or 24hr: "21 29-11-2025")')
    parser.add_argument("--interval", default="1h", help='Interval between posts: "1h", "30m", "24h" (default: 1h)')
    args = parser.parse_args()
    
    try:
        # Parse schedule settings
        first_schedule = parse_schedule_string(args.time)
        interval = parse_interval(args.interval)
        
        console.print(Panel.fit(
            f"[bold cyan]X Scheduler[/bold cyan]\n\n"
            f"Posts directory: {args.posts_dir}\n"
            f"First post: {first_schedule.strftime('%Y-%m-%d %I:%M %p')}\n"
            f"Interval: {interval}",
            border_style="cyan"
        ))
        
        # Find posts
        posts = find_posts(args.posts_dir)
        if not posts:
            console.print(f"[red]No posts found in '{args.posts_dir}'[/red]")
            console.print("\n[yellow]Expected structure:[/yellow]")
            console.print("  Option 1 (RECOMMENDED): posts/1/dkjad.jpg + posts/1/keake.txt")
            console.print("  Option 2: posts/1.png + posts/1.txt")
            console.print("  Custom schedule: posts/1/schedule.txt containing '10PM 30-11-2025'")
            console.print("\n[dim]Supported: .png .jpg .jpeg .gif .mp4 .webp + .txt (optional)[/dim]")
            return
        
        console.print(f"\n[green]Found {len(posts)} post(s)[/green]")
        for num, media, txt, custom_schedule in posts:
            media_info = Path(media).name if media else "no media"
            txt_info = f"{len(txt)} chars" if txt else "no text"
            schedule_info = f" [custom: {custom_schedule}]" if custom_schedule else ""
            console.print(f"  {num}. {media_info} + {txt_info}{schedule_info}")
        
        # Initialize browser
        console.print("\n[cyan]Initializing browser...[/cyan]")
        driver = make_driver()
        
        # Load cookies
        console.print("[cyan]Loading X cookies...[/cyan]")
        loaded = load_cookies(driver, "https://x.com", X_COOKIES)
        if loaded == 0:
            console.print("[red]No cookies loaded! Make sure cookies.json exists.[/red]")
            driver.quit()
            return
        console.print(f"[green]✓ Loaded {loaded} cookies[/green]")
        
        # Schedule posts
        current_schedule = first_schedule
        success_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Scheduling posts...", total=len(posts))
            
            for num, media, txt, custom_schedule in posts:
                console.print(f"\n[bold cyan]Post #{num}[/bold cyan]")
                
                # Use custom schedule if provided, otherwise use interval-based schedule
                if custom_schedule:
                    try:
                        post_schedule = parse_schedule_string(custom_schedule)
                        console.print(f"  [yellow]Using custom schedule: {post_schedule.strftime('%Y-%m-%d %I:%M %p')}[/yellow]")
                    except Exception as e:
                        console.print(f"  [red]Invalid custom schedule '{custom_schedule}': {e}[/red]")
                        console.print(f"  [yellow]Falling back to interval schedule[/yellow]")
                        post_schedule = current_schedule
                else:
                    post_schedule = current_schedule
                
                ok = post_to_x(driver, media, txt, post_schedule)
                if ok:
                    success_count += 1
                
                # Only increment interval schedule if no custom schedule was used
                if not custom_schedule:
                    current_schedule += interval
                
                progress.update(task, advance=1)
                
                # Small delay between posts
                if num < posts[-1][0]:
                    time.sleep(2)
        
        # Cleanup
        driver.quit()
        
        console.print(f"\n[bold green]✓ Completed: {success_count}/{len(posts)} posts scheduled successfully[/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        console.print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
