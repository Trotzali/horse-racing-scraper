import os
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
URL, KEY = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY")

def scrape_full_35_columns():
    target_url = "https://www.punters.com.au/results/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    print("📡 Harvesting 35 Data Points per Runner...")
    
    try:
        response = httpx.get(target_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        master_data = []
        
        # NAVIGATION FILTER: Prevents 'Free Bets' and 'Scores' from entering your DB
        junk_list = ["Free Bets", "Scores", "Racecards", "NEW", "Fast Results", "Tips", "News", "Login"]

        # Loop through each race container
        for race_table in soup.select('.results-table'):
            # --- LEVEL 1: RACE DATA (Top of the Table) ---
            meeting = race_table.select_one('.results-table__header-venue').text.strip()
            # Extracting "Good 4" or "Soft 5"
            track_cond = race_table.select_one('.results-table__header-condition').text.strip()
            # Turning "1200m" into 1200
            dist_raw = race_table.select_one('.results-table__header-distance').text.strip()
            rail = race_table.select_one('.results-table__header-rail').text.strip() if race_table.select_one('.results-table__header-rail') else "True"

            # Loop through individual runner rows
            for row in race_table.select('.results-table__row'):
                horse_name = row.select_one('.results-table__horse-name').text.strip()
                if horse_name in junk_list: continue # Final filter for 'Free Bets'

                # --- THE 35 COLUMN MAPPING CHECKLIST ---
                master_data.append({
                    # 1-6. Identity & Location
                    "meeting_name": meeting,
                    "meeting_date": datetime.now().isoformat(),
                    "race_number": int(race_table.get('data-race-number', 0)),
                    "race_name": race_table.select_one('.results-table__header-name').text.strip(),
                    "track_code": meeting[:4].upper(),
                    "state": "VIC", # Can be extracted from page title or state-specific URL

                    # 7-11. Environmental Data
                    "track_condition": track_cond,
                    "track_rating_num": int(''.join(filter(str.isdigit, track_cond)) or 4), # e.g., GOOD4 -> 4
                    "rail_position": rail,
                    "weather_condition": "Fine", 
                    "race_distance": int(''.join(filter(str.isdigit, dist_raw)) or 0),

                    # 12-18. The Athlete's Profile
                    "horse_name": horse_name,
                    "age": int(row.get('data-age', 0)),
                    "gender": row.get('data-sex', 'U'),
                    "trainer_name": row.select_one('.results-table__trainer').text.strip(),
                    "jockey_name": row.select_one('.results-table__jockey').text.strip(),
                    "weight_carried_kg": float(row.select_one('.results-table__weight').text or 0),
                    "barrier": int(row.select_one('.results-table__barrier').text or 0),

                    # 19-23. Performance Metrics
                    "finishing_position": int(row.select_one('.results-table__pos').text or 0),
                    "margin_lengths": float(row.select_one('.results-table__margin').text or 0),
                    "prize_money_won": float(row.get('data-prize', 0)),
                    "starting_price": float(row.select_one('.results-table__sp').text or 0),
                    "stewards_notes": row.select_one('.results-table__stewards').text.strip() if row.select_one('.results-table__stewards') else "Clear",

                    # 24-27. Race Dynamics (Speed Mapping)
                    "settling_position": row.select_one('.results-table__settle').text.strip() if row.select_one('.results-table__settle') else "N/A",
                    "position_800m": row.select_one('.results-table__800m').text.strip() if row.select_one('.results-table__800m') else "N/A",
                    "position_400m": row.select_one('.results-table__400m').text.strip() if row.select_one('.results-table__400m') else "N/A",
                    "gear_changes": row.select_one('.results-table__gear').text.strip() if row.select_one('.results-table__gear') else "None",

                    # 28-31. Sectional Timing
                    "total_race_time": race_table.select_one('.results-table__time').text.strip(),
                    "sectional_600m": float(row.select_one('.results-table__last-600').text or 0),
                    "sectional_400m": float(row.select_one('.results-table__last-400').text or 0),
                    "sectional_200m": float(row.select_one('.results-table__last-200').text or 0),

                    # 32-35. Pedigree & History
                    "sire": row.get('data-sire', 'Unknown'),
                    "dam": row.get('data-dam', 'Unknown'),
                    "dam_sire": row.get('data-dam-sire', 'Unknown'),
                    "days_since_last_run": int(row.get('data-days-last', 0))
                })

        # Final Delivery to Supabase
        if master_data:
            print(f"✅ Success! Captured {len(master_data)} professional Aussie runners.")
            auth = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
            httpx.post(f"{URL}/rest/v1/results", headers=auth, json=master_data)
        else:
            print("❌ No valid horse data found. Structure may have shifted.")

    except Exception as e:
        print(f"🚨 Master Scraper Error: {e}")

if __name__ == "__main__":
    scrape_full_35_columns()
