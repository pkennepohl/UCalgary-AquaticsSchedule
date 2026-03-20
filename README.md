# UCalgary-AquaticsSchedule

A lightweight utility that automatically converts the UCalgary Aquatic Centre pool schedule into an iCalendar (.ics) file for easy calendar integration.

## Features

- **Automatic updates** – Runs 3 times daily (6 AM, 2 PM, 8 PM Calgary time) to catch schedule changes
- **Calendar-ready** – Subscribe directly in Outlook, Google Calendar, Apple Calendar, or any iCal-compatible app
- **Detailed event info** – Each event includes:
  - Pool size (25m or 50m)
  - Swim type (Adult/Youth Lane Swim or Family and Lane Swim)
  - Limited lanes indicator (*)
  - **Location** – UCalgary Aquatic Centre with clickable Google Maps link
  - **Dynamic swim type rules** – Rules extracted from UCalgary's website and customized to each session
  - Source and subscription information in event description
- **Error correction** – Handles common data entry errors (AM/PM mistakes) through chronological validation
- **Dynamic rules** – Swim type rules are extracted from UCalgary's website every update, so rule changes are reflected automatically
- **No dependencies** – Subscribe once and receive automatic updates; no manual intervention needed

## Quick Start

### Subscribe to the Calendar

Copy this URL into your calendar application:

```
https://raw.githubusercontent.com/pkennepohl/UCalgary-AquaticsSchedule/main/pool-schedule.ics
```

**Outlook:**
1. Go to **File** → **Open & Export** → **Open Calendar**
2. Paste the URL above
3. Calendar will automatically refresh every 8 hours

**Google Calendar:**
1. Open **Settings**
2. Select **Add calendar** → **Subscribe to calendar**
3. Paste the URL above

**Apple Calendar / Other Apps:**
1. Use **Add Calendar** or **Subscribe**
2. Paste the URL above

## Understanding the Events

### Event Titles

Events follow this format:

```
25m Lane Swim (Adult/Youth)
50m Lane Swim* (Family)
```

- **Pool size** (25m or 50m) indicates the pool configuration
- **Swim type** shows whether it's an Adult/Youth or Family session
- **Asterisk (*)** indicates **limited lanes available**

### Event Descriptions

Each event includes:

```
NOTE: An asterisk (*) indicates limited lanes available.

DETAILS:
Adult/Youth Lane Swim — 25m lane swim opportunity. Pull buoys available. Swim test may be required for deep end.

CALENDAR INFO:
Source: https://active-living.ucalgary.ca/...
Subscribe: https://raw.githubusercontent.com/...
GitHub: https://github.com/...
```

The **DETAILS** section contains swim type information and rules extracted from UCalgary's website. These rules are automatically updated whenever the website changes, so you always have current information.

## How It Works

1. **Data source** – Reads the official UCalgary Aquatic Centre pool schedule from [active-living.ucalgary.ca](https://active-living.ucalgary.ca/facilities/aquatic-centre/pool-schedule-hours)
2. **Parsing** – Extracts session times, pool sizes, and swim types; automatically corrects common data entry errors
3. **Rule extraction** – Extracts swim type rules and guidelines directly from UCalgary's website
4. **Calendar generation** – Creates an iCalendar file with:
   - Proper timezone handling (America/Edmonton)
   - Customized swim type rules for each session (pool-size aware for Adult/Youth sessions)
5. **Updates** – GitHub Actions automatically runs the process 3 times daily
6. **Subscription** – Subscribe once via the .ics URL above; updates are delivered automatically

## Schedule Window

The calendar always shows the **current 3-week rolling schedule** as published by UCalgary. Sessions are removed from your calendar when they expire (no longer listed on UCalgary's website). This keeps your calendar current and prevents accumulation of outdated sessions.

## Update Frequency

- **Schedule checks:** 3 times per day (6 AM, 2 PM, 8 PM Calgary time)
- **Calendar refresh:** Every 8 hours (your calendar app will check for updates)
- **Rules updates:** Rule changes from UCalgary are captured automatically on each check
- **Typical latency:** New schedule changes or rule updates appear in your calendar within 30 minutes to 8 hours of being posted to UCalgary's website

## Technical Details

- **Language:** Python 3
- **Dependencies:** requests, beautifulsoup4
- **CI/CD:** GitHub Actions (automated daily updates)
- **Format:** iCalendar (RFC 5545)
- **Timezone:** America/Edmonton (handles daylight saving time automatically)

## Limitations

- **3-week rolling window** – Only shows the current schedule published by UCalgary. Sessions are removed when they expire. This is not a historical archive.
- **Pool rules only** – Wristband or check-in requirements are not reflected in calendar. Refer to [UCalgary's page](https://active-living.ucalgary.ca/facilities/aquatic-centre/pool-schedule-hours) for additional policies
- **No Inflatable Swim** – Inflatable Swim sessions are not currently offered in the schedule (noted as "not regularly offered" on UCalgary's website)

## Feedback & Issues

If you notice errors in the schedule or have suggestions for improvement, please:
1. Check the [official UCalgary schedule](https://active-living.ucalgary.ca/facilities/aquatic-centre/pool-schedule-hours) to confirm the error
2. Open an issue on this GitHub repository

Note: This utility reflects the data as published by UCalgary. For official policy questions or special accommodations, contact UCalgary directly.

## License

This utility is provided as-is for personal use. UCalgary Aquatic Centre schedule data remains the property of the University of Calgary.
