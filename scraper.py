import os
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import httpx
import re

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Australian metro tracks for filtering
METRO_TRACKS = [
    'flemington', 'caulfield', 'moonee valley', 'sandown',  # VIC
    'randwick', 'rosehill', 'canterbury', 'warwick farm',    # NSW
    'eagle farm', 'doomben',                                  # QLD
    'morphettville',                                          # SA
    'ascot', 'belmont',                                       # WA
]

def clean_number(text):
    """Extract number from text like '1200m' or '$50k'"""
    if not text:
        return None
    clean = re.sub(r'[^\d.]', '', str(text))
    try:
        return float(clean) if '.' in clean else int(clean)
    except:
        return None

def parse_margin(margin_text):
    """Convert margin text like '0.5L' or 'Nose' to decimal lengths"""
    if not margin_text or margin_text.upper() in ['', 'N/A', 'NONE']:
        return 0.0
    
    margin_map = {
        'SHORT-HEAD': 0.05,
        'HEAD': 0.1,
        'NOSE': 0.01,
        'NECK': 0.25,
        'SHORT-NECK': 0.15,
    }
    
    upper_text = margin_text.upper()
    for key, val in margin_map.items():
        if key in upper_text:
            return val
    
    # Try to extract decimal number
    num = clean_number(margin_text)
    return num if num else 0.0

async def scrape_racenet_with_browser():
    """
    Use Playwright to render JavaScript and scrape actual race results.
    This solves the 'Fast Results' menu problem.
    """
    today = "2026-02-11"  # Testing with yesterday's date
    target_url = f"https://www.racenet.com.au/results/horse-racing/{today}"
    
    print(f"🎯 Target: {target_url}")
    print("🌐 Launching headless browser (this renders JavaScript)...")
    
    all_results = []
    
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        try:
            # Navigate to results page
            await page.goto(target_url, wait_until='networkidle', timeout=60000)
            
            # Wait for the results to load (key: wait for ACTUAL content, not menu)
            print("⏳ Waiting for race results to load...")
            
            # Try multiple possible selectors for race cards
            await page.wait_for_timeout(3000)  # Give JS time to render
            
            # Find all race containers
            races = await page.query_selector_all('.race-card, .racecard, [class*="Race"]')
            
            if not races:
                print("⚠️ No race cards found. Trying alternative approach...")
                # Sometimes Racenet loads data differently
                # Let's extract from the __NEXT_DATA__ script tag instead
                script_content = await page.inner_text('script#__NEXT_DATA__')
                
                if script_content:
                    print("✅ Found __NEXT_DATA__ - will parse JSON instead")
                    import json
                    data = json.loads(script_content)
                    # Navigate the JSON structure to find races
                    # This part depends on their exact structure
                    # For now, we'll use the direct API approach below
                else:
                    print("❌ Could not find race data on page")
                    await browser.close()
                    return []
            
            print(f"📋 Found {len(races)} race containers")
            
            # For each race, extract the results table
            for race_idx, race_elem in enumerate(races, 1):
                print(f"\n🏇 Processing Race {race_idx}...")
                
                # Get race metadata
                race_name = await race_elem.inner_text('h3, h2, .race-name') if await race_elem.query_selector('h3, h2, .race-name') else f"Race {race_idx}"
                
                # Find the results table within this race
                table = await race_elem.query_selector('table.results-table, table')
                
                if not table:
                    print(f"   ⚠️ No results table found for {race_name}")
                    continue
                
                # Extract all rows
                rows = await table.query_selector_all('tbody tr')
                
                for row in rows:
                    cells = await row.query_selector_all('td')
                    
                    if len(cells) < 3:  # Skip invalid rows
                        continue
                    
                    # Extract cell text
                    cell_texts = []
                    for cell in cells:
                        text = await cell.inner_text()
                        cell_texts.append(text.strip())
                    
                    # Skip if first cell is not a number (this filters out "Fast Results")
                    if not cell_texts[0].isdigit():
                        continue
                    
                    # Build result dict
                    # Column mapping depends on exact table structure
                    # Typical order: Position, Horse, Jockey, Trainer, etc.
                    result = {
                        'meeting_name': 'Unknown',  # Will need to extract from page
                        'meeting_date': datetime.now().isoformat(),
                        'race_number': race_idx,
                        'race_name': race_name,
                        'track_code': 'UNK',
                        'state': 'AUS',
                        'location_type': 'Metro',
                        
                        'track_condition': None,
                        'track_rating_num': None,
                        'rail_position': None,
                        'weather_condition': None,
                        'race_distance': None,
                        
                        'horse_name': cell_texts[1] if len(cell_texts) > 1 else None,
                        'age': None,
                        'gender': None,
                        'trainer_name': cell_texts[3] if len(cell_texts) > 3 else None,
                        'jockey_name': cell_texts[2] if len(cell_texts) > 2 else None,
                        'weight_carried_kg': None,
                        'barrier': None,
                        
                        'finishing_position': int(cell_texts[0]) if cell_texts[0].isdigit() else None,
                        'margin_lengths': parse_margin(cell_texts[4]) if len(cell_texts) > 4 else 0.0,
                        'prize_money_won': None,
                        'starting_price': None,
                        'stewards_notes': None,
                        
                        'settling_position': None,
                        'position_800m': None,
                        'position_400m': None,
                        'gear_changes': None,
                        
                        'total_race_time': None,
                        'sectional_600m': None,
                        'sectional_400m': None,
                        'sectional_200m': None,
                        
                        'sire': None,
                        'dam': None,
                        'days_since_last_run': None,
                    }
                    
                    all_results.append(result)
                    print(f"   ✅ {result['finishing_position']}. {result['horse_name']}")
            
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
        
        finally:
            await browser.close()
    
    return all_results

async def scrape_alternative_api():
    """
    Fallback: Use a working Australian racing API
    Since Racenet's structure is complex, we'll use Tab.com.au's public API
    """
    print("\n🔄 Using Alternative API (Tab.com.au)...")
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Tab.com.au has a public results API
    api_url = f"https://api.tab.com.au/v1/tab-info-service/racing/dates/{today}/meetings?jurisdiction=NSW"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    results = []
    
    try:
        response = httpx.get(api_url, headers=headers, timeout=30)
        data = response.json()
        
        meetings = data.get('meetings', [])
        
        for meeting in meetings:
            venue = meeting.get('meetingName', '')
            
            # Filter to metro tracks only
            if not any(metro in venue.lower() for metro in METRO_TRACKS):
                continue
            
            print(f"\n🏟️  {venue}")
            
            races = meeting.get('races', [])
            
            for race in races:
                race_num = race.get('raceNumber')
                race_name = race.get('raceName', '')
                
                runners = race.get('runners', [])
                
                for runner in runners:
                    if runner.get('resultedPlace'):  # Only finishers
                        result = {
                            'meeting_name': venue,
                            'meeting_date': today,
                            'race_number': race_num,
                            'race_name': race_name,
                            'track_code': venue[:4].upper(),
                            'state': meeting.get('location', 'AUS'),
                            'location_type': 'Metro',
                            
                            'track_condition': race.get('trackCondition'),
                            'track_rating_num': clean_number(race.get('trackCondition')),
                            'rail_position': race.get('railPosition'),
                            'weather_condition': race.get('weatherCondition'),
                            'race_distance': clean_number(race.get('raceDistance')),
                            
                            'horse_name': runner.get('runnerName'),
                            'age': runner.get('age'),
                            'gender': runner.get('sex'),
                            'trainer_name': runner.get('trainerName'),
                            'jockey_name': runner.get('jockeyName'),
                            'weight_carried_kg': runner.get('handicapWeight'),
                            'barrier': runner.get('barrierNumber'),
                            
                            'finishing_position': runner.get('resultedPlace'),
                            'margin_lengths': parse_margin(runner.get('margin')),
                            'prize_money_won': runner.get('prizeMoney'),
                            'starting_price': runner.get('winFixedOdds'),
                            'stewards_notes': runner.get('comment'),
                            
                            'settling_position': None,
                            'position_800m': None,
                            'position_400m': None,
                            'gear_changes': runner.get('gear'),
                            
                            'total_race_time': runner.get('time'),
                            'sectional_600m': None,
                            'sectional_400m': None,
                            'sectional_200m': None,
                            
                            'sire': runner.get('sire'),
                            'dam': runner.get('dam'),
                            'days_since_last_run': None,
                        }
                        
                        results.append(result)
                        print(f"   {result['finishing_position']}. {result['horse_name']}")
        
        return results
    
    except Exception as e:
        print(f"❌ API Error: {e}")
        return []

async def upload_to_supabase(results):
    """Upload results to Supabase"""
    if not results:
        print("\n⚠️ No results to upload")
        return
    
    print(f"\n📤 Uploading {len(results)} results to Supabase...")
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    url = f"{SUPABASE_URL}/rest/v1/results"
    
    try:
        response = httpx.post(url, headers=headers, json=results, timeout=30)
        
        if response.status_code in [200, 201]:
            print(f"✅ SUCCESS! {len(results)} results uploaded")
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"Response: {response.text}")
    
    except Exception as e:
        print(f"❌ Upload error: {e}")

async def main():
    """Main execution"""
    print("🏇 Australian Racing Scraper v2.0")
    print("=" * 50)
    
    # Try Playwright first
    results = await scrape_racenet_with_browser()
    
    # If Playwright fails or returns empty, use API fallback
    if not results:
        print("\n🔄 Playwright returned no results, trying API...")
        results = await scrape_alternative_api()
    
    # Upload to database
    if results:
        await upload_to_supabase(results)
    else:
        print("\n❌ No results found from any source")

if __name__ == "__main__":
    asyncio.run(main())
