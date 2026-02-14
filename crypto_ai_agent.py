import requests
import pandas as pd
import numpy as np
import ta
import time
from telegram import Bot

# ==========================
# CONFIGURATION
# ==========================

SYMBOL = "BTCUSDT"   # You can change to ETHUSDT
TIMEFRAME = "1h"
LIMIT = 200

import os

TELEGRAM_TOKEN = os.getenv("8553832621:AAGyZwKXo59aaSAWqmHVBoUqm2qjz8dhQnY")
CHAT_ID = os.getenv("6289424434")


bot = Bot(token=TELEGRAM_TOKEN)


# ==========================
# DATA ENGINE (Binance public API used for price feed)
# ==========================

def get_data():
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={TIMEFRAME}&limit={LIMIT}"
    data = requests.get(url).json()

    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "_", "_", "_", "_", "_", "_"
    ])

    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)

    return df


# ==========================
# INDICATORS
# ==========================

def calculate_indicators(df):

    df["ema9"] = ta.trend.ema_indicator(df["close"], window=9)
    df["ema20"] = ta.trend.ema_indicator(df["close"], window=20)
    df["ema200"] = ta.trend.ema_indicator(df["close"], window=200)
    df["rsi"] = ta.momentum.rsi(df["close"], window=14)
    df["vol_avg"] = df["volume"].rolling(20).mean()

    return df


# ==========================
# STRATEGY ENGINE
# ==========================

def generate_signal(df):

    last = df.iloc[-1]
    prev = df.iloc[-2]

    signal = None

    # LONG
    if (
        last["close"] > last["ema200"] and
        prev["ema9"] < prev["ema20"] and
        last["ema9"] > last["ema20"] and
        last["rsi"] > 50 and
        last["volume"] > last["vol_avg"]
    ):
        signal = "LONG"

    # SHORT
    elif (
        last["close"] < last["ema200"] and
        prev["ema9"] > prev["ema20"] and
        last["ema9"] < last["ema20"] and
        last["rsi"] < 50 and
        last["volume"] > last["vol_avg"]
    ):
        signal = "SHORT"

    return signal


# ==========================
# RISK MANAGEMENT
# ==========================

def calculate_sl_target(df, signal):

    last = df.iloc[-1]
    entry = last["close"]

    if signal == "LONG":
        sl = df["low"].rolling(5).min().iloc[-1]
        risk = entry - sl
        target = entry + (risk * 2)

    elif signal == "SHORT":
        sl = df["high"].rolling(5).max().iloc[-1]
        risk = sl - entry
        target = entry - (risk * 2)

    rr = abs(target - entry) / abs(entry - sl)

    return entry, sl, target, rr


# ==========================
# SCORING ENGINE
# ==========================

def score_signal(df, signal):

    last = df.iloc[-1]
    score = 0

    if signal == "LONG":
        if last["close"] > last["ema200"]:
            score += 2
        if last["ema9"] > last["ema20"]:
            score += 2
        if last["rsi"] > 50:
            score += 1
        if last["volume"] > last["vol_avg"]:
            score += 2
        if last["close"] > last["open"]:
            score += 1

    if signal == "SHORT":
        if last["close"] < last["ema200"]:
            score += 2
        if last["ema9"] < last["ema20"]:
            score += 2
        if last["rsi"] < 50:
            score += 1
        if last["volume"] > last["vol_avg"]:
            score += 2
        if last["close"] < last["open"]:
            score += 1

    return score


# ==========================
# TELEGRAM ALERT
# ==========================

def send_alert(signal, entry, sl, target, score, rr):

    strength = "WEAK"

    if score >= 7:
        strength = "🔥 STRONG"
    elif score >= 5:
        strength = "✅ MODERATE"

    message = f"""
🚀 {SYMBOL} {signal} SIGNAL

Entry: {entry:.2f}
Stoploss: {sl:.2f}
Target: {target:.2f}
RR: {rr:.2f}
Strength: {strength}
Score: {score}/8
"""

    bot.send_message(chat_id=CHAT_ID, text=message)


# ==========================
# MAIN LOOP
# ==========================

def run():

    print("AI Agent Running...")

    while True:

        df = get_data()
        df = calculate_indicators(df)

        signal = generate_signal(df)

        if signal:
            entry, sl, target, rr = calculate_sl_target(df, signal)
            score = score_signal(df, signal)

            if score >= 6 and rr >= 2:
                send_alert(signal, entry, sl, target, score, rr)
                print("Signal Sent")

        time.sleep(60)   # Runs every 1 hour


if __name__ == "__main__":
    run()
