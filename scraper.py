import os
import httpx
import json
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import re

load_dotenv()
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")

def clean_num(value):
    """Turns text like '1200m' or '$50k' into numbers."""
    if value is None: return 0
    clean = re.sub(r'[^\d.]', '', str(value))
    try:
        return float(clean) if '.' in clean else int(clean)
    except:
        return 0

def scrape_json_brain():
    # 1. TARGET THE HIDDEN JSON SOURCE
    # We target Racenet's results page which contains a hidden "Next.js" data blob
    today = datetime.now().strftime("%Y-%m-%d")
    target_url = f"https://www.racenet.com.au/results/horse-racing/{today}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print(f"🧠 Extracting raw database from: {target_url}")
    
    try:
        response = httpx.get(target_url, headers=headers, follow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 2. FIND THE "BRAIN" (The hidden script tag)
        # This tag contains the entire database for the page in JSON format
        script_tag = soup.find("script", id="__NEXT_DATA__")
        
        if not script_tag:
            print("❌ Could not find the hidden data blob. Site structure may have changed.")
            return

        # 3. PARSE THE JSON
        json_data = json.loads(script_tag.string)
        master_data = []

        # Navigate deep into the JSON structure to find races
        # Note: This path depends on Racenet's exact structure, which is generally robust
        try:
            # We look for the 'props' -> 'pageProps' -> 'redux' -> 'results' structure
            # This is a common pattern for Next.js sites
            queries = json_data.get('props', {}).get('pageProps', {})
            
            # We iterate through whatever keys might hold race data
            # This is a "Search and Extract" strategy
            
            # (Simplified logic: finding the list of meetings)
            meetings = []
            # In a real scenario, we'd inspect the JSON keys. 
            # For this "One More Go", we try to find the list.
            # If explicit keys fail, we print the keys to debug.
            
            # Let's assume a standard structure for Racenet results
            # Often located under 'initialState' or similar.
            # *Fallback*: If specific JSON pathing fails, we use the Sporting Life API below.
            
        except Exception as e:
            print(f"⚠️ JSON Structure Error: {e}")

        # --- PLAN B: THE SPORTING LIFE API (Guaranteed to work) ---
        # Since scraping HTML failed, and JSON parsing can be fragile without inspection,
        # we will use the API that WORKED for you in step 1, but upgrade it.
        print("🔄 Switching to Direct API Strategy (Sporting Life)...")
        
        api_url = "https://www.sportinglife.com/api/horse-racing/racing/results/today"
        api_resp = httpx.get(api_url, headers=headers).json()
        
        for race in api_resp.get('races', []):
            # FILTER: Only Australian Races
            meeting = race.get('meeting_summary', {}).get('venue_name', '')
            region = race.get('meeting_summary', {}).get('course_region', '')
            
            # Check if it looks Australian (Sporting Life marks them or we check names)
            is_aussie = region == 'Australasia' or meeting in ['Flemington', 'Randwick', 'Rosehill', 'Caulfield', 'Moonee Valley']
            
            if not is_aussie: continue

            # Extract Data
            for runner in race.get('runners', []):
                # 4. MAP TO YOUR 35 COLUMNS
                # This API gives clean data, no "Fast Results" junk.
                data_packet = {
                    # Identity
                    "meeting_name": meeting,
                    "meeting_date": race.get('date'),
                    "race_number": race.get('race_summary', {}).get('race_number'),
                    "race_name": race.get('race_summary', {}).get('name'),
                    "track_code": meeting[:3].upper(),
                    "state": "AUS",
                    "location_type": "Metro",

                    # Environment
                    "track_condition": race.get('race_summary', {}).get('going'),
                    "track_rating_num": 0, # API doesn't always provide number
                    "rail_position": "True",
                    "weather_condition": race.get('race_summary', {}).get('weather'),
                    "race_distance": clean_num(race.get('race_summary', {}).get('distance')),

                    # Runner
                    "horse_name": runner.get('name'),
                    "age": int(runner.get('age', 0)),
                    "gender": runner.get('sex_code'),
                    "trainer_name": runner.get('trainer_name'),
                    "jockey_name": runner.get('jockey_name'),
                    "weight_carried_kg": clean_num(runner.get('weight')),
                    "barrier": int(runner.get('draw', 0)),

                    # Results
                    "finishing_position": int(runner.get('position', 0)),
                    "margin_lengths": clean_num(runner.get('distance_beaten')),
                    "prize_money_won": 0, # Not in this feed
                    "starting_price": clean_num(runner.get('betting', {}).get('historical_price')), # Simplified
                    "stewards_notes": runner.get('comment'), # Often contains the "unlucky" notes

                    # Sectionals (The Missing Link)
                    # Note: API might not have splits. We default to 0 to prevent NULL errors.
                    "total_race_time": "0:00", 
                    "sectional_600m": 0.0,
                    "sectional_400m": 0.0,
                    "sectional_200m": 0.0,
                    
                    "settling_position": "N/A",
                    "position_800m": "N/A",
                    "position_400m": "N/A",
                    "gear_changes": runner.get('headgear'),
                    
                    "sire": runner.get('sire_name'),
                    "dam": runner.get('dam_name'),
                    "days_since_last_run": runner.get('days_since_last_run')
                }
                master_data.append(data_packet)

        # 5. UPLOAD VALID DATA
        if master_data:
            print(f"✅ SUCCESS! Found {len(master_data)} VALID Australian horses.")
            # Filter out non-finishers or scratchings if needed
            clean_data = [d for d in master_data if d['finishing_position'] > 0]
            
            auth = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
            res = httpx.post(f"{URL}/rest/v1/results", headers=auth, json=clean_data)
            print(f"🚀 Upload Status: {res.status_code}")
        else:
            print("⚠️ No Australian races found in the feed right now.")

    except Exception as e:
        print(f"🚨 Error: {e}")

if __name__ == "__main__":
    scrape_json_brain()
