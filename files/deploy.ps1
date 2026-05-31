git init
git add .
git commit -m "Initial commit"
gh repo create library-simulation --public --source . --remote origin
git push -u origin main
cd _jupyterlite
git init
git add .
git commit -m "Deploy jupyterlite to gh-pages"
git branch -M gh-pages
git remote add origin https://github.com/wrnzn/library-simulation.git
git push -u origin gh-pages --force
