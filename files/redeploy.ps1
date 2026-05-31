python build_notebook.py
python -m jupyter lite build --contents Library_Simulation.ipynb --output-dir _jupyterlite
cd _jupyterlite
git add .
git commit -m "Fix Pyodide dependencies"
git push -u origin gh-pages --force
