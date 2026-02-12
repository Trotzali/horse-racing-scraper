"""
Quick Setup Verification Script
Run this to test if everything is configured correctly
"""

import os
import sys
from dotenv import load_dotenv

def check_environment():
    """Check if .env file and credentials exist"""
    print("🔍 Checking environment setup...")
    
    load_dotenv()
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url:
        print("❌ SUPABASE_URL not found in .env file")
        return False
    
    if not key:
        print("❌ SUPABASE_KEY not found in .env file")
        return False
    
    print(f"✅ Supabase URL: {url}")
    print(f"✅ Supabase Key: {key[:20]}...")
    return True

def check_playwright():
    """Check if Playwright is installed"""
    print("\n🔍 Checking Playwright installation...")
    
    try:
        from playwright.sync_api import sync_playwright
        print("✅ Playwright package installed")
        
        # Try to launch browser
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                print("✅ Chromium browser installed")
                browser.close()
            return True
        except Exception as e:
            print(f"❌ Chromium not installed: {e}")
            print("\n💡 Fix: Run 'playwright install chromium'")
            return False
            
    except ImportError:
        print("❌ Playwright not installed")
        print("\n💡 Fix: Run 'pip install playwright'")
        return False

def check_supabase_connection():
    """Test connection to Supabase"""
    print("\n🔍 Testing Supabase connection...")
    
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ Missing credentials")
        return False
    
    try:
        import httpx
        
        api_url = f"{url}/rest/v1/results?limit=1"
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}"
        }
        
        response = httpx.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("✅ Successfully connected to Supabase")
            
            data = response.json()
            print(f"   📊 Current rows in database: {len(data)}")
            return True
        else:
            print(f"❌ Connection failed: {response.status_code}")
            print(f"   {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_table_schema():
    """Check if the results table has the correct schema"""
    print("\n🔍 Checking database schema...")
    
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    try:
        import httpx
        
        # Try to insert a test row
        api_url = f"{url}/rest/v1/results"
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        test_data = {
            "meeting_name": "TEST",
            "horse_name": "Test Horse",
            "finishing_position": 1
        }
        
        response = httpx.post(api_url, headers=headers, json=test_data, timeout=10)
        
        if response.status_code in [200, 201]:
            print("✅ Table schema looks good")
            
            # Clean up test data
            delete_url = f"{url}/rest/v1/results?horse_name=eq.Test Horse"
            httpx.delete(delete_url, headers=headers)
            
            return True
        else:
            print(f"❌ Schema issue: {response.status_code}")
            print(f"   {response.text}")
            print("\n💡 Fix: Run the SQL in supabase_schema.sql")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("🏇 AUSTRALIAN RACING SCRAPER - SETUP VERIFICATION")
    print("=" * 60)
    
    checks = [
        ("Environment", check_environment),
        ("Playwright", check_playwright),
        ("Supabase Connection", check_supabase_connection),
        ("Table Schema", check_table_schema)
    ]
    
    results = {}
    
    for name, check_func in checks:
        results[name] = check_func()
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
        if not passed:
            all_passed = False
    
    print("\n")
    
    if all_passed:
        print("🎉 ALL CHECKS PASSED! You're ready to run scraper.py")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
