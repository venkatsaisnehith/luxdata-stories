import httpx
import json
import time

try:
    for attempt in range(5):
        stats = httpx.get('http://localhost:8000/api/stats').json()
        if stats['total_stories'] > 0:
            print(f'Stats: {json.dumps(stats, indent=2)}')
            stories = httpx.get('http://localhost:8000/api/stories?limit=3').json()
            print(f'\nStories count: {len(stories)}')
            for s in stories:
                print(f'\n--- [{s["topic"].upper()}] {s["title"]}')
                print(f'    {s["body"][:200]}...')
            break
        else:
            print("No stories yet, waiting 5 seconds...")
            time.sleep(5)
except Exception as e:
    print(f"Error: {e}")
