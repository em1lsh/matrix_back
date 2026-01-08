@echo off
cd /d "%~dp0.."
call env\Scripts\activate
python scripts/set_webhook.py %*
