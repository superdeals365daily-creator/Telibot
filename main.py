import os, requests, sqlite3, time

# 🔑 Config (GitHub Secrets / .env se load hoga)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
CUELINKS_TOKEN = os.getenv("CUELINKS_TOKEN")
MAX_POSTS = int(os.getenv("MAX_POSTS", "5"))

# Preferred merchants (tumhare categories)
PREFERRED_SITES = [
    "zepto", "blinkit", "instamart", "zomato", "swiggy",
    "dominos", "pizzahut", "oyo", "makemytrip", "goibibo",
    "irctc", "redbus", "uber", "ola", "recharge", "insurance"
]

DB_FILE = "posted_offers.db"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ✅ Database setup
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS posted (offer_id TEXT PRIMARY KEY)")
    conn.commit()
    return conn

def already_posted(conn, offer_id):
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM posted WHERE offer_id=?", (offer_id,))
    return cur.fetchone() is not None

def mark_posted(conn, offer_id):
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO posted (offer_id) VALUES (?)", (offer_id,))
    conn.commit()

# ✅ Fetch offers from Cuelinks
def fetch_cuelinks_offers(limit=20):
    headers = {"Authorization": f'Token token="{CUELINKS_TOKEN}"'}
    url = "https://www.cuelinks.com/api/v1/offers.json"
    offers = []
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            offers.extend(data.get("offers", []))
    except Exception as e:
        print("Error fetching offers:", e)
    return offers[:limit]

# ✅ Build Telegram message
def build_message(offer):
    title = offer.get("title", "Special Deal")
    desc = offer.get("description", "Grab now!")
    link = offer.get("tracking_url") or offer.get("link", "")
    merchant = offer.get("merchant_name", "")
    return f"🔥 *{merchant} - {title}*\n\n{desc}\n\n👉 [Grab Deal]({link})"

# ✅ Post to Telegram
def post_to_telegram(text, img=None):
    if img:
        url = f"{TELEGRAM_API}/sendPhoto"
        payload = {"chat_id": TELEGRAM_CHANNEL_ID, "caption": text, "parse_mode": "Markdown"}
        files = {"photo": requests.get(img, stream=True).raw}
        requests.post(url, data=payload, files=files)
    else:
        url = f"{TELEGRAM_API}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHANNEL_ID, "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload)

# ✅ Main function
def main():
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID and CUELINKS_TOKEN):
        raise SystemExit("Missing config: TELEGRAM or CUELINKS details")

    conn = init_db()
    offers = fetch_cuelinks_offers(limit=50)
    posted = 0

    for offer in offers:
        oid = str(offer.get("id"))
        merchant = (offer.get("merchant_name") or "").lower()
        
        if not any(site in merchant for site in PREFERRED_SITES):
            continue  # skip irrelevant offers

        if already_posted(conn, oid):
            continue

        msg = build_message(offer)
        img = offer.get("image") or offer.get("logo")
        post_to_telegram(msg, img)
        mark_posted(conn, oid)
        posted += 1

        if posted >= MAX_POSTS:
            break
        time.sleep(2)

    print(f"✅ Posted {posted} offers")

if __name__ == "__main__":
    main()
  
