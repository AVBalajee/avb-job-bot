# Telegram Job Link Bot

A simple Python + Telegram bot that gives job-search links based on:
- batch year (example: 2023 batch)
- role choice (Software Engineer, Data Engineer, UI/UX, Hardware Engineer, etc.)
- time window (past 24 hours or past 7 days)
- location

## What this bot does
This bot sends ready-to-open search links for:
- LinkedIn
- Naukri
- Instahyre

## Why link-based instead of scraping?
Direct scraping from job portals is brittle and often breaks because:
- pages change often
- some sites require login/captcha
- anti-bot protections can block requests

So this version is stable and safe for daily use.

## Features
- Telegram inline button UI
- Saved user preferences with SQLite
- Role selection menu
- Batch selection menu
- Time window selection
- Location update using `/location`

## Setup
```bash
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
```

Add your bot token inside `.env`.

## Run
```bash
python bot.py
```

## Commands
- `/start` → open menu
- `/search` → get job links using saved settings
- `/location Bengaluru` → change location
- `/help` → help message

## Example flow
1. Run `/start`
2. Choose batch = 2023
3. Choose role = Software Engineer
4. Choose time = Past 24 hours
5. Click `Search links`

## Notes
- LinkedIn time filtering is encoded in the URL using the `f_TPR` parameter.
- For Naukri and Instahyre, this bot uses safer search-engine fallbacks because direct filter URLs can change frequently.

## Upgrade ideas
- Daily scheduled alerts with APScheduler
- Remote jobs toggle
- Experience level toggle
- CSV export
- SerpAPI / custom search integration for richer result extraction
