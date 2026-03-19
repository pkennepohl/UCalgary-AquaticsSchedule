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
    Parse a time range string like '7:30 - 9:30 a.m.' or '11 a.m. - 4 p.m.'
    Returns tuple: (start_hour, start_min, end_hour, end_min)
    """
    time_str = ' '.join(time_str.split()).strip()
    
    # Remove asterisks and "Limited Lanes" text
    time_str = re.sub(r'\s*\*?Limited Lanes\s*$', '', time_str, flags=re.IGNORECASE)
    
    # Pattern: HH:MM or H followed by optional :MM, then optional am/pm, dash, repeat
    # Handles: "7:30 - 9:30 a.m." or "11 a.m. - 4 p.m." or "7 - 10 p.m."
    pattern = r'(\d{1,2})(?::(\d{2}))?\s*(?:am|a\.m|a\.m\.)?[\s]*-[\s]*(\d{1,2})(?::(\d{2}))?\s*(?:am|a\.m|a\.m\.|pm|p\.m|p\.m\.)'
    
    match = re.search(pattern, time_str, re.IGNORECASE)
    if not match:
        return None
    
    start_hour = int(match.group(1))
    start_min = int(match.group(2) or 0)
    end_hour = int(match.group(3))
    end_min = int(match.group(4) or 0)
    
    # Split by dash to check which side has which meridiem
    dash_pos = time_str.find('-')
    before_dash = time_str[:dash_pos].lower()
    after_dash = time_str[dash_pos+1:].lower()
    
    # Check each side for am/pm
    before_has_am = 'am' in before_dash
    before_has_pm = 'pm' in before_dash
    after_has_am = 'am' in after_dash
    after_has_pm = 'pm' in after_dash
    
    # Apply 12-hour conversion based on what's specified
    # Start time: use before_dash indicator, or infer from after_dash if not specified
    if before_has_pm:
        if start_hour != 12:
            start_hour += 12
    elif before_has_am:
        if start_hour == 12:
            start_hour = 0  # 12 a.m. = midnight
    elif after_has_pm and not after_has_am:
        # No am/pm before dash, but "pm" after and no "am" means both are PM
        if start_hour != 12:
            start_hour += 12
    
    # End time: use after_dash indicator
    if after_has_pm:
        if end_hour != 12:
            end_hour += 12
    elif after_has_am:
        if end_hour == 12:
            end_hour = 0  # 12 a.m. = midnight
    elif before_has_pm and not before_has_am:
        # No am/pm after dash, but "pm" before and no "am" means both are PM
        if end_hour != 12:
            end_hour += 12
    
    return (start_hour, start_min, end_hour, end_min)

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
