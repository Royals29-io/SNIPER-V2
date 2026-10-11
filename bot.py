import os
import threading
import time
import requests
import websocket
import json
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime

# --- CONFIG ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DERIV_APP_ID = os.getenv("DERIV_APP_ID", "1089")

app = Flask(__name__)

# --- BEKENET DASHBOARD HTML (Same as your screenshot) ---
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bekenet Style Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#0f172a;color:white;font-family:Arial;padding:15px}
.btn{width:100%;padding:15px;border:none;border-radius:12px;font-weight:bold;margin:8px 0;font-size:16px}
.green{background:#10b981;color:white}
.yellow{background:#facc15;color:black}
.blue{background:#2563eb;color:white}
.card{background:#1e293b;padding:15px;border-radius:12px;margin-top:15px}
input{width:45%;padding:12px;background:#0f172a;border:1px solid #334155;color:white;border-radius:8px}
h3{color:#38bdf8}
</style>
</head>
<body>
<h2>📊 Sniper V2 Dashboard</h2>

<button class="btn green" onclick="window.open('https://app.deriv.com/dtrader','_blank')">📈 Deriv inbuilt Chart</button>
<button class="btn yellow">📊 Check Trend level</button>

<div class="card">
<h3>Bekenet Advance Trend direction</h3>
<div style="display:flex;justify-content:space-between">
<div><small>X: Start Point</small><br><input id="xVal" placeholder="0.00" value="0.00"></div>
<div><small>Y: Current Price</small><br><input id="yVal" placeholder="0.00" value="0.00"></div>
</div>
<br>
<button class="btn blue" onclick="checkTrend()">Check Trend</button>
<div id="result" style="margin-top:15px;font-weight:bold"></div>
</div>

<div class="card">
<h4>Trend History</h4>
<small>ORIGIN</small><br><br>
<small>X-AXIS: Start Point &nbsp; Y-AXIS: Current ma</small><br>
<canvas id="trendChart" height="200"></canvas>
<div id="status" style="margin-top:10px"><span style="color:#3b82f6">● Trend Path</span> <span style="color:#ef4444">● Active Price</span> <span style="color:#22c55e">× Origin</span> &nbsp; <span id="ready">Ready</span></div>
</div>

<script>
let chart;
function checkTrend(){
 let x = parseFloat(document.getElementById('xVal').value)||0;
 let y = parseFloat(document.getElementById('yVal').value)||0;
 if(x==0){document.getElementById('result').innerHTML='Enter Start Point';return;}
 let diff = ((y - x)/x)*100;
 let strength = Math.min(100, Math.abs(diff)*2);
 let direction = y > x ? 'BUY Trend' : 'SELL Trend';
 let msg = '';
 if(strength > 85) msg = '⚠️ Trend Exhausted - Prepare Reversal';
 else if(strength > 60) msg = '✅ Trend Still Strong - Continue';
 else msg = '🔄 Trend Weak - Wait';

 document.getElementById('result').innerHTML = `
 ${direction}<br>
 Move: ${diff.toFixed(2)}%<br>
 Strength: ${strength.toFixed(1)}%<br>
 ${msg}<br><br>
 Support is ${strength.toFixed(0)}% From Current price
 `;

 // Update chart
 let data = [x, (x+y)/2, y];
 if(chart) chart.destroy();
 chart = new Chart(document.getElementById('trendChart'),{
  type:'line',
  data:{labels:['Origin','Mid','Active'],datasets:[
   {label:'Trend Path',data:data,borderColor:'#3b82f6',tension:0.4},
   {label:'Active Price',data:[null,null,y],backgroundColor:'#ef4444',pointRadius:8,type:'scatter'},
   {label:'Origin',data:[x,null,null],backgroundColor:'#22c55e',pointRadius:8,type:'scatter'}
  ]},
  options:{scales:{y:{beginAtZero:false}}}
 });
}

 // Auto fill from URL ?x=&y=
 const urlParams = new URLSearchParams(window.location.search);
 if(urlParams.get('x')) document.getElementById('xVal').value = urlParams.get('x');
 if(urlParams.get('y')) document.getElementById('yVal').value = urlParams.get('y');
 if(urlParams.get('x')) checkTrend();
</script>
</body>
</html>
"""

@app.route('/')
def home():
    return "Sniper V2 LIVE - Go to /dashboard"

@app.route('/dashboard')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/trend')
def api_trend():
    try:
        x = float(request.args.get('x',0))
        y = float(request.args.get('y',0))
        diff = ((y-x)/x*100) if x!=0 else 0
        return jsonify({"diff":diff,"strength":abs(diff),"direction":"BUY" if y>x else "SELL"})
    except:
        return jsonify({"error":"invalid"})

# --- YOUR SNIPER BOT LOGIC ---
MARKETS = ["R_10","R_25","R_50","R_75","R_100","1HZ10V","1HZ25V","1HZ50V","1HZ75V","1HZ100V","JD10","JD25","JD50","JD75","JD100","FLX5"]

def send_telegram(msg):
    if not TELEGRAM_TOKEN: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        # Add dashboard link like Bekenet
        dashboard_link = f"{os.getenv('RAILWAY_PUBLIC_DOMAIN','')}/dashboard"
        if dashboard_link.startswith("http") is False and dashboard_link!="":
            dashboard_link = "https://"+dashboard_link
        full_msg = msg + f"\n\n📊 Check Trend: {dashboard_link}/dashboard" if dashboard_link else msg
        requests.post(url, json={"chat_id":TELEGRAM_CHAT_ID,"text":full_msg,"parse_mode":"Markdown"}, timeout=10)
    except Exception as e:
        print("Telegram error",e)

def on_message(ws, message):
    data = json.loads(message)
    if 'tick' in data:
        symbol = data['tick']['symbol']
        price = float(data['tick']['quote'])
        # Simple sniper logic - replace with your stretch logic
        print(f"{symbol} {price}")
        # Example signal condition (you keep your own)
        # if stretch > 85: send_telegram(f"BUY {symbol} NOW...")

def on_open(ws):
    print("Deriv Connected - LIVE")
    for m in MARKETS:
        ws.send(json.dumps({"ticks":m}))

def run_bot():
    while True:
        try:
            ws = websocket.WebSocketApp(f"wss://ws.derivws.com/websockets/v3?app_id={DERIV_APP_ID}",
                                        on_message=on_message, on_open=on_open)
            ws.run_forever()
        except Exception as e:
            print("WS error",e)
            time.sleep(5)

# --- START BOTH ---
if __name__ == "__main__":
    # Start bot in background thread
    threading.Thread(target=run_bot, daemon=True).start()
    # Start Flask web (dashboard)
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
