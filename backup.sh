
source ../bin/activate
pip freeze > requirements.txt

git add -A
git commit -m "Backup op $(date '+%Y-%m-%d %H:%M:%S')"
git push
