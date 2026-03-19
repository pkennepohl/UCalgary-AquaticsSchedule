#!/usr/bin/env python3
"""
UCalgary Pool Schedule to iCal (.ics) Exporter - Version 3

Direct HTML structure parser - parses nested <ul> and <li> elements.
Much more reliable than text-based parsing.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
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
    Parse a time range string with maximum flexibility to handle staff input variations.
    Handles: 7:30 - 9:30 a.m., 11 a.m. - 4 p.m., 7 - 10 p.m., 9.30 - 18.30, etc.
    Returns tuple: (start_hour, start_min, end_hour, end_min) or None if unparseable.
    """
    if not time_str or not isinstance(time_str, str):
        return None
    
    original = time_str
    time_str = time_str.strip()
    
    # Remove asterisks and "Limited Lanes" text
    time_str = re.sub(r'\s*\*?Limited Lanes\s*$', '', time_str, flags=re.IGNORECASE)
    time_str = time_str.strip()
    
    # Normalize: convert periods to colons for time separators (but keep a.m. periods)
    # Replace time periods (e.g., "7.30") with colons, but preserve "a.m." and "p.m."
    time_str = re.sub(r'(\d)\.(\d{2})(?![mp])', r'\1:\2', time_str)  # "7.30" → "7:30", but not "a.m"
    
    # Normalize different dash types to single dash
    time_str = re.sub(r'[–—]', '-', time_str)  # em-dash, en-dash → regular dash
    
    # Normalize spaces around dash
    time_str = re.sub(r'\s*-\s*', ' - ', time_str)
    
    # Try multiple patterns, from most specific to least specific
    patterns = [
        # Pattern 1: "HH:MM AM/PM - HH:MM AM/PM" (most specific)
        r'(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)\s*-\s*(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)',
        # Pattern 2: "HH:MM - HH:MM AM/PM"
        r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)',
        # Pattern 3: "H AM/PM - HH:MM AM/PM" (no minutes on start)
        r'(\d{1,2})\s*([ap]\.?m\.?)\s*-\s*(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)',
        # Pattern 4: "HH:MM AM/PM - HH AM/PM" (no minutes on end)
        r'(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)\s*-\s*(\d{1,2})\s*([ap]\.?m\.?)',
        # Pattern 5: "H - HH AM/PM" (no minutes either side)
        r'(\d{1,2})\s*-\s*(\d{1,2})\s*([ap]\.?m\.?)',
        # Pattern 6: "HH:MM - HH AM/PM" (minutes on start, not end)
        r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2})\s*([ap]\.?m\.?)',
        # Pattern 7: "HH:MM AM/PM - HH:MM" (no AM/PM on end)
        r'(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)\s*-\s*(\d{1,2}):(\d{2})',
        # Pattern 8: "H AM/PM - H AM/PM" (no colons, compact format)
        r'(\d{1,2})\s*([ap]\.?m\.?)\s*-\s*(\d{1,2})\s*([ap]\.?m\.?)',
        # Pattern 9: Single time with AM/PM "HH:MM AM/PM"
        r'(\d{1,2}):(\d{2})\s+([ap]\.?m\.?)(?:\s|$)',
        # Pattern 10: Single time "H AM/PM" (no colon)
        r'^(\d{1,2})\s+([ap]\.?m\.?)(?:\s|$)',
    ]
    
    match = None
    pattern_used = None
    
    for pattern in patterns:
        match = re.search(pattern, time_str, re.IGNORECASE)
        if match:
            pattern_used = pattern
            break
    
    if not match:
        # Could not parse
        return None
    
    groups = match.groups()
    
    # Extract components based on which pattern matched
    if pattern_used == patterns[0]:  # "HH:MM AM/PM - HH:MM AM/PM"
        start_hour, start_min, start_ampm, end_hour, end_min, end_ampm = groups
        start_hour, start_min = int(start_hour), int(start_min)
        end_hour, end_min = int(end_hour), int(end_min)
        start_ampm_normalized = normalize_ampm(start_ampm)
        end_ampm_normalized = normalize_ampm(end_ampm)
        
        if start_ampm_normalized == 'pm' and start_hour != 12:
            start_hour += 12
        elif start_ampm_normalized == 'am' and start_hour == 12:
            start_hour = 0
        
        if end_ampm_normalized == 'pm' and end_hour != 12:
            end_hour += 12
        elif end_ampm_normalized == 'am' and end_hour == 12:
            end_hour = 0
    
    elif pattern_used == patterns[1]:  # "HH:MM - HH:MM AM/PM"
        start_hour, start_min, end_hour, end_min, end_ampm = groups
        start_hour, start_min = int(start_hour), int(start_min)
        end_hour, end_min = int(end_hour), int(end_min)
        end_ampm_normalized = normalize_ampm(end_ampm)
        
        # Apply end_ampm to both if only end is specified
        if end_ampm_normalized == 'pm':
            if start_hour != 12:
                start_hour += 12
            if end_hour != 12:
                end_hour += 12
        elif end_ampm_normalized == 'am':
            if start_hour == 12:
                start_hour = 0
            if end_hour == 12:
                end_hour = 0
    
    elif pattern_used == patterns[2]:  # "H AM/PM - HH:MM AM/PM"
        start_hour, start_ampm, end_hour, end_min, end_ampm = groups
        start_hour = int(start_hour)
        start_min = 0
        end_hour, end_min = int(end_hour), int(end_min)
        start_ampm_normalized = normalize_ampm(start_ampm)
        end_ampm_normalized = normalize_ampm(end_ampm)
        
        if start_ampm_normalized == 'pm' and start_hour != 12:
            start_hour += 12
        elif start_ampm_normalized == 'am' and start_hour == 12:
            start_hour = 0
        
        if end_ampm_normalized == 'pm' and end_hour != 12:
            end_hour += 12
        elif end_ampm_normalized == 'am' and end_hour == 12:
            end_hour = 0
    
    elif pattern_used == patterns[3]:  # "HH:MM AM/PM - HH AM/PM"
        start_hour, start_min, start_ampm, end_hour, end_ampm = groups
        start_hour, start_min = int(start_hour), int(start_min)
        end_hour = int(end_hour)
        end_min = 0
        start_ampm_normalized = normalize_ampm(start_ampm)
        end_ampm_normalized = normalize_ampm(end_ampm)
        
        if start_ampm_normalized == 'pm' and start_hour != 12:
            start_hour += 12
        elif start_ampm_normalized == 'am' and start_hour == 12:
            start_hour = 0
        
        if end_ampm_normalized == 'pm' and end_hour != 12:
            end_hour += 12
        elif end_ampm_normalized == 'am' and end_hour == 12:
            end_hour = 0
    
    elif pattern_used == patterns[4]:  # "H - HH AM/PM"
        start_hour, end_hour, end_ampm = groups
        start_hour = int(start_hour)
        start_min = 0
        end_hour = int(end_hour)
        end_min = 0
        end_ampm_normalized = normalize_ampm(end_ampm)
        
        # Apply end_ampm to both
        if end_ampm_normalized == 'pm':
            if start_hour != 12:
                start_hour += 12
            if end_hour != 12:
                end_hour += 12
        elif end_ampm_normalized == 'am':
            if start_hour == 12:
                start_hour = 0
            if end_hour == 12:
                end_hour = 0
    
    elif pattern_used == patterns[5]:  # "HH:MM - HH AM/PM"
        start_hour, start_min, end_hour, end_ampm = groups
        start_hour, start_min = int(start_hour), int(start_min)
        end_hour = int(end_hour)
        end_min = 0
        end_ampm_normalized = normalize_ampm(end_ampm)
        
        # Apply end_ampm to both
        if end_ampm_normalized == 'pm':
            if start_hour != 12:
                start_hour += 12
            if end_hour != 12:
                end_hour += 12
        elif end_ampm_normalized == 'am':
            if start_hour == 12:
                start_hour = 0
            if end_hour == 12:
                end_hour = 0
    
    elif pattern_used == patterns[6]:  # "HH:MM AM/PM - HH:MM"
        start_hour, start_min, start_ampm, end_hour, end_min = groups
        start_hour, start_min = int(start_hour), int(start_min)
        end_hour, end_min = int(end_hour), int(end_min)
        start_ampm_normalized = normalize_ampm(start_ampm)
        
        # Apply start_ampm to both
        if start_ampm_normalized == 'pm':
            if start_hour != 12:
                start_hour += 12
            if end_hour != 12:
                end_hour += 12
        elif start_ampm_normalized == 'am':
            if start_hour == 12:
                start_hour = 0
            if end_hour == 12:
                end_hour = 0
    
    elif pattern_used == patterns[7]:  # "H AM/PM - H AM/PM" (pattern 8)
        start_hour, start_ampm, end_hour, end_ampm = groups
        start_hour = int(start_hour)
        start_min = 0
        end_hour = int(end_hour)
        end_min = 0
        start_ampm_normalized = normalize_ampm(start_ampm)
        end_ampm_normalized = normalize_ampm(end_ampm)
        
        if start_ampm_normalized == 'pm' and start_hour != 12:
            start_hour += 12
        elif start_ampm_normalized == 'am' and start_hour == 12:
            start_hour = 0
        
        if end_ampm_normalized == 'pm' and end_hour != 12:
            end_hour += 12
        elif end_ampm_normalized == 'am' and end_hour == 12:
            end_hour = 0
    
    elif pattern_used == patterns[8]:  # "HH:MM AM/PM" (single time, pattern 9)
        start_hour, start_min, start_ampm = groups
        start_hour, start_min = int(start_hour), int(start_min)
        start_ampm_normalized = normalize_ampm(start_ampm)
        
        if start_ampm_normalized == 'pm' and start_hour != 12:
            start_hour += 12
        elif start_ampm_normalized == 'am' and start_hour == 12:
            start_hour = 0
        
        # For single time, we can't proceed without an end time
        return None
    
    elif pattern_used == patterns[9]:  # "H AM/PM" (single time, pattern 10)
        start_hour, start_ampm = groups
        start_hour = int(start_hour)
        start_ampm_normalized = normalize_ampm(start_ampm)
        
        if start_ampm_normalized == 'pm' and start_hour != 12:
            start_hour += 12
        elif start_ampm_normalized == 'am' and start_hour == 12:
            start_hour = 0
        
        # For single time, we can't proceed without an end time
        return None
    
    # Validate the result
    if start_hour < 0 or start_hour > 23 or end_hour < 0 or end_hour > 23:
        return None
    
    if start_min < 0 or start_min > 59 or end_min < 0 or end_min > 59:
        return None
    
    return (start_hour, start_min, end_hour, end_min)

def normalize_ampm(ampm_str):
    """Normalize various AM/PM formats to 'am' or 'pm'."""
    if not ampm_str:
        return None
    ampm_str = ampm_str.lower().replace('.', '').replace(' ', '')
    if ampm_str.startswith('p'):
        return 'pm'
    elif ampm_str.startswith('a'):
        return 'am'
    return None

def parse_schedule(html):
    """Parse the HTML by working directly with nested <ul> and <li> structure."""
    soup = BeautifulSoup(html, 'html.parser')
    
    sessions = []
    current_year = datetime.now().year
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    
    # Find all <p> tags
    for p_tag in soup.find_all('p'):
        p_text = p_tag.get_text()
        
        # Skip the introductory combo header
        if 'Inflatable Swim' in p_text:
            continue
        
        # Check if this is a schedule header
        if 'Adult/Youth Lane Swim' not in p_text and 'Family and Lane Swim' not in p_text:
            continue
        
        # Determine schedule type
        if 'Adult/Youth Lane Swim' in p_text:
            schedule_type = 'Adult/Youth Lane Swim'
        else:
            schedule_type = 'Family and Lane Swim'
        
        # Find the next <ul> sibling
        ul = p_tag.find_next('ul')
        if not ul:
            continue
        
        # Get all top-level <li> elements (each is a day)
        day_items = ul.find_all('li', recursive=False)
        
        for day_li in day_items:
            # Get all text before any nested <ul>
            day_text = day_li.get_text(strip=True)
            
            # Extract day and date from the first part
            # Pattern: "Day, Month Date"
            day_match = re.match(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[,\s]+(\w+)\s+(\d{1,2})', day_text, re.IGNORECASE)
            
            if not day_match:
                continue
            
            day_name = day_match.group(1).strip()
            month_name = day_match.group(2).strip()
            day_num = int(day_match.group(3))
            
            month = month_map.get(month_name, 1)
            year = current_year
            
            # Handle year wraparound: if month is earlier than current month, it's next year
            if month < datetime.now().month:
                year += 1
            
            # Find nested <ul> with time slots
            nested_ul = day_li.find('ul')
            if not nested_ul:
                continue
            
            # Get all time slot <li> elements
            time_items = nested_ul.find_all('li', recursive=False)
            
            for time_li in time_items:
                time_text = time_li.get_text(strip=True)
                
                # Extract pool size
                pool_match = re.search(r'(25m|50m)', time_text)
                if not pool_match:
                    continue
                
                pool = pool_match.group(1)
                
                # Check for "Limited Lanes"
                is_limited = '*Limited Lanes' in time_text or 'Limited Lanes' in time_text
                
                # Extract time portion (everything before pool size)
                pool_pos = time_text.index(pool)
                time_str = time_text[:pool_pos].strip()
                
                # Parse the time
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
                        'type': schedule_type
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
TRANSP:TRANSPARENT
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
