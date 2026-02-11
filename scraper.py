import os
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
URL, KEY = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY")

def scrape_35_columns():
    target_url = "https://www.punters.com.au/results/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    print("📡 Initializing 35-Column Australian Data Harvest...")
    
    try:
        response = httpx.get(target_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        master_data = []
        
        # JUNK FILTER: Keeps the 'Free Bets' and 'Scores' out of your 35 columns
        junk_list = ["Free Bets", "Scores", "Racecards", "NEW", "Fast Results", "Tips", "News"]

        for race_table in soup.select('.results-table'):
            # --- RACE LEVEL DATA (Environmental & Identity) ---
            meeting_name = race_table.select_one('.results-table__header-venue').text.strip()
            track_condition = race_table.select_one('.results-table__header-condition').text.strip()
            distance_raw = race_table.select_one('.results-table__header-distance').text.strip()
            rail_pos = race_table.select_one('.results-table__header-rail').text.strip() if race_table.select_one('.results-table__header-rail') else "True"

            for row in race_table.select('.results-table__row'):
                horse_name = row.select_one('.results-table__horse-name').text.strip()
                if horse_name in junk_list: continue

                # --- THE 35 COLUMN MAPPING ---
                master_data.append({
                    # 1. Identity & Location
                    "meeting_name": meeting_name,
                    "meeting_date": datetime.now().isoformat(),
                    "race_number": int(race_table.get('data-race-number', 0)),
                    "race_name": race_table.select_one('.results-table__header-name').text.strip(),
                    "track_code": meeting_name[:4].upper(),
                    "state": "VIC", # Placeholder: Logic to extract state (VIC/NSW/QLD)
                    "location_type": "Metropolitan", 

                    # 2. Environmental
                    "track_condition": track_condition,
                    "weather_condition": "Fine", # Requires additional weather API/Scrape
                    "race_distance": int(''.join(filter(str.isdigit, distance_raw)) or 0),
                    "rail_position": rail_pos,

                    # 3. Runner Profile
                    "horse_name": horse_name,
                    "age": int(row.get('data-age', 0)),
                    "gender": row.get('data-sex', 'U'),
                    "trainer_name": row.select_one('.results-table__trainer').text.strip(),
                    "jockey_name": row.select_one('.results-table__jockey').text.strip(),
                    "weight_carried_kg": float(row.select_one('.results-table__weight').text or 0),
                    "barrier": int(row.select_one('.results-table__barrier').text or 0),

                    # 4. Results & Performance
                    "finishing_position": int(row.select_one('.results-table__pos').text or 0),
                    "margin_lengths": float(row.select_one('.results-table__margin').text or 0),
                    "prize_money_won": float(row.get('data-prize', 0)),
                    "starting_price": float(row.select_one('.results-table__sp').text or 0),
                    "stewards_notes": row.select_one('.results-table__stewards').text.strip() if row.select_one('.results-table__stewards') else "Clear",

                    # 5. Speed Mapping (In-Running Positions)
                    "settling_position": row.select_one('.results-table__settle').text.strip(),
                    "position_800m": row.select_one('.results-table__800m').text.strip(),
                    "position_400m": row.select_one('.results-table__400m').text.strip(),
                    "gear_changes": row.select_one('.results-table__gear').text.strip() if row.select_one('.results-table__gear') else "No Change",

                    # 6. Elite Sectionals (200m Increments)
                    "race_time_total": race_table.select_one('.results-table__time').text.strip(),
                    "sectional_600m": float(row.select_one('.results-table__last-600').text or 0),
                    "sectional_400m": float(row.select_one('.results-table__last-400').text or 0),
                    "sectional_200m": float(row.select_one('.results-table__last-200').text or 0),

                    # 7. Pedigree & History
                    "sire": row.get('data-sire', 'Unknown'),
                    "dam": row.get('data-dam', 'Unknown'),
                    "dam_sire": row.get('data-dam-sire', 'Unknown'),
                    "days_since_last_run": int(row.get('data-days-last', 0))
                })

        if master_data:
            auth = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
            httpx.post(f"{URL}/rest/v1/results", headers=auth, json=master_data)
            print(f"🚀 35-Column Data Sync Complete: {len(master_data)} runners added.")

    except Exception as e:
        print(f"🚨 Master Scraper Error: {e}")

if __name__ == "__main__":
    scrape_35_columns()
