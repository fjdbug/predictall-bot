from duckduckgo_search import DDGS

def test_search():
    topic = "python"
    print(f"Testing search for: {topic}")
    try:
        results = list(DDGS().news(topic, max_results=5))
        if results:
            print(f"✅ Found {len(results)} results:")
            for res in results:
                print(f"- {res.get('title')} ({res.get('url')})")
        else:
            print("❌ No results found with .news().")
            
        print("Testing .text() method...")
        results_text = list(DDGS().text(topic, max_results=5))
        if results_text:
             print(f"✅ Found {len(results_text)} text results.")
        else:
             print("❌ No results with .text().")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_search()
