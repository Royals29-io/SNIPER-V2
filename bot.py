import websocket, json, time, requests, os
from threading import Thread
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

SYMBOLS = ["R_10","R_25","R_50","R_75","R_100","1HZ10V","1HZ25V","1HZ50V","1HZ75V","1HZ100V","stpRNG","stpRNG2","stpRNG3","stpRNG4","stpRNG5","frxXAUUSD"]

NEWS_BLOCKED = False
NEWS_MSG = ""
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
history = {s: [] for s in SYMBOLS}

def send_telegram(msg):
    if not TELEGRAM_TOKEN:
        print(msg)
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

def news_watcher():
    global NEWS_BLOCKED, NEWS_MSG
    while True:
        try:
            r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=15).json()
            blocked = False
            for ev in r:
                if ev.get('impact') == 'High' and ev.get('currency') == 'USD':
                    title = ev.get('title','')
                    if any(k in title for k in ['Non-Farm','CPI','FOMC','Employment','Fed']):
                        blocked = True
                        NEWS_MSG = f"⚠️ {title} - GOLD BLOCKED"
            NEWS_BLOCKED = blocked
            time.sleep(60)
        except:
            time.sleep(120)

def check_and_signal(symbol, price):
    hist = history.get(symbol, [])
    hist.append(price)
    if len(hist) > 50:
        hist.pop(0)
    history[symbol] = hist
    if len(hist) < 20:
        return
    sma = sum(hist) / len(hist)
    atr = sum(abs(hist[i]-hist[i-1]) for i in range(1, len(hist))) / (len(hist)-1) if len(hist) > 1 else 0.001
    if atr == 0:
        atr = 0.001
    dist = abs(price - sma) / atr if atr else 0
    stretch = min(100, (dist / 3) * 100)
    is_chop = atr < 0.002
    if "XAU" in symbol and NEWS_BLOCKED:
        return
    if is_chop or stretch < 85:
        return
    direction = "SELL" if price > sma else "BUY"
    emoji = "🔴" if direction == "SELL" else "🟢"
    msg = f"{emoji} *{direction} {symbol}*\nStretch: {stretch:.0f}%\nPrice: {price}\nMarket: CLEAN ✅"
    send_telegram(msg)

def on_message(ws, message):
    try:
        d = json.loads(message)
        if 'tick' in d:
            sym = d['tick']['symbol']
            price = float(d['tick']['quote'])
            check_and_signal(sym, price)
    except:
        pass

def start_ws():
    while True:
        try:
            ws = websocket.WebSocketApp(
                "wss://ws.derivws.com/websockets/v3?app_id=1089",
                on_message=on_message,
                on_open=lambda w: [w.send(json.dumps({"ticks": s})) for s in SYMBOLS]
            )
            ws.run_forever(ping_interval=30)
        except:
            time.sleep(5)

@app.route('/')
def home():
    return f"Sniper V2 - LIVE - {len(SYMBOLS)} Markets on Koyeb"

@app.route('/api/news-status')
def news_status():
    return jsonify({"blocked": NEWS_BLOCKED, "message": NEWS_MSG})

if __name__ == '__main__':
    Thread(target=news_watcher, daemon=True).start()
    Thread(target=start_ws, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8000)))
