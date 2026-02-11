import os
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import re
import time

load_dotenv()
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")

# --- CLEANING HELPERS ---
def clean_num(text):
    if not text: return 0
    # Keeps only numbers (turns "1200m" -> 1200, "$50,000" -> 50000)
    clean = re.sub(r'[^\d.]', '', str(text))
    try:
        return float(clean) if '.' in clean else int(clean)
    except:
        return 0

def get_text(soup, selector):
    el = soup.select_one(selector)
    return el.text.strip() if el else None

# --- PHASE 1: FIND THE RACES ---
def get_race_links():
    # We go to the main results page to finding the MEETING links first
    base_url = "https://www.punters.com.au"
    start_url = f"{base_url}/results/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    print(f"🕵️  Scouting for race links on {start_url}...")
    try:
        resp = httpx.get(start_url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        race_links = []
        # We look for links that follow the pattern: /racing-results/venue/date/race-number/
        # This regex ensures we only get ACTUAL races, not menus.
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/racing-results/' in href and '/race-' in href:
                if href not in race_links:
                    race_links.append(f"{base_url}{href}")
        
        # Limit to first 5 races for testing so it doesn't run forever
        unique_links = list(set(race_links))[:5] 
        print(f"✅ Found {len(unique_links)} races to scrape: {unique_links}")
        return unique_links
    except Exception as e:
        print(f"🚨 Scout Error: {e}")
        return []

# --- PHASE 2: SCRAPE THE DEEP DATA ---
def scrape_single_race(target_url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    print(f"🚜 Harvesting data from: {target_url}")
    
    try:
        resp = httpx.get(target_url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. SCRAPE RACE ENVIRONMENT (Top of page)
        meeting = get_text(soup, '.event-title') or "Unknown Venue"
        track_cond = get_text(soup, '.track-condition') or "Good 4"
        dist_text = get_text(soup, '.race-distance') or "0m"
        race_name = get_text(soup, '.race-name') or "Race"
        
        master_data = []
        
        # 2. FIND THE TABLE (The real one)
        # On the specific race page, the table is usually 'results-table'
        rows = soup.select('table.results-table tbody tr')
        
        for row in rows:
            # CHECK: Does this row have a towel number? If not, it's junk.
            # Using 'data-competitor-id' is the safest check.
            if not row.get('data-competitor-id') and not row.select_one('.competitor-number'):
                continue 

            # --- MAP THE 35 COLUMNS ---
            horse_name = get_text(row, '.competitor-name a') or get_text(row, '.competitor-name')
            if not horse_name: continue

            data_packet = {
                # Identity
                "meeting_name": meeting,
                "meeting_date": datetime.now().isoformat(),
                "race_number": clean_num(target_url.split('race-')[-1].replace('/', '')),
                "race_name": race_name,
                "track_code": meeting.split(' ')[0][:4].upper(),
                "state": "VIC", # Placeholder
                "location_type": "Metro",

                # Environmental
                "track_condition": track_cond,
                "track_rating_num": int(clean_num(track_cond)) if clean_num(track_cond) != 0 else 4,
                "rail_position": "True",
                "weather_condition": "Fine",
                "race_distance": int(clean_num(dist_text)),

                # Runner
                "horse_name": horse_name,
                "age": 0, # Often hidden on this view
                "gender": "U",
                "trainer_name": get_text(row, '.trainer-name'),
                "jockey_name": get_text(row, '.jockey-name'),
                "weight_carried_kg": clean_num(get_text(row, '.weight')),
                "barrier": int(clean_num(get_text(row, '.barrier'))),

                # Results
                "finishing_position": int(clean_num(get_text(row, '.position-number'))),
                "margin_lengths": clean_num(get_text(row, '.margin')),
                "prize_money_won": clean_num(get_text(row, '.prize-money')),
                "starting_price": clean_num(get_text(row, '.sp-odds')),
                "stewards_notes": "See Full Report", # Requires 3rd click, keeping simple for now

                # Dynamics (Defaults if not present on page)
                "settling_position": "N/A",
                "position_800m": "N/A",
                "position_400m": "N/A",
                "gear_changes": "None",

                # Sectionals
                "total_race_time": get_text(row, '.time') or "0:00",
                "sectional_600m": clean_num(get_text(row, '.sectional-600')),
                "sectional_400m": 0.0,
                "sectional_200m": 0.0,

                # Pedigree
                "sire": "Unknown",
                "dam": "Unknown",
                "days_since_last_run": 0
            }
            master_data.append(data_packet)

        # 3. SEND TO SUPABASE
        if master_data:
            auth = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
            httpx.post(f"{URL}/rest/v1/results", headers=auth, json=master_data)
            print(f"✅ Success! Uploaded {len(master_data)} horses from {meeting}")
        else:
            print("⚠️ No horses found on this page.")

    except Exception as e:
        print(f"🚨 Harvest Error on {target_url}: {e}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    links = get_race_links()
    if links:
        print(f"🚀 Starting Deep Scrape on {len(links)} races...")
        for link in links:
            scrape_single_race(link)
            time.sleep(1) # Be polite to the server
    else:
        print("❌ Could not find any race links. Check the source URL.")
