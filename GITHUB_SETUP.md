# GitHub Actions Pool Schedule Setup

## What This Does

- **Checks daily** for schedule changes (or manually trigger anytime)
- **Generates an iCal file** (`pool-schedule.ics`) with all pool sessions as calendar events
- **Only updates on changes** – Outlook only refreshes when the schedule actually changes
- **Fully automated** – once set up, requires zero maintenance

## Setup Steps

### 1. Create a GitHub Repository

1. Go to **github.com** and create a new public repository (e.g., `pool-schedule`)
2. Clone it to your computer:
   ```bash
   git clone https://github.com/YOUR_USERNAME/pool-schedule
   cd pool-schedule
   ```

### 2. Add the Files

Create these two files in your repo:

**`pool_schedule_ical.py`** – (copy the Python script from this guide)

**`.github/workflows/pool-schedule.yml`** – (copy the workflow file from this guide)

Your repo structure should look like:
```
pool-schedule/
├── pool_schedule_ical.py
└── .github/
    └── workflows/
        └── pool-schedule.yml
```

### 3. Commit and Push

```bash
git add .
git commit -m "Initial setup: pool schedule automation"
git push origin main
```

### 4. Enable GitHub Actions

- Go to your repo on GitHub
- Click **Actions** tab
- Click "I understand my workflows, go ahead and enable them"

### 5. Test the Workflow

- In **Actions** tab, find "Update Pool Schedule"
- Click it
- Click **Run workflow** → **Run workflow** (manual trigger)
- Wait ~30 seconds, you should see it complete
- Check your repo for the `pool-schedule.ics` file

### 6. Get the Raw File URL

Once the workflow completes and creates `pool-schedule.ics`:

1. Click on `pool-schedule.ics` in your repo
2. Click **Raw** button
3. Copy the URL (should be something like):
   ```
   https://raw.githubusercontent.com/YOUR_USERNAME/pool-schedule/main/pool-schedule.ics
   ```

### 7. Subscribe in Outlook (Desktop or Web)

**Web (Outlook.com):**
1. Go to **outlook.com**
2. Left sidebar → **Add calendar** → **Subscribe from web**
3. Paste the raw `.ics` URL
4. Name it "Pool Schedule"
5. Click **Import**

**Desktop (Outlook app):**
1. File → Open & Export → Import iCalendar
2. Paste the raw URL
3. Choose which calendar to add to
4. Done

**Mobile (Outlook app):**
1. Tap **Calendars**
2. Tap **Add calendar**
3. Tap **Subscribe from web**
4. Paste the raw URL
5. Done

### 8. Verify the Subscription

- You should see pool sessions appear in your Outlook calendar
- Sessions are color-coded by pool (you can customize this in Outlook)
- Sessions marked "(Limited Lanes)" appear in the event title

## How the Automation Works

**Daily Schedule:**
- Workflow runs every day at **6 AM Calgary time** (automatically adjusted for daylight saving)

**Change Detection:**
- Fetches current schedule
- Compares new `.ics` to previous version
- Only commits if different
- Outlook only refreshes when the file changes (avoids unnecessary syncs)

**Manual Trigger:**
- You can also manually run it anytime:
  - Go to **Actions** → **Update Pool Schedule** → **Run workflow**
  - Useful if you want to check for changes immediately

## Customization

### Change Check Frequency

Edit `.github/workflows/pool-schedule.yml` cron line:

```yaml
# Run every 6 hours
- cron: '0 */6 * * *'

# Run every 3 days
- cron: '0 0 */3 * *'

# Run twice daily (6 AM and 2 PM Calgary time)
- cron: '0 13,21 * * *'
```

[Cron expression reference](https://crontab.guru/)

### Change the Timezone

The current cron is set for Calgary time (UTC-7/-6). To adjust:
- UTC: `0 13 * * *` (already set)
- Eastern: `0 11 * * *` (UTC-5/-4)
- Pacific: `0 15 * * *` (UTC-8/-7)

### Customize Event Details

Edit `pool_schedule_ical.py` to change event colors, descriptions, or locations in the generated `.ics` file.

## Troubleshooting

### Schedule not updating in Outlook?
- Outlook refreshes subscriptions daily by default
- Force a refresh: 
  - **Web**: Reload the page
  - **Desktop**: File → Options → Advanced → Calendar → Sync interval
  - **Mobile**: Force close and reopen the app

### Missing sessions in calendar?
- Check the `pool-schedule.ics` file in your GitHub repo – are sessions there?
- If not, the workflow failed. Check **Actions** tab for error logs.

### Want to see all past workflows?
- **Actions** tab → **Update Pool Schedule** → Shows run history
- Click any run to see logs

## Maintenance

That's it! The workflow runs automatically. You never need to do anything again unless:

- You want to change the schedule time (edit the cron)
- You want to customize event details (edit the Python script)
- You want to stop the automation (disable the workflow)

## File Contents Reference

**`pool-schedule.ics`** (auto-generated, ~10-20 KB)
- Contains all pool sessions as iCal events
- Updated daily if schedule changes
- Subscribed to by Outlook

**`.github/workflows/pool-schedule.yml`**
- Runs the Python script daily
- Checks for changes
- Commits only if changed

**`pool_schedule_ical.py`**
- Fetches UCalgary schedule
- Parses HTML
- Generates iCal format
