import os
import httpx
from dotenv import load_dotenv

# 1. Load your keys from the .env file
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

def test_connection():
    # Construct the direct link to your 'results' table
    api_url = f"{url}/rest/v1/results"
    
    # These are your security badges
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    # The horse we are testing with
    new_horse = {
        "horse_name": "Direct Test Horse",
        "jockey_name": "No-Error Jockey",
        "odds_decimal": 5.0
    }

    print("Connecting to Supabase pantry...")
    
    # Send the data directly
    with httpx.Client() as client:
        response = client.post(api_url, headers=headers, json=new_horse)
        
    if response.status_code == 201 or response.status_code == 200:
        print("🎉 SUCCESS! 'Direct Test Horse' is now in your database.")
    else:
        print(f"❌ FAILED. Error code: {response.status_code}")
        print(f"Message: {response.text}")

if __name__ == "__main__":
    test_connection()