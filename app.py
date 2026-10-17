from datetime import datetime
import json
import os
import re
import pandas as pd
from PIL import Image
import pytesseract
import streamlit as st
import yfinance as yf

DATA_FILE = "finance_data.json"


def load_data():
  if not os.path.exists(DATA_FILE):
    return {
        "cash": 0.0,
        "banks": {"A 銀行": 0.0, "B 銀行": 0.0},
        "transactions": [],
        "stocks_tw": [],
        "stocks_us": [],
    }
  with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)
    if "banks" not in data:
      data["banks"] = {"A 銀行": 0.0, "B 銀行": 0.0}
    if "stocks_tw" not in data:
      data["stocks_tw"] = []
    if "stocks_us" not in data:
      data["stocks_us"] = []
    return data


def save_data(data):
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


def get_stock_info(symbol):
  """抓取股票名稱與即時現價"""
  try:
    ticker = yf.Ticker(symbol)
    info = ticker.info
    name = (
        info.get("shortName")
        or info.get("longName")
        or info.get("displaySymbol")
        or symbol
    )
    history = ticker.history(period="1d")
    current_price = (
        history["Close"].iloc[-1] if not history.empty else 0.0
    )
    return name, current_price
  except Exception:
    return symbol, 0.0


st.set_page_config(
    page_title="個人資產管理系統", page_icon="💰", layout="wide"
)

data = load_data()

st.title("💰 個人資產管理系統")
st.markdown("---")

menu = st.sidebar.selectbox(
    "選擇功能區塊",
    [
        "📊 總資產總覽",
        "📸 截圖自動辨識持股",
        "🏦 銀行與現金管理",
        "📝 新增日常收支",
        "📈 手動新增股票",
        "🗑️ 資料刪除與管理",
    ],
)

# -------------------------------------------------------------------
# 1. 總資產總覽 (含股票中文名稱)
# -------------------------------------------------------------------
if menu == "📊 總資產總覽":
  st.header("📊 總資產分佈")

  cash = data.get("cash", 0.0)
  banks = data.get("banks", {})
  bank_total = sum(banks.values())

  # 台股抓取
  stocks_tw = data.get("stocks_tw", [])
  tw_stock_value = 0.0
  tw_list = []
  for stock in stocks_tw:
    symbol = stock["symbol"]
    buy_price = stock["buy_price"]
    shares = stock["shares"]

    name, current_price = get_stock_info(symbol)
    if current_price == 0.0:
      current_price = buy_price

    market_value = current_price * shares
    profit = market_value - (buy_price * shares)
    profit_pct = (profit / (buy_price * shares)) * 100 if buy_price > 0 else 0
    tw_stock_value += market_value

    tw_list.append({
        "股票名稱 (代號)": f"{symbol} - {name}",
        "持股數": shares,
        "買入均價": buy_price,
        "即時現價": round(current_price, 2),
        "總市值 (TWD)": round(market_value, 2),
        "未實現損益": round(profit, 2),
        "報酬率 (%)": round(profit_pct, 2),
    })

  # 美股抓取
  stocks_us = data.get("stocks_us", [])
  us_stock_value = 0.0
  us_list = []
  for stock in stocks_us:
    symbol = stock["symbol"]
    buy_price = stock["buy_price"]
    shares = stock["shares"]

    name, current_price = get_stock_info(symbol)
    if current_price == 0.0:
      current_price = buy_price

    market_value = current_price * shares
    profit = market_value - (buy_price * shares)
    profit_pct = (profit / (buy_price * shares)) * 100 if buy_price > 0 else 0
    us_stock_value += market_value

    us_list.append({
        "股票名稱 (代號)": f"{symbol} - {name}",
        "持股數": shares,
        "買入均價 ($)": buy_price,
        "即時現價 ($)": round(current_price, 2),
        "總市值 ($)": round(market_value, 2),
        "未實現損益 ($)": round(profit, 2),
        "報酬率 (%)": round(profit_pct, 2),
    })

  total_net_worth = cash + bank_total + tw_stock_value

  st.success(
      f"### 💎 總淨資產 (現金 + 銀行 + 台股)： NT$ {total_net_worth:,.2f}"
  )

  col1, col2, col3, col4 = st.columns(4)
  col1.metric("💵 手邊現金", f"NT$ {cash:,.2f}")
  col2.metric("🏦 銀行存款總計", f