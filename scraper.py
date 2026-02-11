import os
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import re

load_dotenv()
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")

def clean_num(text):
    if not text: return 0
    clean = re.sub(r'[^\d.]', '', str(text))
    try:
        return float(clean) if '.' in clean else int(clean)
    except:
        return 0

def scrape_strict_validator():
    # We target the date-specific page to avoid the homepage "Hub" layout
    today = datetime.now().strftime("%Y-%m-%d")
    target_url = f"https://www.punters.com.au/results/{today}/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print(f"🕵️  Analysing tables on {target_url}...")
    
    try:
        response = httpx.get(target_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        master_data = []
        
        # 1. FIND ALL TABLES
        all_tables = soup.find_all('table')
        print(f"👀 Found {len(all_tables)} tables. Filtering for REAL race data...")
        
        for table in all_tables:
            # --- THE VALIDATOR ---
            # Check the table header text. If it doesn't mention "Horse" or "Runner", IT IS JUNK.
            header_text = table.get_text().lower()
            if "horse" not in header_text and "runner" not in header_text:
                continue # Skip navigation tables, ad tables, etc.

            # Extract Venue (Environmental Data)
            # Usually found in a heading just before the table
            venue_name = "Unknown Venue"
            prev_node = table.find_previous(['h2', 'h3', 'div', 'span'])
            if prev_node:
                venue_name = prev_node.get_text().strip()

            # 2. PROCESS ROWS
            rows = table.find_all('tr')
            for row in rows:
                # --- THE STRICT FILTER ---
                # A real horse row MUST have a finishing position number.
                # "Fast Results" does not have a number.
                pos_text = ""
                pos_el = row.select_one('.position-number') or row.select_one('td:first-child')
                
                if pos_el:
                    pos_text = pos_el.get_text().strip()
                
                # If the first column isn't a number (e.g. it's blank or text), SKIP IT.
                if not pos_text.isdigit():
                    continue

                # 3. EXTRACT 35 COLUMNS
                horse_el = row.select_one('.horse-name a') or row.select_one('.competitor-name')
                if not horse_el: continue
                
                horse_name = horse_el.get_text().strip()
                
                # Data Mapping
                data_packet = {
                    "meeting_name": venue_name,
                    "meeting_date": datetime.now().isoformat(),
                    "race_number": 0,
                    "race_name": "Daily Results",
                    "track_code": venue_name[:3].upper(),
                    "state": "AUS",
                    "location_type": "Metro",
                    "track_condition": "Good 4", # Placeholder
                    "track_rating_num": 4,
                    "rail_position": "True",
                    "weather_condition": "Fine",
                    "race_distance": 0,
                    
                    "horse_name": horse_name,
                    "age": 0,
                    "gender": "U",
                    "trainer_name": row.select_one('.trainer').text.strip() if row.select_one('.trainer') else "Unknown",
                    "jockey_name": row.select_one('.jockey').text.strip() if row.select_one('.jockey') else "Unknown",
                    "weight_carried_kg": clean_num(row.select_one('.weight').text) if row.select_one('.weight') else 0,
                    "barrier": int(clean_num(row.select_one('.barrier').text)) if row.select_one('.barrier') else 0,
                    
                    "finishing_position": int(pos_text), # We verified this is a digit above
                    "margin_lengths": clean_num(row.select_one('.margin').text) if row.select_one('.margin') else 0,
                    "prize_money_won": clean_num(row.select_one('.prize').text) if row.select_one('.prize') else 0,
                    "starting_price": clean_num(row.select_one('.odds').text) if row.select_one('.odds') else 0,
                    "stewards_notes": "None",
                    
                    "settling_position": "N/A",
                    "position_800m": "N/A",
                    "position_400m": "N/A",
                    "gear_changes": "None",
                    "total_race_time": "0:00",
                    "sectional_600m": 0.0,
                    "sectional_400m": 0.0,
                    "sectional_200m": 0.0,
                    "sire": "Unknown",
                    "dam": "Unknown",
                    "days_since_last_run": 0
                }
                master_data.append(data_packet)

        # 4. UPLOAD
        if master_data:
            print(f"✅ Success! Found {len(master_data)} VERIFIED horses.")
            print(f"   (Sample: {master_data[0]['finishing_position']} - {master_data[0]['horse_name']})")
            
            auth = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
            # Send in batches
            for i in range(0, len(master_data), 50):
                batch = master_data[i:i+50]
                res = httpx.post(f"{URL}/rest/v1/results", headers=auth, json=batch)
                if res.status_code != 201:
                    print(f"⚠️ Batch Error: {res.status_code}")
        else:
            print("❌ No valid tables found. The site may require a browser (Selenium).")

    except Exception as e:
        print(f"🚨 Error: {e}")

if __name__ == "__main__":
    scrape_strict_validator()
