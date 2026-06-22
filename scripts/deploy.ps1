# deploy.sh (หรือ deploy.ps1 บน Windows)
uv export --no-hashes --no-emit-project --format requirements-txt > requirements.txt
(Get-Content requirements.txt) | Where-Object { $_ -notmatch "gradio" } | Set-Content requirements.txt
git add .
git commit -m "deploy update"
git push space main