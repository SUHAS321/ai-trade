import time
import requests
import pandas as pd
import numpy as np
# =========================
# TELEGRAM CONFIG
# =========================
TELEGRAM_TOKEN = "8725264690:AAE6xjCAyXyc2qsTRMk9eeuy6_cWXOy8uFA"
CHAT_ID = "1345617133"

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        pass


# =========================
# SETTINGS
# =========================
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]

BALANCE = 20
TRADE_PERCENT = 0.25

TP = 0.01
SL = 0.005

active_trades = {}

# =========================
# DATA
# =========================
def get_data(symbol, interval):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=100"
    data = requests.get(url).json()
    df = pd.DataFrame(data)
    df["close"] = df[4].astype(float)
    df["volume"] = df[5].astype(float)
    return df


# =========================
# RSI
# =========================
def rsi(series):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# =========================
# NEWS SENTIMENT (BASIC)
# =========================
def news_score():
    # simplified dummy sentiment
    return np.random.uniform(-1, 1)


# =========================
# SIGNAL ENGINE
# =========================
def analyze(symbol):
    df1 = get_data(symbol, "1m")
    df5 = get_data(symbol, "5m")

    price = df1["close"].iloc[-1]

    # indicators
    ema9 = df1["close"].ewm(span=9).mean().iloc[-1]
    ema21 = df1["close"].ewm(span=21).mean().iloc[-1]

    ema5_tf = df5["close"].ewm(span=9).mean().iloc[-1]
    ema21_tf = df5["close"].ewm(span=21).mean().iloc[-1]

    r = rsi(df1["close"]).iloc[-1]

    volume = df1["volume"].iloc[-1]
    avg_volume = df1["volume"].rolling(20).mean().iloc[-1]

    news = news_score()

    score = 0

    # Trend
    if ema9 > ema21 and ema5_tf > ema21_tf:
        score += 1
    elif ema9 < ema21 and ema5_tf < ema21_tf:
        score += 1

    # RSI
    if 35 < r < 45 or 55 < r < 65:
        score += 1

    # Volume
    if volume > avg_volume:
        score += 1

    # News
    if news > 0:
        score += 1

    # SIGNAL
    if score >= 3:
        if ema9 > ema21:
            return "BUY", price, score
        else:
            return "SELL", price, score

    return "HOLD", price, score


# =========================
# OPEN TRADE
# =========================
def open_trade(symbol):
    global BALANCE

    if symbol in active_trades:
        return

    signal, price, score = analyze(symbol)

    if signal == "HOLD":
        return

    amount = BALANCE * TRADE_PERCENT
    qty = amount / price

    if signal == "BUY":
        tp = price * (1 + TP)
        sl = price * (1 - SL)
    else:
        tp = price * (1 - TP)
        sl = price * (1 + SL)

    active_trades[symbol] = {
        "side": signal,
        "entry": price,
        "tp": tp,
        "sl": sl,
        "qty": qty,
        "score": score
    }

    send(f"""
📊 ENTRY SIGNAL
{symbol} {signal}

Entry: {price:.2f}
TP: {tp:.2f}
SL: {sl:.2f}

Confidence: {score}/4
Balance: ${BALANCE:.2f}
""")


# =========================
# CLOSE TRADES
# =========================
def check_trades():
    global BALANCE

    to_close = []

    for symbol, trade in active_trades.items():
        price = float(requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        ).json()["price"])

        entry = trade["entry"]
        qty = trade["qty"]
        side = trade["side"]

        if side == "BUY":
            if price >= trade["tp"] or price <= trade["sl"]:
                pnl = (price - entry) * qty
            else:
                continue
        else:
            if price <= trade["tp"] or price >= trade["sl"]:
                pnl = (entry - price) * qty
            else:
                continue

        BALANCE += pnl
        result = "PROFIT" if pnl > 0 else "LOSS"

        send(f"""
📉 TRADE CLOSED
{symbol}

Result: {result}
PnL: ${pnl:.2f}

💰 Balance: ${BALANCE:.2f}
""")

        to_close.append(symbol)

    for s in to_close:
        del active_trades[s]


# =========================
# MAIN LOOP
# =========================
send("🚀 AI TRADING BOT STARTED")

while True:
    try:
        for s in SYMBOLS:
            open_trade(s)

        check_trades()

        time.sleep(20)

    except Exception as e:
        print(e)
        time.sleep(20)