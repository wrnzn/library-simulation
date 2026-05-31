import urllib.request
import json
import urllib.parse

# We want 10 valid IEEE/Academic references from 2020-2025 regarding Discrete Event Simulation, Capacity, Library, SimPy
queries = [
    "discrete event simulation capacity planning",
    "operations research capacity allocation",
    "simpy discrete event simulation",
    "stochastic modeling queueing theory facility"
]

results = []

for q in queries:
    url = f"https://api.openalex.org/works?search={urllib.parse.quote(q)}&filter=publication_year:>2019&per-page=5"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            for work in data.get('results', []):
                title = work.get('title')
                doi = work.get('doi')
                year = work.get('publication_year')
                authors = ", ".join([a['author']['display_name'] for a in work.get('authorships', [])])
                journal = work.get('primary_location', {}).get('source', {}).get('display_name', 'Unknown Journal')
                
                if title and doi and title not in [r['title'] for r in results]:
                    results.append({'title': title, 'authors': authors, 'year': year, 'journal': journal, 'doi': doi})
    except Exception as e:
        print(f"Failed query {q}: {e}")

print("FETCHED REFERENCES:")
for i, r in enumerate(results[:10]):
    print(f"[{i+1}] {r['authors']}, \"{r['title']},\" {r['journal']}, {r['year']}. {r['doi']}")

with open('real_refs.json', 'w', encoding='utf-8') as f:
    json.dump(results[:10], f, indent=2)
