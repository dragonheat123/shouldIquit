#!/usr/bin/env python3
"""
Test script to debug Tavily API LinkedIn profile fetching
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def test_tavily_linkedin(profile_url: str):
    """Test Tavily API with a LinkedIn profile URL"""
    api_key = os.getenv("TAVILY_API_KEY")
    
    if not api_key:
        print("❌ No TAVILY_API_KEY found in .env file")
        return
    
    print(f"🔍 Testing Tavily API with: {profile_url}")
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    
    username = profile_url.split("/in/")[-1].strip("/").split("?")[0]
    print(f"Extracted username: {username}")
    
    # Construct search query
    search_query = f"{profile_url} OR site:linkedin.com/in/{username}"
    print(f"\nSearch query: {search_query}")
    
    # Make Tavily API request
    try:
        print("\n📡 Sending request to Tavily API...")
        res = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": search_query,
                "max_results": 5,
                "include_answer": True,
                "include_raw_content": True,
                "search_depth": "advanced",
            },
            timeout=20,
        )
        
        print(f"Response status: {res.status_code}")
        
        if res.status_code != 200:
            print(f"❌ API Error: {res.text}")
            return
        
        data = res.json()
        
        # Save full response for inspection
        with open("tavily_response.json", "w") as f:
            json.dump(data, f, indent=2)
        print("\n✅ Full response saved to: tavily_response.json")
        
        # Display summary
        print("\n" + "="*60)
        print("TAVILY RESPONSE SUMMARY")
        print("="*60)
        
        answer = data.get("answer", "")
        if answer:
            print(f"\n📝 Answer:\n{answer}\n")
        
        results = data.get("results", [])
        print(f"\n📊 Found {len(results)} results:\n")
        
        for i, result in enumerate(results, 1):
            print(f"\n--- Result {i} ---")
            print(f"Title: {result.get('title', 'N/A')}")
            print(f"URL: {result.get('url', 'N/A')}")
            print(f"Content preview: {result.get('content', '')[:200]}...")
            
            if result.get('raw_content'):
                print(f"Raw content length: {len(result.get('raw_content', ''))} chars")
        
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Test with the Clement Lork profile
    test_url = "https://www.linkedin.com/in/clement-lork/"
    
    print("="*60)
    print("TAVILY LINKEDIN PROFILE TESTER")
    print("="*60)
    print()
    
    test_tavily_linkedin(test_url)
    
    print("\n✅ Test complete!")
    print("Check 'tavily_response.json' for full API response")
