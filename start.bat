@echo off
rem One-click play. Runs a private Ollama with the larger context (D-027, D-030); your normal Ollama is untouched.
cd /d "%~dp0"
set OLLAMA_HOST=127.0.0.1:11435
set OLLAMA_CONTEXT_LENGTH=32768
curl -s -o nul http://127.0.0.1:11435/api/version
if errorlevel 1 start "Pantheon Ollama" /min ollama serve
uv run pantheon play %*
