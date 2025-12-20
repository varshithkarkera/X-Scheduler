# X Scheduler

A simple Python script to schedule posts (text + images/videos) to X/Twitter.

## What is this?

X Scheduler automates scheduling posts to X/Twitter. Instead of manually scheduling each post through the X interface, you can:

1. Put your images/videos and captions in numbered folders
2. Run the script with a start time and interval
3. Let it automatically schedule all your posts

Perfect for content creators, social media managers, or anyone who wants to batch-schedule their X posts.

## Quick Start

```bash
# 1. Install dependencies
pip install selenium webdriver-manager rich

# 2. Create your posts folder
mkdir posts
mkdir posts/1
# Add your image: posts/1/photo.jpg
# Add your caption: posts/1/caption.txt

# 3. Export your X/Twitter cookies to cookies.json

# 4. Run the scheduler
python "X Scheduler.py" --time "9PM 29-11-2025" --interval 1h
```

That's it! The script will open Chrome, log into X using your cookies, and schedule all your posts.

## Features

- 📅 Schedule posts with custom times or intervals
- 🖼️ Support for images, videos, and GIFs
- 📝 Text-only or media-only posts
- ⏰ Both 12-hour and 24-hour time formats
- 🎯 Per-post custom scheduling
- 🔄 Automatic interval-based scheduling

## Installation

### Requirements

- Python 3.7+
- Chrome browser installed

### Install Dependencies

```bash
pip install selenium webdriver-manager rich
```

### Setup Cookies

1. Export your X/Twitter cookies to a JSON file
2. Save it as `cookies.json` in the same folder as the script

## Usage

### Basic Usage

```bash
python "X Scheduler.py" --time "9PM 29-11-2025"
```

This will:
- Look for posts in the `posts/` folder (default)
- Start scheduling from 9 PM on November 29, 2025
- Use 1-hour intervals between posts (default)

### Custom Options

```bash
# Custom posts directory
python "X Scheduler.py" --time "9PM 29-11-2025" --posts-dir ./my-posts

# Custom interval (30 minutes)
python "X Scheduler.py" --time "9PM 29-11-2025" --interval 30m

# 24-hour format
python "X Scheduler.py" --time "21 29-11-2025" --interval 2h
```

### Command-Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--time` | Yes | - | First post schedule time |
| `--posts-dir` | No | `posts` | Directory containing posts |
| `--interval` | No | `1h` | Interval between posts |

### Time Format

**12-hour format (with AM/PM):**
- `9PM 29-11-2025`
- `9:30PM 29-11-2025`
- `11AM 25-12-2025`
- `11:45AM 25-12-2025`

**24-hour format:**
- `21 29-11-2025` (9 PM)
- `21:30 29-11-2025` (9:30 PM)
- `14 25-12-2025` (2 PM)
- `14:30 25-12-2025` (2:30 PM)

### Interval Format

- `1h`, `2h`, `24h` - Hours
- `30m`, `45m`, `90m` - Minutes
- `30s`, `60s` - Seconds

## Post Structure

### Option 1: Numbered Folders (RECOMMENDED)

Create numbered folders with any filenames inside:

```
posts/
  1/
    dkjad.jpg
    keake.txt
  2/
    video.mp4
    description.txt
  3/
    myphoto.png
  4/
    mytext.txt
```

### Option 2: Numbered Files

Use numbered files directly in the posts directory:

```
posts/
  1.png
  1.txt
  2.jpg
  2.txt
  3.mp4
  4.txt
```

### Supported Media Types

- Images: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`
- Videos: `.mp4`
- Text: `.txt` (optional)

### Media-Only or Text-Only Posts

You can create posts with just media or just text:

```
posts/
  1/
    photo.jpg       (media only)
  2/
    tweet.txt       (text only)
  3/
    video.mp4
    caption.txt     (both)
```

## Custom Scheduling

Override the interval-based schedule for specific posts by adding a schedule file.

### Option 1 (Folders)

Create a `.txt` file with 't', 'time', or 'schedule' in the name:

```
posts/
  1/
    photo.jpg
    caption.txt
    t.txt           <- Contains: 10PM 30-11-2025
```

Or:

```
posts/
  1/
    photo.jpg
    caption.txt
    timet.txt       <- Contains: 10PM 30-11-2025
```

Or:

```
posts/
  1/
    photo.jpg
    caption.txt
    schedule.txt    <- Contains: 10PM 30-11-2025
```

### Option 2 (Flat Files)

Use the `Xt.txt` naming convention where X is the post number:

```
posts/
  1.png
  1.txt             <- "Check out this photo!" (caption)
  1t.txt            <- "10PM 30-11-2025" (schedule)
  2.jpg
  2.txt             <- "Another great post!" (caption)
  2t.txt            <- "11PM 30-11-2025" (schedule)
```

**Key points:**
- `1.txt` = post caption/text
- `1t.txt` = schedule time (the 't' stands for time)
- You can have BOTH caption and schedule for the same post!

### Custom Schedule Format

Same as the `--time` argument:

**12-hour:**
```
10PM 30-11-2025
9:30AM 25-12-2025
```

**24-hour:**
```
21 30-11-2025
14:30 25-12-2025
```

## Examples

### Example 1: Simple Image Posts

```
posts/
  1.jpg
  2.jpg
  3.jpg
```

```bash
python "X Scheduler.py" --time "9AM 01-01-2026" --interval 2h
```

Posts 3 images at 9 AM, 11 AM, and 1 PM on January 1, 2026.

### Example 2: Images with Captions

```
posts/
  1/
    sunset.jpg
    caption.txt     <- "Beautiful sunset today! 🌅"
  2/
    coffee.jpg
    caption.txt     <- "Morning coffee ☕"
```

```bash
python "X Scheduler.py" --time "6PM 20-12-2025" --interval 24h
```

Posts daily at 6 PM starting December 20, 2025.

### Example 3: Mixed Content with Custom Schedules

```
posts/
  1/
    announcement.jpg
    text.txt        <- "Big news coming!"
    t.txt           <- "9AM 25-12-2025"
  2/
    video.mp4
    text.txt        <- "Check out this video!"
    t.txt           <- "12PM 25-12-2025"
  3/
    photo.jpg
    text.txt        <- "Happy holidays!"
    t.txt           <- "6PM 25-12-2025"
```

Or using flat files:

```
posts/
  1.jpg
  1.txt             <- "Big news coming!"
  1t.txt            <- "9AM 25-12-2025"
  2.mp4
  2.txt             <- "Check out this video!"
  2t.txt            <- "12PM 25-12-2025"
  3.jpg
  3.txt             <- "Happy holidays!"
  3t.txt            <- "6PM 25-12-2025"
```

```bash
python "X Scheduler.py" --time "9AM 25-12-2025"
```

Posts at specific times on Christmas Day (ignores the `--interval` for posts with custom schedules).

### Example 4: Text-Only Thread

```
posts/
  1.txt             <- "Thread 1/5: Let me tell you about..."
  2.txt             <- "Thread 2/5: First, we need to..."
  3.txt             <- "Thread 3/5: Then, we can..."
  4.txt             <- "Thread 4/5: After that..."
  5.txt             <- "Thread 5/5: Finally..."
```

```bash
python "X Scheduler.py" --time "10AM 01-01-2026" --interval 5m
```

Posts a thread with 5-minute intervals between tweets.

## Important Notes

### Browser Behavior

- The script runs Chrome in **normal mode** (not headless)
- This is because X/Twitter detects and blocks headless browsers
- You'll see the browser window open and perform actions
- Don't close the browser window while the script is running

### Cookies

- Make sure your `cookies.json` file is up to date
- If posts fail, try exporting fresh cookies from your browser
- The script will load cookies automatically on startup

### Error Handling

- If a post fails, the script continues with the next one
- Check the console output for detailed error messages
- Failed posts won't be retried automatically

### No posts found

- Check that your posts directory exists
- Verify files are numbered correctly (1, 2, 3, etc.)
- Make sure files have supported extensions

### No cookies loaded

- Ensure `cookies.json` exists in the same folder as the script
- Export fresh cookies from your browser
- Check the JSON format is valid

### Scheduling failed

- Verify your schedule time is in the future
- Check the time format is correct
- Make sure you're logged into X/Twitter (cookies are valid)

### Browser closes immediately

- Don't close the browser window manually
- Let the script complete all posts
- Check for error messages in the console

## License

MIT License - Feel free to use and modify!

## Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## Disclaimer

This tool is for educational purposes. Use responsibly and follow X/Twitter's Terms of Service and automation rules.

