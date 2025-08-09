@echo off
REM FastAPI Launcher Batch Script
REM Usage: serve.bat [command] [options]
REM Examples:
REM   serve.bat dev
REM   serve.bat dev --port 8080
REM   serve.bat prod --workers 4
REM   serve.bat info

uv run python scripts/launcher.py %*
