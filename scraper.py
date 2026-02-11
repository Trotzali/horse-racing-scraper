import os
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")

def scrape_and_save():
    target_url = "https://www.sportinglife.com/racing/results"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    print(f"Searching for ACTUAL horses at {target_url}...")
    
    response = httpx.get(target_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    found_horses = []
    # This specifically targets the 'HorseName' links inside the results container
    # It also ignores common menu items
    junk_words = ["Free Bets", "Racecards", "Fast Results", "Scores", "NEW", "Log In"]
    
    for horse in soup.find_all('a'):
        name = horse.text.strip()
        # Look for the specific Sporting Life CSS class for horse names
        is_horse_class = any("HorseName" in cls for cls in horse.get("class", []))
        
        if is_horse_class and name not in junk_words:
            found_horses.append({
                "horse_name": name,
                "jockey_name": "Pro Scraper",
                "odds_decimal": 0.0
            })

    # Limit to 10 real horses for this test
    found_horses = found_horses[:10]

    api_url = f"{URL}/rest/v1/results"
    auth_headers = {
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json"
    }

    if found_horses:
        print(f"Success! Found {len(found_horses)} real horses. Sending to database...")
        httpx.post(api_url, headers=auth_headers, json=found_horses)
    else:
        print("Still couldn't find real horse names. Website layout might have changed.")
    
    # 2. THE GRAB: Fetching the website content
    response = httpx.get(target_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
  # 3. THE LOGIC: Finding ACTUAL horse names
    found_horses = []
    
    # This specifically looks for the horse name links on Sporting Life
    # We look for <a> tags that have 'HorseName' in their class
    for horse in soup.find_all('a', class_='HorseName-sc-16u6769-0'):
        name = horse.text.strip()
        if name:
            found_horses.append({
                "horse_name": name,
                "jockey_name": "Pro Scraper",
                "odds_decimal": 0.0 # We can add odds logic next!
            })
    
    # If the class above changed, this is a backup for generic racing sites:
    if not found_horses:
        for horse in soup.select('.horse-name, .hr-racing-runner-name'):
            found_horses.append({
                "horse_name": horse.text.strip(),
                "jockey_name": "Backup Scraper",
                "odds_decimal": 0.0
            })

    # 4. THE SAVE: Sending them to your Supabase Pantry
    api_url = f"{URL}/rest/v1/results"
    auth_headers = {
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json"
    }

    if found_horses:
        print(f"Found {len(found_horses)} horses! Sending to database...")
        res = httpx.post(api_url, headers=auth_headers, json=found_horses)
        if res.status_code in [200, 201]:
            print("🚀 SUCCESS! Real horses have been added to your database.")
    else:
        print("Couldn't find any horses. The website layout might have changed.")

if __name__ == "__main__":
    scrape_and_save()