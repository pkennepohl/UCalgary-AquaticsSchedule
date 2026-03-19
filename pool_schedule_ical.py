#!/usr/bin/env python3
"""
UCalgary Pool Schedule to iCal (.ics) Exporter

Fetches the pool schedule and generates an iCalendar file for Outlook subscription.
Designed to run via GitHub Actions daily (only commits if schedule changes).
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from urllib.parse import quote

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

def parse_schedule(html):
    """Parse the HTML and extract all sessions from nested list structure."""
    soup = BeautifulSoup(html, 'html.parser')
    
    sessions = []
    current_year = datetime.now().year
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    
    # Find all <p> tags that contain "Adult/Youth Lane Swim"
    for p_tag in soup.find_all('p'):
        if 'Adult/Youth Lane Swim' not in p_tag.get_text():
            continue
        
        # Find the next <ul> sibling which contains the schedule
        ul = p_tag.find_next('ul')
        if not ul:
            continue
        
        # Each top-level <li> is a day
        for day_li in ul.find_all('li', recursive=False):
            day_text = day_li.get_text(strip=True)
            
            # Extract day and date: "Monday, March 16"
            day_match = re.match(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[,\s]+(\w+)\s+(\d+)', day_text, re.IGNORECASE)
            if not day_match:
                continue
            
            day_name = day_match.group(1).strip().capitalize()
            month_name = day_match.group(2).strip()
            day_num = int(day_match.group(3))
            
            month = month_map.get(month_name, 1)
            year = current_year
            if month < datetime.now().month:
                year += 1
            
            # Find nested <ul> with time slots
            nested_ul = day_li.find('ul')
            if not nested_ul:
                continue
            
            # Each nested <li> is a time slot
            for time_li in nested_ul.find_all('li', recursive=False):
                time_text = time_li.get_text(strip=True)
                
                # Extract pool and check for limited lanes
                pool_match = re.search(r'(25m|50m)', time_text)
                if not pool_match:
                    continue
                
                pool = pool_match.group(1)
                is_limited = 'limited' in time_text.lower()
                
                # Extract time portion
                pool_pos = time_text.index(pool)
                time_part = time_text[:pool_pos].strip()
                
                # Parse times
                time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*-\s*(\d{1,2}):?(\d{2})?\s*([ap])\.?m\.?', time_part, re.IGNORECASE)
                if not time_match:
                    continue
                
                start_hour = int(time_match.group(1))
                start_min = int(time_match.group(2) or 0)
                end_hour = int(time_match.group(3))
                end_min = int(time_match.group(4) or 0)
                am_pm_char = time_match.group(5).lower()
                
                is_pm = (am_pm_char == 'p')
                
                # Check for second am/pm indicator
                remaining = time_part[time_match.end():]
                second_ampm = re.search(r'([ap])\.?m\.?', remaining, re.IGNORECASE)
                if second_ampm:
                    is_pm = (second_ampm.group(1).lower() == 'p')
                
                # Adjust hours
                if is_pm and start_hour != 12:
                    start_hour += 12
                if is_pm and end_hour != 12:
                    end_hour += 12
                if not is_pm and start_hour == 12:
                    start_hour = 0
                if not is_pm and end_hour == 12:
                    end_hour = 0
                
                try:
                    start_dt = datetime(year, month, day_num, start_hour, start_min)
                    end_dt = datetime(year, month, day_num, end_hour, end_min)
                    
                    session = {
                        'day': day_name,
                        'date_str': f"{month:02d}/{day_num:02d}/{year}",
                        'start_dt': start_dt,
                        'end_dt': end_dt,
                        'time_str': time_part,
                        'pool': pool,
                        'limited': is_limited
                    }
                    
                    sessions.append(session)
                except (ValueError, TypeError):
                    continue
    
    return sessions

def create_ical(sessions):
    """Create an iCalendar (.ics) file content."""
    
    # iCal header
    ical = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//UCalgary Pool Schedule//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:UCalgary Pool Schedule
X-WR-CALDESC:Weekly pool schedule from UCalgary Aquatic Centre
X-WR-TIMEZONE:America/Edmonton
REFRESH-INTERVAL;VALUE=DURATION:PT24H
"""
    
    # Create an event for each session
    for session in sessions:
        # Generate unique ID (based on date, time, pool)
        event_id = f"pool-{session['start_dt'].isoformat().replace(':', '').replace('-', '')}-{session['pool']}@ucalgary.ca"
        
        # Format timestamps for iCal (UTC is not needed, use local time)
        start_time = session['start_dt'].strftime('%Y%m%dT%H%M%S')
        end_time = session['end_dt'].strftime('%Y%m%dT%H%M%S')
        created = datetime.now().strftime('%Y%m%dT%H%M%SZ')
        
        # Event title
        limited_note = ' (Limited Lanes)' if session['limited'] else ''
        title = f"Pool - {session['pool']}{limited_note}"
        
        # Build event
        ical += f"""BEGIN:VEVENT
UID:{event_id}
DTSTAMP:{created}
DTSTART:{start_time}
DTEND:{end_time}
SUMMARY:{title}
DESCRIPTION:UCalgary Aquatic Centre\\nPool: {session['pool']}\\nTime: {session['time_str']}
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
    
    # Count sessions
    sessions_25m = [s for s in sessions if s['pool'] == '25m']
    sessions_50m = [s for s in sessions if s['pool'] == '50m']
    print(f"Found {len(sessions)} sessions ({len(sessions_25m)} at 25m, {len(sessions_50m)} at 50m)")
    
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
