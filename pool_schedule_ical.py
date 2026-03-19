#!/usr/bin/env python3
"""
UCalgary Pool Schedule to iCal (.ics) Exporter - Version 2

Completely rewritten parser to handle all schedule types and edge cases.
Fetches the pool schedule and generates an iCalendar file for Outlook subscription.
Designed to run via GitHub Actions daily (only commits if schedule changes).
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

def fetch_schedule():
    """Fetch the schedule from UCalgary website."""
    url = 'https://active-living.ucalgary.ca/facilities/aquatic-centre/pool-schedule-hours'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching schedule: {e}")
        return None

def parse_time_range(time_str):
    """
    Parse a time range string like '7:30 - 9:30 a.m.' or '11 a.m. - 4 p.m.'
    Returns tuple: (start_hour, start_min, end_hour, end_min)
    """
    # Remove extra spaces
    time_str = ' '.join(time_str.split())
    
    # Match times with optional colons and minutes, with am/pm
    # Pattern: HH:MM or H or HH followed by optional :MM, then am/pm
    pattern = r'(\d{1,2})(?::(\d{2}))?\s*(?:am|a\.m|a\.m\.|pm|p\.m|p\.m\.)\s*-\s*(\d{1,2})(?::(\d{2}))?\s*(?:am|a\.m|a\.m\.|pm|p\.m|p\.m\.)'
    
    match = re.search(pattern, time_str, re.IGNORECASE)
    if not match:
        return None
    
    start_hour = int(match.group(1))
    start_min = int(match.group(2) or 0)
    end_hour = int(match.group(3))
    end_min = int(match.group(4) or 0)
    
    # Determine AM/PM by looking at the times and which period is mentioned
    # Find where "am" or "pm" appears
    time_lower = time_str.lower()
    
    # Check if there's "a.m" before the dash and "p.m" after
    before_dash = time_str[:time_str.index('-')]
    after_dash = time_str[time_str.index('-'):]
    
    before_am = bool(re.search(r'am|a\.m', before_dash, re.IGNORECASE))
    before_pm = bool(re.search(r'pm|p\.m', before_dash, re.IGNORECASE))
    after_am = bool(re.search(r'am|a\.m', after_dash, re.IGNORECASE))
    after_pm = bool(re.search(r'pm|p\.m', after_dash, re.IGNORECASE))
    
    # Case 1: Only one am/pm indicator - apply to both times
    if before_am and not before_pm and not after_pm:
        # Both are AM
        pass
    elif before_pm and not before_am and not after_am:
        # Both are PM
        if start_hour != 12:
            start_hour += 12
        if end_hour != 12:
            end_hour += 12
    # Case 2: Different am/pm for start and end
    elif before_am and after_pm:
        # Start is AM, end is PM
        if end_hour != 12:
            end_hour += 12
    elif before_pm and after_am:
        # Start is PM, end is AM (unusual, probably next day)
        if start_hour != 12:
            start_hour += 12
        # end_hour stays as is (it's AM next day)
    # Case 3: No clear AM/PM found for one of them
    else:
        # Find the last AM/PM in the entire string
        if 'pm' in time_lower or 'p.m' in time_lower:
            if start_hour != 12:
                start_hour += 12
            if end_hour != 12:
                end_hour += 12
        # else both stay as is (AM)
    
    return (start_hour, start_min, end_hour, end_min)

def parse_schedule(html):
    """Parse the HTML and extract ALL swimming sessions from all weeks."""
    soup = BeautifulSoup(html, 'html.parser')
    
    sessions = []
    current_year = datetime.now().year
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    
    # Find all text nodes and look for day/date patterns
    # This is more robust than relying on specific HTML structure
    
    full_text = soup.get_text()
    
    # Split by "Adult/Youth Lane Swim" to find all weeks
    sections = full_text.split('Adult/Youth Lane Swim')
    
    for section_idx, section in enumerate(sections[1:]):  # Skip first element (before any section)
        # This section contains one week of Adult/Youth Lane Swim data
        
        # Find all day/date patterns in this section
        # Pattern: "Day, Month Date" (e.g., "Monday, March 16")
        day_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[,\s]+(\w+)\s+(\d{1,2})'
        
        day_matches = list(re.finditer(day_pattern, section, re.IGNORECASE))
        
        for day_idx, day_match in enumerate(day_matches):
            day_name = day_match.group(1).strip()
            month_name = day_match.group(2).strip()
            day_num = int(day_match.group(3))
            
            month = month_map.get(month_name, 1)
            year = current_year
            if month < datetime.now().month:
                year += 1
            
            # Extract content from this day until the next day or end of section
            start_pos = day_match.end()
            if day_idx + 1 < len(day_matches):
                end_pos = day_matches[day_idx + 1].start()
            else:
                # Check if there's a "Family and Lane Swim" section after this
                family_pos = section.find('Family and Lane Swim', start_pos)
                if family_pos != -1:
                    end_pos = family_pos
                else:
                    end_pos = len(section)
            
            day_content = section[start_pos:end_pos]
            
            # Find all time ranges and pool info in this day
            # Pattern: "Time range PoolSize optional-LimitedLanes"
            time_pool_pattern = r'(\d{1,2}(?::\d{2})?\s*(?:am|a\.m|a\.m\.|pm|p\.m|p\.m\.)\s*-\s*\d{1,2}(?::\d{2})?\s*(?:am|a\.m|a\.m\.|pm|p\.m|p\.m\.))\s+(25m|50m)\s*(\*?Limited Lanes)?'
            
            time_matches = re.finditer(time_pool_pattern, day_content, re.IGNORECASE)
            
            for time_match in time_matches:
                time_str = time_match.group(1).strip()
                pool = time_match.group(2).strip()
                is_limited = bool(time_match.group(3))
                
                # Parse the time range
                time_result = parse_time_range(time_str)
                if not time_result:
                    continue
                
                start_hour, start_min, end_hour, end_min = time_result
                
                try:
                    start_dt = datetime(year, month, day_num, start_hour, start_min)
                    end_dt = datetime(year, month, day_num, end_hour, end_min)
                    
                    # Validate that end > start (not wrapping to next day)
                    if end_dt <= start_dt:
                        continue
                    
                    session = {
                        'day': day_name,
                        'date_str': f"{month:02d}/{day_num:02d}/{year}",
                        'start_dt': start_dt,
                        'end_dt': end_dt,
                        'time_str': time_str,
                        'pool': pool,
                        'limited': is_limited,
                        'type': 'Adult/Youth Lane Swim'
                    }
                    
                    sessions.append(session)
                except (ValueError, TypeError):
                    continue
    
    # Now find "Family and Lane Swim" sessions
    family_sections = full_text.split('Family and Lane Swim')
    
    for section_idx, section in enumerate(family_sections[1:]):  # Skip first element
        # Find all day/date patterns
        day_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[,\s]+(\w+)\s+(\d{1,2})'
        
        day_matches = list(re.finditer(day_pattern, section, re.IGNORECASE))
        
        for day_idx, day_match in enumerate(day_matches):
            day_name = day_match.group(1).strip()
            month_name = day_match.group(2).strip()
            day_num = int(day_match.group(3))
            
            month = month_map.get(month_name, 1)
            year = current_year
            if month < datetime.now().month:
                year += 1
            
            # Extract content from this day
            start_pos = day_match.end()
            if day_idx + 1 < len(day_matches):
                end_pos = day_matches[day_idx + 1].start()
            else:
                end_pos = len(section)
            
            day_content = section[start_pos:end_pos]
            
            # Find all time ranges and pool info
            time_pool_pattern = r'(\d{1,2}(?::\d{2})?\s*(?:am|a\.m|a\.m\.|pm|p\.m|p\.m\.)\s*-\s*\d{1,2}(?::\d{2})?\s*(?:am|a\.m|a\.m\.|pm|p\.m|p\.m\.))\s+(25m|50m)\s*(\*?Limited Lanes)?'
            
            time_matches = re.finditer(time_pool_pattern, day_content, re.IGNORECASE)
            
            for time_match in time_matches:
                time_str = time_match.group(1).strip()
                pool = time_match.group(2).strip()
                is_limited = bool(time_match.group(3))
                
                # Parse the time range
                time_result = parse_time_range(time_str)
                if not time_result:
                    continue
                
                start_hour, start_min, end_hour, end_min = time_result
                
                try:
                    start_dt = datetime(year, month, day_num, start_hour, start_min)
                    end_dt = datetime(year, month, day_num, end_hour, end_min)
                    
                    # Validate that end > start
                    if end_dt <= start_dt:
                        continue
                    
                    session = {
                        'day': day_name,
                        'date_str': f"{month:02d}/{day_num:02d}/{year}",
                        'start_dt': start_dt,
                        'end_dt': end_dt,
                        'time_str': time_str,
                        'pool': pool,
                        'limited': is_limited,
                        'type': 'Family and Lane Swim'
                    }
                    
                    sessions.append(session)
                except (ValueError, TypeError):
                    continue
    
    return sessions

def create_ical(sessions):
    """Create an iCalendar (.ics) file content with proper timezone handling."""
    
    # iCal header with VTIMEZONE definition for America/Edmonton
    ical = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//UCalgary Pool Schedule//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:UCalgary Pool Schedule
X-WR-CALDESC:Weekly pool schedule from UCalgary Aquatic Centre
X-WR-TIMEZONE:America/Edmonton
REFRESH-INTERVAL;VALUE=DURATION:PT24H
BEGIN:VTIMEZONE
TZID:America/Edmonton
BEGIN:DAYLIGHT
DTSTART:20240310T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
TZOFFSETFROM:-0700
TZOFFSETTO:-0600
TZNAME:MDT
END:DAYLIGHT
BEGIN:STANDARD
DTSTART:20231105T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
TZOFFSETFROM:-0600
TZOFFSETTO:-0700
TZNAME:MST
END:STANDARD
END:VTIMEZONE
"""
    
    # Create an event for each session
    for session in sessions:
        # Generate unique ID
        event_id = f"pool-{session['start_dt'].isoformat().replace(':', '').replace('-', '')}-{session['pool']}@ucalgary.ca"
        
        # Format timestamps for iCal with timezone ID reference
        start_time = session['start_dt'].strftime('%Y%m%dT%H%M%S')
        end_time = session['end_dt'].strftime('%Y%m%dT%H%M%S')
        created = datetime.now().strftime('%Y%m%dT%H%M%SZ')
        
        # Event title
        limited_note = ' (Limited Lanes)' if session['limited'] else ''
        title = f"Pool - {session['pool']}{limited_note}"
        
        # Build event with TZID reference for proper timezone handling
        ical += f"""BEGIN:VEVENT
UID:{event_id}
DTSTAMP:{created}
DTSTART;TZID=America/Edmonton:{start_time}
DTEND;TZID=America/Edmonton:{end_time}
SUMMARY:{title}
DESCRIPTION:UCalgary Aquatic Centre - {session['type']}\\nPool: {session['pool']}\\nTime: {session['time_str']}
LOCATION:UCalgary Aquatic Centre, 2500 University Drive NW, Calgary, AB
CATEGORIES:Training,Swimming,Pool
TRANSP:OPAQUE
END:VEVENT
"""
    
    # iCal footer
    ical += "END:VCALENDAR\n"
    
    return ical

def main():
    print("Fetching UCalgary pool schedule...")
    html = fetch_schedule()
    
    if not html:
        print("Failed to fetch schedule")
        return False
    
    # Save HTML for debugging
    with open('schedule_debug.html', 'w') as f:
        f.write(html)
    print("DEBUG: HTML saved to schedule_debug.html")
    
    print("Parsing schedule...")
    sessions = parse_schedule(html)
    
    if not sessions:
        print("No sessions found in schedule")
        return False
    
    # Count sessions by type and pool
    adult_youth = [s for s in sessions if s['type'] == 'Adult/Youth Lane Swim']
    family = [s for s in sessions if s['type'] == 'Family and Lane Swim']
    sessions_25m = [s for s in sessions if s['pool'] == '25m']
    sessions_50m = [s for s in sessions if s['pool'] == '50m']
    
    print(f"Found {len(sessions)} total sessions:")
    print(f"  - {len(adult_youth)} Adult/Youth Lane Swim")
    print(f"  - {len(family)} Family and Lane Swim")
    print(f"  - {len(sessions_25m)} at 25m pool")
    print(f"  - {len(sessions_50m)} at 50m pool")
    
    # Create iCal
    ical_content = create_ical(sessions)
    
    # Save to file
    filename = 'pool-schedule.ics'
    with open(filename, 'w') as f:
        f.write(ical_content)
    
    print(f"✓ iCal file saved to: {filename}")
    return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
