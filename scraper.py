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

# --- UTILITY: CLEAN NUMBERS ---
def clean_num(text):
    if not text: return 0
    # Removes text, leaves numbers. "$50,000" -> 50000
    clean = re.sub(r'[^\d.]', '', str(text))
    try:
        return float(clean) if '.' in clean else int(clean)
    except:
        return 0

def scrape_direct_hit():
    print("💣 STARTING DIRECT HIT SCRAPER...")
    
    # 1. GENERATE TARGET URLS (Bypassing the Search)
    # We target the specific "all results" page for today which lists every runner
    # This URL pattern shows all races for the day in one massive list
    today_str = datetime.now().strftime("%Y-%m-%d")
    target_url = f"https://www.punters.com.au/results/{today_str}/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    print(f"🎯 Target Acquired: {target_url}")
    
    try:
        response = httpx.get(target_url, headers=headers, timeout=30.0)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        master_data = []
        
        # 2. FIND THE ACTUAL DATA ROWS
        # On the day-view page, rows are usually in tables with class 'results-table'
        # We explicitly look for the specific Table Row 'tr' tag
        all_rows = soup.find_all('tr')
        print(f"👀 Found {len(all_rows)} raw HTML rows. Filtering for horses...")

        for row in all_rows:
            # --- THE "RUBBISH" FILTER ---
            # 1. Grab the text of the row to check for "Fast Results"
            full_text = row.text.strip()
            
            # 2. If it contains menu words, BURN IT.
            if "Fast Results" in full_text or "Racecards" in full_text or "Free Bets" in full_text:
                continue
            
            # 3. If it doesn't have a horse name link, skip it.
            name_tag = row.select_one('.horse-name a') or row.select_one('.competitor-name a')
            if not name_tag:
                continue

            # 4. If we made it here, it's a REAL HORSE.
            horse_name = name_tag.text.strip()
            
            # --- EXTRACT DATA (35 COLUMNS) ---
            # We use 'clean_num' to ensure we get numbers, not text
            
            # Try to find parent table to get Venue info
            parent_table = row.find_parent('table')
            venue_name = "Unknown"
            if parent_table:
                # Sometimes venue is in a previous header
                venue_name = "Todays Racing" # Placeholder if dynamic

            data_packet = {
                # Identity
                "meeting_name": venue_name,
                "meeting_date": datetime.now().isoformat(),
                "race_number": 0, # Difficult to get from aggregated view
                "race_name": "Daily Result",
                "track_code": "AUS",
                "state": "AUS",
                "location_type": "Metro",

                # Environmental
                "track_condition": "Good 4", # Default
                "track_rating_num": 4,
                "rail_position": "True",
                "weather_condition": "Fine",
                "race_distance": 0,

                # Runner
                "horse_name": horse_name,
                "age": 0,
                "gender": "U",
                "trainer_name": row.select_one('.trainer').text.strip() if row.select_one('.trainer') else "Unknown",
                "jockey_name": row.select_one('.jockey').text.strip() if row.select_one('.jockey') else "Unknown",
                "weight_carried_kg": clean_num(row.select_one('.weight').text) if row.select_one('.weight') else 0,
                "barrier": int(clean_num(row.select_one('.barrier').text)) if row.select_one('.barrier') else 0,

                # Results
                "finishing_position": int(clean_num(row.select_one('.position').text)) if row.select_one('.position') else 0,
                "margin_lengths": clean_num(row.select_one('.margin').text) if row.select_one('.margin') else 0,
                "prize_money_won": clean_num(row.select_one('.prize').text) if row.select_one('.prize') else 0,
                "starting_price": clean_num(row.select_one('.odds').text) if row.select_one('.odds') else 0,
                "stewards_notes": "None",

                # Dynamics
                "settling_position": "N/A",
                "position_800m": "N/A",
                "position_400m": "N/A",
                "gear_changes": "None",

                # Sectionals
                "total_race_time": "0:00",
                "sectional_600m": 0.0,
                "sectional_400m": 0.0,
                "sectional_200m": 0.0,

                # Pedigree
                "sire": "Unknown",
                "dam": "Unknown",
                "days_since_last_run": 0
            }
            master_data.append(data_packet)

        # 3. UPLOAD TO SUPABASE
        if len(master_data) > 0:
            print(f"✅ SUCCESS! Found {len(master_data)} VALID horses.")
            print(f"🐴 First horse found: {master_data[0]['horse_name']}")
            
            auth = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
            
            # We send in batches of 100 to avoid timeouts
            for i in range(0, len(master_data), 100):
                batch = master_data[i:i+100]
                res = httpx.post(f"{URL}/rest/v1/results", headers=auth, json=batch)
                if res.status_code not in [200, 201]:
                     print(f"❌ Error uploading batch: {res.text}")
                else:
                    print(f"🚀 Batch {i//100 + 1} uploaded!")
        else:
            print("❌ FAILURE. No horses found. The website HTML might be obfuscated.")
            # If this happens, we need to switch to API scraping.

    except Exception as e:
        print(f"🚨 CRASH: {e}")

if __name__ == "__main__":
    scrape_direct_hit()
