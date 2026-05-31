import json

# Update requirements.txt
try:
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        reqs = f.read()
    if 'ipywidgets' not in reqs:
        reqs += '\nipywidgets\n'
        with open('requirements.txt', 'w', encoding='utf-8') as f:
            f.write(reqs)
except Exception:
    pass

# Update Jupyter Notebook's piplite command just in case they run it on the web
with open('Library_Simulation_v2.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb.get('cells', []):
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        if "await piplite.install" in source and "ipywidgets" not in source:
            source = source.replace("await piplite.install(['simpy', 'seaborn', 'scipy', 'pandas', 'matplotlib'])",
                                    "await piplite.install(['simpy', 'seaborn', 'scipy', 'pandas', 'matplotlib', 'ipywidgets'])")
            cell['source'] = [line + '\n' for line in source.split('\n')]
            if cell['source']:
                cell['source'][-1] = cell['source'][-1].rstrip('\n')

with open('Library_Simulation_v2.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Dependencies updated!")
