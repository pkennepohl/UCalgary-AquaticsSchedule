#!/usr/bin/env python3
"""
UCalgary Pool Schedule to iCal (.ics) Exporter - Version 3 (FIXED)

Direct HTML structure parser - parses nested <ul> and <li> elements.
Improved time pattern matching with correct ordering.
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

def parse_time_range(time_str):
    """
    Parse a time range string with maximum flexibility.
    Handles: 7:30 - 9:30 a.m., 11 a.m. - 4 p.m., 6 - 8:30 p.m., 5:30 - 10 p.m., etc.
    Returns tuple: (start_hour, start_min, end_hour, end_min) or None if unparseable.
    """
    if not time_str or not isinstance(time_str, str):
        return None
    
    time_str = time_str.strip()
    time_str = re.sub(r'\s*\*?Limited Lanes\s*$', '', time_str, flags=re.IGNORECASE)
    time_str = time_str.strip()
    time_str = re.sub(r'(\d)\.(\d{2})(?![mp])', r'\1:\2', time_str)
    time_str = re.sub(r'[–—]', '-', time_str)
    time_str = re.sub(r'\s*-\s*', ' - ', time_str)
    
    # Pattern list: order matters! More specific patterns MUST come first.
    patterns = [
        # 0: Both times with minutes AND am/pm on both
        (r'(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)\s*-\s*(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)', 
         'HH:MM AM/PM - HH:MM AM/PM'),
        # 1: Both times with minutes, am/pm only on end
        (r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)',
         'HH:MM - HH:MM AM/PM'),
        # 2: Start no minutes, end with minutes AND am/pm on end
        (r'(\d{1,2})\s*-\s*(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)',
         'H - HH:MM AM/PM'),
        # 3: Start with minutes, end no minutes AND am/pm on end
        (r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2})\s*([ap]\.?m\.?)',
         'HH:MM - HH AM/PM'),
        # 4: Start no minutes with am/pm, end with minutes and am/pm
        (r'(\d{1,2})\s*([ap]\.?m\.?)\s*-\s*(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)',
         'H AM/PM - HH:MM AM/PM'),
        # 5: Start with minutes and am/pm, end no minutes with am/pm
        (r'(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)\s*-\s*(\d{1,2})\s*([ap]\.?m\.?)',
         'HH:MM AM/PM - H AM/PM'),
        # 6: Start with minutes and am/pm, end with minutes no am/pm
        (r'(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)\s*-\s*(\d{1,2}):(\d{2})',
         'HH:MM AM/PM - HH:MM'),
        # 7: Both times no minutes, am/pm on end only
        (r'(\d{1,2})\s*-\s*(\d{1,2})\s*([ap]\.?m\.?)',
         'H - HH AM/PM'),
        # 8: Both times no minutes, am/pm on both
        (r'(\d{1,2})\s*([ap]\.?m\.?)\s*-\s*(\d{1,2})\s*([ap]\.?m\.?)',
         'H AM/PM - H AM/PM'),
    ]
    
    match = None
    pattern_index = -1
    
    for idx, (pattern, desc) in enumerate(patterns):
        match = re.search(pattern, time_str, re.IGNORECASE)
        if match:
            pattern_index = idx
            break
    
    if not match:
        return None
    
    groups = match.groups()
    start_hour = start_min = end_hour = end_min = None
    
    # Debug: Check group count matches expectation
    expected_groups = [6, 5, 4, 4, 5, 5, 5, 3, 4]
    if pattern_index >= 0 and pattern_index < len(expected_groups):
        if len(groups) != expected_groups[pattern_index]:
            # Mismatch - this time didn't really match as expected
            # Try the next pattern instead of failing
            return None
    
    # Parse based on which pattern matched
    if pattern_index == 0:  # HH:MM AM/PM - HH:MM AM/PM
        start_hour, start_min, start_ampm, end_hour, end_min, end_ampm = groups
        start_hour, start_min = int(start_hour), int(start_min)
        end_hour, end_min = int(end_hour), int(end_min)
        
        start_ampm_n = normalize_ampm(start_ampm)
        end_ampm_n = normalize_ampm(end_ampm)
        
        if start_ampm_n == 'pm' and start_hour != 12:
            start_hour += 12
        elif start_ampm_n == 'am' and start_hour == 12:
            start_hour = 0
        
        if end_ampm_n == 'pm' and end_hour != 12:
            end_hour += 12
        elif end_ampm_n == 'am' and end_hour == 12:
            end_hour = 0
    
    elif pattern_index == 1:  # HH:MM - HH:MM AM/PM
        start_hour, start_min, end_hour, end_min, end_ampm = groups
        start_hour, start_min = int(start_hour), int(start_min)
        end_hour, end_min = int(end_hour), int(end_min)
        
        end_ampm_n = normalize_ampm(end_ampm)
        
        # Apply end_ampm to both
        if end_ampm_n == 'pm':
            if start_hour != 12:
                start_hour += 12
            if end_hour != 12:
                end_hour += 12
        elif end_ampm_n == 'am':
            if start_hour == 12:
                start_hour = 0
            if end_hour == 12:
                end_hour = 0
    
    elif pattern_index == 2:  # H - HH:MM AM/PM
        start_hour, end_hour, end_min, end_ampm = groups
        start_hour = int(start_hour)
        start_min = 0
        end_hour, end_min = int(end_hour), int(end_min)
        
        end_ampm_n = normalize_ampm(end_ampm)
        
        # Apply end_ampm to both
        if end_ampm_n == 'pm':
            if start_hour != 12:
                start_hour += 12
            if end_hour != 12:
                end_hour += 12
        elif end_ampm_n == 'am':
            if start_hour == 12:
                start_hour = 0
            if end_hour == 12:
                end_hour = 0
    
    elif pattern_index == 3:  # HH:MM - HH AM/PM
        start_hour, start_min, end_hour, end_ampm = groups
        start_hour, start_min = int(start_hour), int(start_min)
        end_hour = int(end_hour)
        end_min = 0
        
        end_ampm_n = normalize_ampm(end_ampm)
        
        # Apply end_ampm to both
        if end_ampm_n == 'pm':
            if start_hour != 12:
                start_hour += 12
            if end_hour != 12:
                end_hour += 12
        elif end_ampm_n == 'am':
            if start_hour == 12:
                start_hour = 0
            if end_hour == 12:
                end_hour = 0
    
    elif pattern_index == 4:  # H AM/PM - HH:MM AM/PM
        start_hour, start_ampm, end_hour, end_min, end_ampm = groups
        start_hour = int(start_hour)
        start_min = 0
        end_hour, end_min = int(end_hour), int(end_min)
        
        start_ampm_n = normalize_ampm(start_ampm)
        end_ampm_n = normalize_ampm(end_ampm)
        
        if start_ampm_n == 'pm' and start_hour != 12:
            start_hour += 12
        elif start_ampm_n == 'am' and start_hour == 12:
            start_hour = 0
        
        if end_ampm_n == 'pm' and end_hour != 12:
            end_hour += 12
        elif end_ampm_n == 'am' and end_hour == 12:
            end_hour = 0
    
    elif pattern_index == 5:  # HH:MM AM/PM - H AM/PM
        start_hour, start_min, start_ampm, end_hour, end_ampm = groups
        start_hour, start_min = int(start_hour), int(start_min)
        end_hour = int(end_hour)
        end_min = 0
        
        start_ampm_n = normalize_ampm(start_ampm)
        end_ampm_n = normalize_ampm(end_ampm)
        
        if start_ampm_n == 'pm' and start_hour != 12:
            start_hour += 12
        elif start_ampm_n == 'am' and start_hour == 12:
            start_hour = 0
        
        if end_ampm_n == 'pm' and end_hour != 12:
            end_hour += 12
        elif end_ampm_n == 'am' and end_hour == 12:
            end_hour = 0
    
    elif pattern_index == 6:  # HH:MM AM/PM - HH:MM
        start_hour, start_min, start_ampm, end_hour, end_min = groups
        start_hour, start_min = int(start_hour), int(start_min)
        end_hour, end_min = int(end_hour), int(end_min)
        
        start_ampm_n = normalize_ampm(start_ampm)
        
        # Apply start_ampm to both
        if start_ampm_n == 'pm':
            if start_hour != 12:
                start_hour += 12
            if end_hour != 12:
                end_hour += 12
        elif start_ampm_n == 'am':
            if start_hour == 12:
                start_hour = 0
            if end_hour == 12:
                end_hour = 0
    
    elif pattern_index == 7:  # H - HH AM/PM
        start_hour, end_hour, end_ampm = groups
        start_hour = int(start_hour)
        start_min = 0
        end_hour = int(end_hour)
        end_min = 0
        
        end_ampm_n = normalize_ampm(end_ampm)
        
        # Apply end_ampm to both
        if end_ampm_n == 'pm':
            if start_hour != 12:
                start_hour += 12
            if end_hour != 12:
                end_hour += 12
        elif end_ampm_n == 'am':
            if start_hour == 12:
                start_hour = 0
            if end_hour == 12:
                end_hour = 0
    
    elif pattern_index == 8:  # H AM/PM - H AM/PM
        start_hour, start_ampm, end_hour, end_ampm = groups
        start_hour = int(start_hour)
        start_min = 0
        end_hour = int(end_hour)
        end_min = 0
        
        start_ampm_n = normalize_ampm(start_ampm)
        end_ampm_n = normalize_ampm(end_ampm)
        
        if start_ampm_n == 'pm' and start_hour != 12:
            start_hour += 12
        elif start_ampm_n == 'am' and start_hour == 12:
            start_hour = 0
        
        if end_ampm_n == 'pm' and end_hour != 12:
            end_hour += 12
        elif end_ampm_n == 'am' and end_hour == 12:
            end_hour = 0
    
    else:
        return None
    
    # Validate
    if start_hour is None or end_hour is None:
        return None
    if start_hour < 0 or start_hour > 23 or end_hour < 0 or end_hour > 23:
        return None
    if start_min < 0 or start_min > 59 or end_min < 0 or end_min > 59:
        return None
    if start_hour * 60 + start_min >= end_hour * 60 + end_min:
        return None
    
    return (start_hour, start_min, end_hour, end_min)

def apply_chronological_correction(sessions):
    """
    Validate and correct AM/PM errors within each day.
    All sessions on the same day must be in chronological order (regardless of type/pool).
    """
    from collections import defaultdict
    
    # Group by day (month, day_num)
    groups = defaultdict(list)
    for idx, session in enumerate(sessions):
        key = (session['month'], session['day_num'])
        groups[key].append((idx, session))
    
    corrections = []
    
    for key, group in groups.items():
        month, day_num = key
        
        # Check each session against the previous one
        for i in range(1, len(group)):
            prev_idx, prev_session = group[i-1]
            curr_idx, curr_session = group[i]
            
            prev_end_mins = prev_session['end_hour'] * 60 + prev_session['end_min']
            curr_start_mins = curr_session['start_hour'] * 60 + curr_session['start_min']
            
            # Check if current session starts before previous ends
            if curr_start_mins < prev_end_mins:
                # Try flipping the CURRENT session first
                flipped_start = curr_session['start_hour']
                flipped_end = curr_session['end_hour']
                
                flip_worked = False
                
                # Try flipping current session
                if flipped_start >= 12 and flipped_end >= 12:
                    # Both PM, flip to AM
                    flipped_start = flipped_start - 12 if flipped_start > 12 else 12
                    flipped_end = flipped_end - 12 if flipped_end > 12 else 12
                elif flipped_start < 12 and flipped_end < 12:
                    # Both AM, flip to PM
                    flipped_start = flipped_start + 12
                    flipped_end = flipped_end + 12
                else:
                    # Mixed AM/PM on current, can't flip - try prev instead
                    flipped_start = curr_session['start_hour']
                    flipped_end = curr_session['end_hour']
                
                flipped_start_mins = flipped_start * 60 + curr_session['start_min']
                flipped_end_mins = flipped_end * 60 + curr_session['end_min']
                
                # If flipping current works, apply it
                if flipped_start_mins >= prev_end_mins:
                    original_str = f"{curr_session['start_hour']:02d}:{curr_session['start_min']:02d} - {curr_session['end_hour']:02d}:{curr_session['end_min']:02d}"
                    flipped_str = f"{flipped_start:02d}:{curr_session['start_min']:02d} - {flipped_end:02d}:{curr_session['end_min']:02d}"
                    
                    corrections.append(
                        f"  {curr_session['day_name']} {month} {day_num} | {curr_session['swim_type'][:15]:15} | "
                        f"{curr_session['pool']:4} | {original_str} → {flipped_str}"
                    )
                    
                    curr_session['start_hour'] = flipped_start
                    curr_session['end_hour'] = flipped_end
                    group[i] = (curr_idx, curr_session)
                    sessions[curr_idx] = curr_session
                    flip_worked = True
                
                # If flipping current didn't work, try flipping PREVIOUS session
                if not flip_worked:
                    prev_flipped_start = prev_session['start_hour']
                    prev_flipped_end = prev_session['end_hour']
                    
                    if prev_flipped_start >= 12 and prev_flipped_end >= 12:
                        prev_flipped_start = prev_flipped_start - 12 if prev_flipped_start > 12 else 12
                        prev_flipped_end = prev_flipped_end - 12 if prev_flipped_end > 12 else 12
                    elif prev_flipped_start < 12 and prev_flipped_end < 12:
                        prev_flipped_start = prev_flipped_start + 12
                        prev_flipped_end = prev_flipped_end + 12
                    else:
                        # Mixed AM/PM, can't flip
                        continue
                    
                    prev_flipped_end_mins = prev_flipped_end * 60 + prev_session['end_min']
                    
                    # Check if flipping previous fixes the order
                    if curr_start_mins >= prev_flipped_end_mins:
                        original_str = f"{prev_session['start_hour']:02d}:{prev_session['start_min']:02d} - {prev_session['end_hour']:02d}:{prev_session['end_min']:02d}"
                        flipped_str = f"{prev_flipped_start:02d}:{prev_session['start_min']:02d} - {prev_flipped_end:02d}:{prev_session['end_min']:02d}"
                        
                        corrections.append(
                            f"  {prev_session['day_name']} {month} {day_num} | {prev_session['swim_type'][:15]:15} | "
                            f"{prev_session['pool']:4} | {original_str} → {flipped_str}"
                        )
                        
                        prev_session['start_hour'] = prev_flipped_start
                        prev_session['end_hour'] = prev_flipped_end
                        group[i-1] = (prev_idx, prev_session)
                        sessions[prev_idx] = prev_session
    
    if corrections:
        print("\n" + "=" * 120)
        print("AM/PM CORRECTIONS MADE (Chronological Order Validation)")
        print("=" * 120)
        for correction in corrections:
            print(correction)
        print("=" * 120 + "\n")
    
    return sessions

def parse_schedule(html):
    """Parse the HTML and extract schedule."""
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    sessions = []
    
    p_tags = soup.find_all('p')
    
    for p in p_tags:
        p_text = p.get_text()
        if 'Inflatable Swim' in p_text:
            continue
        
        if 'Adult/Youth Lane Swim' not in p_text and 'Family and Lane Swim' not in p_text:
            continue
        
        swim_type = 'Adult/Youth Lane Swim' if 'Adult/Youth Lane Swim' in p_text else 'Family and Lane Swim'
        
        ul = p.find_next('ul')
        if not ul:
            continue
        
        day_items = ul.find_all('li', recursive=False)
        
        for day_li in day_items:
            day_text = day_li.get_text(strip=True)
            
            day_match = re.match(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[,\s]+(\w+)\s+(\d{1,2})', day_text, re.IGNORECASE)
            if not day_match:
                continue
            
            day_name = day_match.group(1)
            month_name = day_match.group(2)
            day_num = int(day_match.group(3))
            
            nested_ul = day_li.find('ul')
            if not nested_ul:
                continue
            
            time_items = nested_ul.find_all('li', recursive=False)
            
            for time_li in time_items:
                time_text = time_li.get_text(strip=True)
                
                pool_match = re.search(r'(25m|50m)', time_text)
                if not pool_match:
                    continue
                
                pool = pool_match.group(1)
                
                time_range = re.search(r'(.+?)\s+(?:25m|50m)', time_text)
                if time_range:
                    time_str = time_range.group(1).strip()
                else:
                    time_str = time_text
                
                parsed = parse_time_range(time_str)
                if not parsed:
                    continue
                
                start_h, start_m, end_h, end_m = parsed
                
                sessions.append({
                    'day_name': day_name,
                    'month': month_name,
                    'day_num': day_num,
                    'start_hour': start_h,
                    'start_min': start_m,
                    'end_hour': end_h,
                    'end_min': end_m,
                    'pool': pool,
                    'swim_type': swim_type,
                    'time_str': time_str
                })
    
    return sessions

def create_ics(sessions):
    """Generate iCal file content."""
    ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//UCalgary Pool Schedule//NONSGML v1.0//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:UCalgary Pool Schedule
X-WR-TIMEZONE:America/Edmonton
REFRESH-INTERVAL;VALUE=DURATION:PT24H
BEGIN:VTIMEZONE
TZID:America/Edmonton
BEGIN:DAYLIGHT
DTSTART:20260308T020000
TZOFFSETFROM:-0700
TZOFFSETTO:-0600
TZNAME:MDT
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
DTSTART:20261101T020000
TZOFFSETFROM:-0600
TZOFFSETTO:-0700
TZNAME:MST
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE
"""
    
    for session in sessions:
        # Determine the date
        try:
            dt = datetime.strptime(f"{session['month']} {session['day_num']} 2026", '%B %d %Y')
        except:
            continue
        
        date_str = dt.strftime('%Y%m%d')
        start_time = f"{date_str}T{session['start_hour']:02d}{session['start_min']:02d}00"
        end_time = f"{date_str}T{session['end_hour']:02d}{session['end_min']:02d}00"
        
        summary = f"Pool - {session['pool']}"
        description = f"{session['swim_type']}\\nTime: {session['time_str']}"
        
        ics += f"""BEGIN:VEVENT
DTSTART;TZID=America/Edmonton:{start_time}
DTEND;TZID=America/Edmonton:{end_time}
SUMMARY:{summary}
DESCRIPTION:{description}
TRANSP:TRANSPARENT
END:VEVENT
"""
    
    ics += "END:VCALENDAR\n"
    return ics

def main():
    print("Fetching UCalgary pool schedule...")
    html = fetch_schedule()
    
    if not html:
        print("Failed to fetch schedule")
        return
    
    # Debug: Save HTML
    with open('schedule_debug.html', 'w') as f:
        f.write(html)
    
    print("Parsing schedule...")
    sessions = parse_schedule(html)
    
    print(f"Found {len(sessions)} sessions")
    
    print("Validating chronological order...")
    sessions = apply_chronological_correction(sessions)
    
    if sessions:
        ics_content = create_ics(sessions)
        
        with open('pool-schedule.ics', 'w') as f:
            f.write(ics_content)
        
        print(f"✓ Created pool-schedule.ics with {len(sessions)} events")
    else:
        print("✗ No sessions found!")

if __name__ == '__main__':
    main()
