import logging
import os
import sqlite3
from dataclasses import dataclass
from typing import Dict, List
from urllib.parse import quote_plus

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "jobbot.db")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION", "India")

BATCHES = ["2026", "2025", "2024", "2023", "2022", "2021"]
TIMEFRAMES = {
    "24h": "Past 24 hours",
    "7d": "Past 7 days",
}

ROLES = {
    "software_engineer": "Software Engineer",
    "data_engineer": "Data Engineer",
    "ui_ux": "UI/UX Designer",
    "hardware_engineer": "Hardware Engineer",
    "backend_engineer": "Backend Engineer",
    "frontend_engineer": "Frontend Engineer",
    "qa_engineer": "QA Engineer",
    "devops_engineer": "DevOps Engineer",
    "data_analyst": "Data Analyst",
    "business_analyst": "Business Analyst",
}


@dataclass
class UserPrefs:
    batch: str = "2023"
    role_key: str = "software_engineer"
    timeframe: str = "24h"
    location: str = DEFAULT_LOCATION


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_prefs (
            user_id INTEGER PRIMARY KEY,
            batch TEXT NOT NULL,
            role_key TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            location TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def get_prefs(user_id: int) -> UserPrefs:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT batch, role_key, timeframe, location FROM user_prefs WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row:
        return UserPrefs(*row)
    return UserPrefs()


def save_prefs(user_id: int, prefs: UserPrefs) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_prefs(user_id, batch, role_key, timeframe, location)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            batch = excluded.batch,
            role_key = excluded.role_key,
            timeframe = excluded.timeframe,
            location = excluded.location
        """,
        (user_id, prefs.batch, prefs.role_key, prefs.timeframe, prefs.location),
    )
    conn.commit()
    conn.close()


def google_site_fallback(site: str, query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(f'site:{site} {query}')}"


def linkedin_url(query: str, location: str, timeframe: str) -> str:
    seconds = 86400 if timeframe == "24h" else 604800
    return (
        "https://www.linkedin.com/jobs/search/?"
        f"keywords={quote_plus(query)}&location={quote_plus(location)}"
        f"&f_TPR=r{seconds}&sortBy=DD"
    )


def naukri_url(query: str, location: str, timeframe: str) -> str:
    human_window = "last 24 hours" if timeframe == "24h" else "last 7 days"
    return google_site_fallback("naukri.com", f"{query} {location} {human_window}")


def instahyre_url(query: str, location: str, timeframe: str) -> str:
    human_window = "last 24 hours" if timeframe == "24h" else "last 7 days"
    return google_site_fallback("instahyre.com", f"{query} {location} {human_window}")


def build_links(prefs: UserPrefs) -> Dict[str, str]:
    role_label = ROLES[prefs.role_key]
    query = f"{role_label} {prefs.batch} batch fresher entry level 0-2 years"

    return {
        "LinkedIn": linkedin_url(query, prefs.location, prefs.timeframe),
        "Naukri": naukri_url(query, prefs.location, prefs.timeframe),
        "Instahyre": instahyre_url(query, prefs.location, prefs.timeframe),
    }


def main_menu(prefs: UserPrefs) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(f"Batch: {prefs.batch}", callback_data="menu_batch")],
        [InlineKeyboardButton(f"Role: {ROLES[prefs.role_key]}", callback_data="menu_role")],
        [InlineKeyboardButton(f"Time: {TIMEFRAMES[prefs.timeframe]}", callback_data="menu_time")],
        [InlineKeyboardButton(f"Search links ({prefs.location})", callback_data="search_now")],
        [InlineKeyboardButton("Help", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)


def batch_menu() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(batch, callback_data=f"batch:{batch}")] for batch in BATCHES]
    buttons.append([InlineKeyboardButton("⬅ Back", callback_data="home")])
    return InlineKeyboardMarkup(buttons)


def role_menu() -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for key, label in ROLES.items():
        rows.append([InlineKeyboardButton(label, callback_data=f"role:{key}")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)


def timeframe_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("Past 24 hours", callback_data="time:24h")],
        [InlineKeyboardButton("Past 7 days", callback_data="time:7d")],
        [InlineKeyboardButton("⬅ Back", callback_data="home")],
    ]
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    prefs = get_prefs(user.id)

    text = (
        "🚀 *Job Link Bot*\n\n"
        "Choose your *batch*, *role*, and *time window*.\n"
        "Then tap *Search links* and I’ll send buttons for LinkedIn, Naukri, and Instahyre.\n\n"
        f"*Current settings*\n"
        f"• Batch: *{prefs.batch}*\n"
        f"• Role: *{ROLES[prefs.role_key]}*\n"
        f"• Time: *{TIMEFRAMES[prefs.timeframe]}*\n"
        f"• Location: *{prefs.location}*"
    )

    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=main_menu(prefs),
            parse_mode=ParseMode.MARKDOWN,
        )


async def set_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    prefs = get_prefs(user.id)

    if not context.args:
        await update.message.reply_text(
            "Usage:\n/location Bengaluru\n/location Chennai\n/location India"
        )
        return

    prefs.location = " ".join(context.args).strip()
    save_prefs(user.id, prefs)
    await update.message.reply_text(f"✅ Location updated to: {prefs.location}")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    prefs = get_prefs(user.id)
    await send_links(update, context, prefs)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "*Commands*\n"
        "/start - open main menu\n"
        "/search - get job links with saved preferences\n"
        "/location <city/country> - set location\n"
        "/help - show help\n\n"
        "*Example*\n"
        "`/location Bengaluru`\n\n"
        "*Note*\n"
        "Naukri and Instahyre may open in browser depending on Telegram/mobile app behavior."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


def job_link_buttons(links: Dict[str, str]) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔗 Open LinkedIn", url=links["LinkedIn"])],
        [InlineKeyboardButton("🔗 Open Naukri", url=links["Naukri"])],
        [InlineKeyboardButton("🔗 Open Instahyre", url=links["Instahyre"])],
        [
            InlineKeyboardButton("Change Batch", callback_data="menu_batch"),
            InlineKeyboardButton("Change Role", callback_data="menu_role"),
        ],
        [
            InlineKeyboardButton("Change Time", callback_data="menu_time"),
            InlineKeyboardButton("Home", callback_data="home"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def send_links(update: Update, context: ContextTypes.DEFAULT_TYPE, prefs: UserPrefs) -> None:
    links = build_links(prefs)
    role_label = ROLES[prefs.role_key]
    time_label = TIMEFRAMES[prefs.timeframe]

    text = (
        f"🔎 *Job search ready*\n\n"
        f"*Batch:* {prefs.batch}\n"
        f"*Role:* {role_label}\n"
        f"*Time window:* {time_label}\n"
        f"*Location:* {prefs.location}\n\n"
        "Tap the buttons below to open the search pages.\n\n"
        "_Note: Some platforms, especially Naukri, may still open in browser based on Telegram/app behavior._"
    )

    reply_markup = job_link_buttons(links)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN,
        )


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    prefs = get_prefs(user.id)
    data = query.data

    if data == "home":
        await query.edit_message_text(
            "Choose your options below.",
            reply_markup=main_menu(prefs),
        )
        return

    if data == "menu_batch":
        await query.edit_message_text("Select batch:", reply_markup=batch_menu())
        return

    if data == "menu_role":
        await query.edit_message_text("Select role:", reply_markup=role_menu())
        return

    if data == "menu_time":
        await query.edit_message_text("Select time window:", reply_markup=timeframe_menu())
        return

    if data == "help":
        await query.edit_message_text(
            "Use /location to change location.\nThen click Search links to open current job pages.",
            reply_markup=main_menu(prefs),
        )
        return

    if data == "search_now":
        await send_links(update, context, prefs)
        return

    if data.startswith("batch:"):
        prefs.batch = data.split(":", 1)[1]
        save_prefs(user.id, prefs)
        await query.edit_message_text("✅ Batch saved.", reply_markup=main_menu(prefs))
        return

    if data.startswith("role:"):
        prefs.role_key = data.split(":", 1)[1]
        save_prefs(user.id, prefs)
        await query.edit_message_text("✅ Role saved.", reply_markup=main_menu(prefs))
        return

    if data.startswith("time:"):
        prefs.timeframe = data.split(":", 1)[1]
        save_prefs(user.id, prefs)
        await query.edit_message_text("✅ Time window saved.", reply_markup=main_menu(prefs))
        return


def run() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing in .env file")

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("location", set_location))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(callbacks))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run()