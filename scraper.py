import os
import httpx
from dotenv import load_dotenv

load_dotenv()
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")

def scrape_and_save():
    # Targeting the API that contains deeper horse profiles
    target_url = "https://www.sportinglife.com/api/horse-racing/racing/results/today"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    print("Fetching deep data: Age, Trainer, and Going...")
    
    response = httpx.get(target_url, headers=headers)
    data = response.json()
    
    found_horses = []
    
    for race in data.get('races', [])[:5]:
        # Grab race-level data (The Going and Distance)
        going = race.get('going', 'Unknown')
        distance = race.get('distance', 'Unknown')
        
        for runner in race.get('runners', []):
            # Grab horse-level data (Age, Gender, Trainer)
            found_horses.append({
                "horse_name": runner.get('name'),
                "jockey_name": runner.get('jockey_name', 'Unknown'),
                "trainer_name": runner.get('trainer_name', 'Unknown'),
                "age": str(runner.get('age', 'U')),
                "gender": runner.get('sex_code', 'U'),
                "going": going,
                "distance": distance,
                "odds_decimal": 0.0
            })

    if found_horses:
        print(f"✅ Success! Found {len(found_horses)} horses with full profiles.")
        api_url = f"{URL}/rest/v1/results"
        auth_headers = {
            "apikey": KEY,
            "Authorization": f"Bearer {KEY}",
            "Content-Type": "application/json"
        }
        httpx.post(api_url, headers=auth_headers, json=found_horses)

if __name__ == "__main__":
    scrape_and_save()