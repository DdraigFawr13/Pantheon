@echo off
rem One-click play. Needs ANTHROPIC_API_KEY=... in a .env file in this folder (D-032).
cd /d "%~dp0"
uv run pantheon play %*
pause
