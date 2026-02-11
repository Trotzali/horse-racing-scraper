import os
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import re

load_dotenv()
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")

# --- HELPER FUNCTIONS TO CLEAN DATA ---
def clean_money(text):
    if not text: return 0.0
    # Removes '$' and ',' to turn '$23,000' into 23000.0
    clean = re.sub(r'[^\d.]', '', text)
    return float(clean) if clean else 0.0

def clean_dist(text):
    if not text: return 0
    # Turns '1200m' into 1200
    clean = re.sub(r'[^\d]', '', text)
    return int(clean) if clean else 0

def get_text_safe(row, selector):
    el = row.select_one(selector)
    return el.text.strip() if el else None

def scrape_nuclear_option():
    # We use a date-specific URL to ensure we get a full table, not a summary page
    today = datetime.now().strftime("%Y-%m-%d")
    target_url = f"https://www.punters.com.au/results/{today}/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }
    
    print(f"📡 Hitting {target_url} with 'Nuclear' strict mode...")
    
    try:
        response = httpx.get(target_url, headers=headers, follow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        master_data = []
        
        # 1. FIND THE RACE TABLES
        # We look for tables that explicitly have 'results-table' in the class
        race_tables = soup.select('table.results-table')
        
        if not race_tables:
            print("⚠️ No race tables found. The site structure might be blocking bots or no races today.")
            return

        for table in race_tables:
            # --- RACE LEVEL METADATA ---
            # We assume the header is immediately preceding the table or part of a container
            container = table.find_parent('div', class_='results-table-container') or table
            
            # Robust lookups for race info
            meeting = container.get('data-venue', 'Unknown Venue')
            track_cond = get_text_safe(container, '.track-condition') or "Good 4"
            dist_text = get_text_safe(container, '.race-distance') or "0m"
            
            # 2. FIND THE HORSE ROWS
            # We iterate through TRs, but we ONLY process them if they have a 'data-competitor-id'
            # This instantly filters out "Free Bets", "Fast Results", and "News"
            rows = table.find_all('tr')
            
            for row in rows:
                # THE MAGICAL FILTER: If it doesn't have a horse ID, it's garbage.
                # Punters.com usually puts data-competitor-id on the row or a child.
                # If that fails, we check if it has a "Barrier" cell.
                is_real_horse = row.select_one('.barrier') or row.get('data-competitor-id')
                
                if not is_real_horse:
                    continue # Skip menu links, headers, and ads
                
                # --- EXTRACTION ---
                # We define all 35 columns. If a selector fails, it defaults to a safe value (0 or "N/A").
                
                horse_name = get_text_safe(row, '.horse-name a') or get_text_safe(row, '.horse-name')
                if not horse_name: continue # Double check

                data_packet = {
                    # --- IDENTITY ---
                    "meeting_name": meeting,
                    "meeting_date": datetime.now().isoformat(),
                    "race_number": int(container.get('data-race-number', 0)),
                    "race_name": get_text_safe(container, '.race-name') or "Race",
                    "track_code": meeting[:4].upper(),
                    "state": "VIC", # Placeholder, requires logic map
                    "location_type": "Metropolitan",
                    
                    # --- ENVIRONMENTAL ---
                    "track_condition": track_cond,
                    "track_rating_num": int(clean_dist(track_cond)) if clean_dist(track_cond) > 0 else 4,
                    "rail_position": "True", # Often not on summary page
                    "weather_condition": "Fine",
                    "race_distance": clean_dist(dist_text),
                    
                    # --- PROFILE ---
                    "horse_name": horse_name,
                    "age": 0, # Often hidden in detail page, setting 0 to prevent NULL
                    "gender": "U",
                    "trainer_name": get_text_safe(row, '.trainer') or "Unknown",
                    "jockey_name": get_text_safe(row, '.jockey') or "Unknown",
                    "weight_carried_kg": clean_money(get_text_safe(row, '.weight')),
                    "barrier": int(clean_dist(get_text_safe(row, '.barrier'))),
                    
                    # --- PERFORMANCE ---
                    "finishing_position": int(clean_dist(get_text_safe(row, '.position'))) or 0,
                    "margin_lengths": clean_money(get_text_safe(row, '.margin')),
                    "prize_money_won": clean_money(row.get('data-prize')), # Often in data attr
                    "starting_price": clean_money(get_text_safe(row, '.odds')),
                    "stewards_notes": "None", # Requires deep scrape
                    
                    # --- DYNAMICS ---
                    "settling_position": "N/A", # Requires deep scrape
                    "position_800m": "N/A",
                    "position_400m": "N/A",
                    "gear_changes": "None",
                    
                    # --- SECTIONALS ---
                    "total_race_time": get_text_safe(row, '.time') or "0:00",
                    "sectional_600m": clean_money(get_text_safe(row, '.sectional')),
                    "sectional_400m": 0.0,
                    "sectional_200m": 0.0,
                    
                    # --- PEDIGREE ---
                    "sire": "Unknown",
                    "dam": "Unknown",
                    "dam_sire": "Unknown",
                    "days_since_last_run": 0
                }
                
                master_data.append(data_packet)

        # 3. UPLOAD
        if master_data:
            print(f"✅ Success! Found {len(master_data)} VALID horses (No junk links).")
            # print(master_data[0]) # Uncomment to debug first row
            
            auth_headers = {
                "apikey": KEY,
                "Authorization": f"Bearer {KEY}",
                "Content-Type": "application/json"
            }
            res = httpx.post(f"{URL}/rest/v1/results", headers=auth_headers, json=master_data)
            if res.status_code in [200, 201]:
                print("🚀 Database updated successfully.")
            else:
                print(f"❌ Database Error: {res.status_code} - {res.text}")
        else:
            print("❌ No data found. Debug: Check if site is loading via JavaScript.")

    except Exception as e:
        print(f"🚨 Critical Error: {e}")

if __name__ == "__main__":
    scrape_nuclear_option()
