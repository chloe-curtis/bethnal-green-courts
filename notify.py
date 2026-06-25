import json
import os
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# --- Config ---
TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SENT_FILE = "sent.json"

HEADERS = {"User-Agent": "Mozilla/5.0"}
VENUE = "bethnal-green-gardens"
VENUE_NAME = "Bethnal Green"
COURTS = {
    154: "Court 1",
    155: "Court 2",
    156: "Court 3",
    157: "Court 4",
}
TIMES = {"08:00", "09:00", "17:00", "18:00", "19:00", "20:00", "21:00"}


# --- Scraper ---
def get_availability(date):
    url = f"https://tennistowerhamlets.com/book/courts/{VENUE}/{date}#book"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    available = []
    for slot in soup.select("input.bookable"):
        venue_id, court_id, day, time = slot["value"].split("_")
        court_id = int(court_id)
        if court_id not in COURTS or time not in TIMES:
            continue
        available.append({
            "date": day,
            "court": COURTS[court_id],
            "time": time,
        })
    return available


def slot_key(slot):
    return f"{slot['date']}_{slot['court']}_{slot['time']}"


# --- Load already-sent slots ---
if os.path.exists(SENT_FILE):
    with open(SENT_FILE) as f:
        content = f.read().strip()
        sent = set(json.loads(content)) if content else set()
else:
    sent = set()


# --- Scrape all 8 days ---
all_available = []
for i in range(8):
    date = (datetime.today() + timedelta(days=i)).strftime("%Y-%m-%d")
    try:
        slots = get_availability(date)
        all_available.extend(slots)
    except Exception as e:
        print(f"Failed for {date}: {e}")


# --- Find new slots ---
new_slots = [s for s in all_available if slot_key(s) not in sent]

if not new_slots:
    print("No new slots found.")
else:
    lines = [f"🎾 *{VENUE_NAME} — New Court Availability!*\n"]
    for slot in sorted(new_slots, key=lambda x: (x["date"], x["time"])):
        lines.append(f"📅 {slot['date']}  🕐 {slot['time']}  🎾 {slot['court']}")
    lines.append(f"\n👉 https://tennistowerhamlets.com/book/courts/{VENUE}")
    message = "\n".join(lines)

    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"},
    )
    response.raise_for_status()
    print(f"Notified about {len(new_slots)} new slot(s).")

    current_keys = {slot_key(s) for s in all_available}
    updated_sent = (sent & current_keys) | {slot_key(s) for s in new_slots}

    with open(SENT_FILE, "w") as f:
        json.dump(sorted(updated_sent), f, indent=2)
    print("sent.json updated.")
