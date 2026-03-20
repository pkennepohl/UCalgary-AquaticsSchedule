# UCalgary-AquaticsSchedule

A lightweight utility that automatically converts the UCalgary Aquatic Centre pool schedule into an iCalendar (.ics) file for easy calendar integration.

## Features

- **Automatic updates** – Runs 3 times daily (6 AM, 2 PM, 8 PM Calgary time) to catch schedule changes
- **Calendar-ready** – Subscribe directly in Outlook, Google Calendar, Apple Calendar, or any iCal-compatible app
- **Detailed event info** – Each event includes:
  - Pool size (25m or 50m)
  - Swim type (Adult/Youth Lane Swim or Family and Lane Swim)
  - Limited lanes indicator (*)
  - Source and subscription information in event description
- **Error correction** – Handles common data entry errors (AM/PM mistakes) through chronological validation
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
- Explanation of what the asterisk means
- Link to the official UCalgary pool schedule (for reference/changes)
- Calendar subscription URL
- GitHub repository link

## How It Works

1. **Data source** – Reads the official UCalgary Aquatic Centre pool schedule from [active-living.ucalgary.ca](https://active-living.ucalgary.ca/facilities/aquatic-centre/pool-schedule-hours)
2. **Parsing** – Extracts session times, pool sizes, and swim types; automatically corrects common data entry errors
3. **Calendar generation** – Creates an iCalendar file with proper timezone handling (America/Edmonton)
4. **Updates** – GitHub Actions automatically runs the process 3 times daily
5. **Subscription** – Subscribe once via the .ics URL above; updates are delivered automatically

## Update Frequency

- **Schedule checks:** 3 times per day (6 AM, 2 PM, 8 PM Calgary time)
- **Calendar refresh:** Every 8 hours (your calendar app will check for updates)
- **Typical latency:** New schedule changes appear in your calendar within 30 minutes to 8 hours of being posted

## Technical Details

- **Language:** Python 3
- **Dependencies:** requests, beautifulsoup4
- **CI/CD:** GitHub Actions (automated daily updates)
- **Format:** iCalendar (RFC 5545)
- **Timezone:** America/Edmonton (handles daylight saving time automatically)

## Limitations

- Sessions are limited to the 3-week window shown on the UCalgary website
- Wristband or check-in requirements are not reflected in calendar (refer to [UCalgary's page](https://active-living.ucalgary.ca/facilities/aquatic-centre/pool-schedule-hours) for additional rules)
- Historical schedule data is not available

## Feedback & Issues

If you notice errors in the schedule or have suggestions for improvement, please:
1. Check the [official UCalgary schedule](https://active-living.ucalgary.ca/facilities/aquatic-centre/pool-schedule-hours) to confirm the error
2. Open an issue on this GitHub repository

Note: This utility reflects the data as published by UCalgary. For official policy questions or special accommodations, contact UCalgary directly.

## License

This utility is provided as-is for personal use. UCalgary Aquatic Centre schedule data remains the property of the University of Calgary.
