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
    """Parse the HTML and extract all sessions with proper dates."""
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    
    sessions = []
    
    current_year = datetime.now().year
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    
    # Split into lines and process
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    current_date = None
    in_schedule_section = False
    
    for i, line in enumerate(lines):
        # Skip until we hit "Adult/Youth Lane Swim"
        if 'Adult/Youth Lane Swim' in line:
            in_schedule_section = True
            continue
        
        # Stop if we hit "Family and" or end of schedule
        if in_schedule_section and ('Family and' in line or 'Inflatable' in line or 'Open swim times vary' in line):
            break
        
        if not in_schedule_section:
            continue
        
        # Match day headers: "Monday, January 5"
        day_match = re.match(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(\w+)\s+(\d+)$', line, re.IGNORECASE)
        if day_match:
            day_name = day_match.group(1).capitalize()
            month_name = day_match.group(2)
            day_num = int(day_match.group(3))
            
            month = month_map.get(month_name, 1)
            year = current_year
            if month < datetime.now().month:
                year += 1
            
            current_date = {
                'day': day_name,
                'month': month,
                'day_num': day_num,
                'year': year
            }
            continue
        
        # Match time slots: "7:30 - 9:30 a.m. 25m *Limited Lanes"
        if current_date and re.search(r'\d{1,2}.*-.*\d{1,2}.*[ap]\.?m\.?', line):
            pool_match = re.search(r'(25m|50m)', line)
            is_limited = 'limited' in line.lower()
            
            if not pool_match:
                continue
            
            # Extract time string
            time_part = line[:line.index(pool_match.group(1))].strip()
            
            # Parse start and end times
            time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*-\s*(\d{1,2}):?(\d{2})?\s*([ap])\.?m\.?', time_part, re.IGNORECASE)
            if not time_match:
                continue
            
            start_hour = int(time_match.group(1))
            start_min = int(time_match.group(2) or 0)
            end_hour = int(time_match.group(3))
            end_min = int(time_match.group(4) or 0)
            am_pm = time_match.group(5).lower()
            
            # Adjust for PM (handle both a.m. and a.m formats)
            if am_pm == 'p' and start_hour != 12:
                start_hour += 12
            if am_pm == 'p' and end_hour != 12:
                end_hour += 12
            if am_pm == 'a' and start_hour == 12:
                start_hour = 0
            if am_pm == 'a' and end_hour == 12:
                end_hour = 0
            
            pool = pool_match.group(1)
            
            # Create datetime objects
            try:
                start_dt = datetime(
                    current_date['year'],
                    current_date['month'],
                    current_date['day_num'],
                    start_hour,
                    start_min
                )
                
                end_dt = datetime(
                    current_date['year'],
                    current_date['month'],
                    current_date['day_num'],
                    end_hour,
                    end_min
                )
                
                session = {
                    'day': current_date['day'],
                    'date_str': f"{current_date['month']:02d}/{current_date['day_num']:02d}/{current_date['year']}",
                    'start_dt': start_dt,
                    'end_dt': end_dt,
                    'time_str': time_part,
                    'pool': pool,
                    'limited': is_limited
                }
                
                sessions.append(session)
            except ValueError:
                # Skip invalid dates
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
