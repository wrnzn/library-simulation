python build_notebook.py
python -m jupyter lite build --contents . --output-dir _jupyterlite
cd _jupyterlite
git add .
git commit -m "Deploy v2 to bust cache"
git push -u origin gh-pages --force
