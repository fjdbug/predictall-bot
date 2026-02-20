from duckduckgo_search import DDGS

def test_tweets():
    queries = [
        'site:x.com "Prediction markets"',
        'site:twitter.com "Prediction markets"',
        'prediction markets (site:twitter.com OR site:x.com)',
        'prediction markets',
    ]
    
    print("Testing DuckDuckGo Tweet Search...")
    
    for q in queries:
        print(f"\nQUERY: {q}")
        try:
            results = list(DDGS().news(q, max_results=3))
            if results:
                print(f"✅ Found {len(results)} results.")
                for r in results:
                    print(f"   - {r.get('title')} ({r.get('url')})")
            else:
                print("❌ No results.")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_tweets()
