#!/usr/bin/env python3
"""
UCalgary Pool Schedule Scraper - Export to HTML
Fetches the schedule and creates a simple HTML file you can open on your phone.
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

def parse_schedule(html):
    """Parse the HTML and extract all sessions."""
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    
    sessions_by_pool = {'25m': [], '50m': []}
    
    # Split by "Adult/Youth Lane Swim"
    sections = text.split('Adult/Youth Lane Swim')
    
    for section in sections[1:]:
        lines = [l.strip() for l in section.split('\n') if l.strip()]
        current_date = None
        
        for line in lines:
            # Match day headers: "Monday, January 5"
            day_match = re.match(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(\w+)\s+(\d+)\s*$', line, re.IGNORECASE)
            if day_match:
                current_date = {
                    'day': day_match.group(1).capitalize(),
                    'month': day_match.group(2),
                    'day_num': int(day_match.group(3))
                }
                continue
            
            # Match time slots: "7:30 - 9:30 a.m. 25m"
            if current_date and re.search(r'\d{1,2}.*-.*\d{1,2}.*[ap]\.?m\.?', line):
                pool_match = re.search(r'(25m|50m)', line)
                is_limited = 'limited' in line.lower()
                
                time_str = line
                if pool_match:
                    time_str = line[:line.index(pool_match.group(1))].strip()
                
                pool = pool_match.group(1) if pool_match else 'Unknown'
                
                session = {
                    'day': current_date['day'],
                    'date': f"{current_date['month']} {current_date['day_num']}",
                    'time': time_str,
                    'limited': is_limited
                }
                
                if pool in sessions_by_pool:
                    sessions_by_pool[pool].append(session)
            
            # Stop at next section
            if 'Family and' in line or 'Inflatable' in line:
                break
    
    return sessions_by_pool

def create_html(sessions_by_pool):
    """Create a simple HTML file."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UCalgary Pool Schedule</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e293b 0%, #1e3a8a 50%, #0f172a 100%);
            color: #e0e7ff;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { font-size: 2em; margin-bottom: 10px; color: #93c5fd; }
        .subtitle { color: #bfdbfe; margin-bottom: 30px; font-size: 0.95em; }
        .timestamp { color: #94a3b8; font-size: 0.85em; margin-bottom: 20px; }
        
        .pool-section { margin-bottom: 40px; }
        .pool-header {
            font-size: 1.3em;
            font-weight: bold;
            color: white;
            padding: 12px 16px;
            background: linear-gradient(90deg, #3b82f6, #2563eb);
            border-radius: 6px 6px 0 0;
            margin-bottom: 0;
        }
        
        .sessions {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-top: none;
            border-radius: 0 0 6px 6px;
            overflow: hidden;
        }
        
        .session {
            padding: 16px;
            border-bottom: 1px solid rgba(59, 130, 246, 0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .session:last-child { border-bottom: none; }
        
        .session.limited { opacity: 0.6; }
        .session.limited-badge { color: #fca5a5; font-size: 0.8em; }
        
        .day-info { font-weight: 500; color: #e0e7ff; }
        .time-info { color: #cbd5e1; font-size: 0.9em; }
        .day { color: #93c5fd; font-weight: 600; }
        .date { color: #94a3b8; font-size: 0.85em; }
        
        .notes {
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 6px;
            padding: 20px;
            margin-top: 40px;
            font-size: 0.9em;
            line-height: 1.6;
        }
        
        .notes h3 { color: #93c5fd; margin-bottom: 12px; }
        .notes li { margin-left: 20px; margin-bottom: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏊 Pool Schedule</h1>
        <p class="subtitle">UCalgary Aquatic Centre – This Week's Sessions</p>
        <p class="timestamp">Last updated: """ + datetime.now().strftime("%A, %B %d, %Y at %I:%M %p") + """</p>
"""
    
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for pool, sessions in [('25m', sessions_by_pool['25m']), ('50m', sessions_by_pool['50m'])]:
        if not sessions:
            continue
        
        # Group by day
        by_day = {}
        for session in sessions:
            day = session['day']
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(session)
        
        html += f"""        <div class="pool-section">
            <div class="pool-header">{pool} Pool</div>
            <div class="sessions">
"""
        
        for day in day_order:
            if day not in by_day:
                continue
            
            for session in by_day[day]:
                limited_class = 'limited' if session['limited'] else ''
                limited_note = ' <span class="limited-badge">(Limited Lanes)</span>' if session['limited'] else ''
                
                html += f"""                <div class="session {limited_class}">
                    <div>
                        <div class="day-info"><span class="day">{session['day']}</span> · <span class="date">{session['date']}</span></div>
                        <div class="time-info">{session['time']}{limited_note}</div>
                    </div>
                </div>
"""
        
        html += """            </div>
        </div>
"""
    
    html += """        <div class="notes">
            <h3>📋 Notes</h3>
            <ul>
                <li>Sessions marked <span style="color: #fca5a5;">(Limited Lanes)</span> have reduced availability</li>
                <li>Schedule updates weekly – check back each Monday for current times</li>
                <li>Water restrictions in effect: limit showers to 3 minutes, steam rooms unavailable</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""
    
    return html

def main():
    print("Fetching UCalgary pool schedule...")
    html = fetch_schedule()
    
    if not html:
        print("Failed to fetch schedule")
        return
    
    print("Parsing schedule...")
    sessions = parse_schedule(html)
    
    # Count sessions
    total = sum(len(s) for s in sessions.values())
    print(f"Found {total} sessions ({len(sessions['25m'])} at 25m, {len(sessions['50m'])} at 50m)")
    
    # Create HTML
    output_html = create_html(sessions)
    
    # Save to file
    filename = 'ucalgary-pool-schedule.html'
    with open(filename, 'w') as f:
        f.write(output_html)
    
    print(f"\n✓ Schedule saved to: {filename}")
    print(f"\nOpen this file in your browser or transfer to your phone to view.")

if __name__ == '__main__':
    main()
