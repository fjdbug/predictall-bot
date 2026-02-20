from googlesearch import search

def test_google():
    query = 'site:x.com "Prediction markets"'
    print(f"Testing Google Search for: {query}")
    try:
        results = search(query, num_results=5, advanced=True)
        count = 0
        for r in results:
            print(f"   - {r.title} ({r.url})")
            print(f"     {r.description}")
            count += 1
        
        if count == 0:
            print("❌ No results.")
        else:
            print(f"✅ Found {count} results.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_google()
