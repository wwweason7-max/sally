import json
import os
from datetime import datetime
import pandas as pd
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
        "🏦 銀行與現金管理",
        "📝 新增日常收支",
        "📈 股票持股管理",
        "🗑️ 資料刪除與管理",
    ],
)

# -------------------------------------------------------------------
# 1. 總資產總覽
# -------------------------------------------------------------------
if menu == "📊 總資產總覽":
  st.header("📊 總資產分佈")

  cash = data.get("cash", 0.0)
  banks = data.get("banks", {})
  bank_total = sum(banks.values())

  # 台股抓取與統計
  stocks_tw = data.get("stocks_tw", [])
  tw_stock_value = 0.0
  tw_list = []
  for stock in stocks_tw:
    symbol = stock["symbol"]
    buy_price = stock["buy_price"]
    shares = stock["shares"]
    try:
      ticker = yf.Ticker(symbol)
      current_price = ticker.history(period="1d")["Close"].iloc[-1]
    except Exception:
      current_price = buy_price

    market_value = current_price * shares
    profit = market_value - (buy_price * shares)
    profit_pct = (profit / (buy_price * shares)) * 100 if buy_price > 0 else 0
    tw_stock_value += market_value

    tw_list.append({
        "代號": symbol,
        "股數": shares,
        "買入均價": buy_price,
        "即時現價": round(current_price, 2),
        "總市值 (TWD)": round(market_value, 2),
        "損益": round(profit, 2),
        "報酬率 (%)": round(profit_pct, 2),
    })

  # 美股抓取與統計
  stocks_us = data.get("stocks_us", [])
  us_stock_value = 0.0
  us_list = []
  for stock in stocks_us:
    symbol = stock["symbol"]
    buy_price = stock["buy_price"]
    shares = stock["shares"]
    try:
      ticker = yf.Ticker(symbol)
      current_price = ticker.history(period="1d")["Close"].iloc[-1]
    except Exception:
      current_price = buy_price

    market_value = current_price * shares
    profit = market_value - (buy_price * shares)
    profit_pct = (profit / (buy_price * shares)) * 100 if buy_price > 0 else 0
    us_stock_value += market_value

    us_list.append({
        "代號": symbol,
        "股數": shares,
        "買入均價 ($)": buy_price,
        "即時現價 ($)": round(current_price, 2),
        "總市值 ($)": round(market_value, 2),
        "損益 ($)": round(profit, 2),
        "報酬率 (%)": round(profit_pct, 2),
    })

  total_net_worth = cash + bank_total + tw_stock_value

  st.success(
      f"### 💎 總淨資產 (現金 + 銀行 + 台股)： NT$ {total_net_worth:,.2f}"
  )
  st.caption("* 註：美股總市值為 USD 獨立顯示")

  st.markdown("---")

  col1, col2, col3, col4 = st.columns(4)
  col1.metric("💵 手邊現金", f"NT$ {cash:,.2f}")
  col2.metric("🏦 銀行存款總計", f"NT$ {bank_total:,.2f}")
  col3.metric("🇹🇼 台股總市值", f"NT$ {tw_stock_value:,.2f}")
  col4.metric("🇺🇸 美股總市值", f"US$ {us_stock_value:,.2f}")

  st.markdown("---")

  # 銀行細項
  st.subheader("🏦 銀行帳戶細節")
  if banks:
    bank_df = pd.DataFrame(
        list(banks.items()), columns=["銀行名稱", "存款餘額 (NT$)"]
    )
    st.dataframe(bank_df, use_container_width=True)
  else:
    st.info("尚無銀行帳戶資料")

  # 台股細項
  st.subheader("🇹🇼 台股持股明細")
  if tw_list:
    st.dataframe(tw_list, use_container_width=True)
  else:
    st.info("尚無台股持股")

  # 美股細項
  st.subheader("🇺🇸 美股持股明細")
  if us_list:
    st.dataframe(us_list, use_container_width=True)
  else:
    st.info("尚無美股持股")

# -------------------------------------------------------------------
# 2. 銀行與現金管理
# -------------------------------------------------------------------
elif menu == "🏦 銀行與現金管理":
  st.header("🏦 銀行帳戶與現金設定")

  # 調整手邊現金
  st.subheader("💵 調整手邊現金金額")
  new_cash = st.number_input(
      "目前現金總額", min_value=0.0, value=float(data.get("cash", 0.0)), step=100.0
  )
  if st.button("更新現金金額"):
    data["cash"] = new_cash
    save_data(data)
    st.success("✅ 現金總額更新成功！")

  st.markdown("---")

  # 新增 / 編輯銀行帳戶
  st.subheader("🏦 新增或修改銀行帳戶")
  with st.form("add_bank_form"):
    bank_name = st.text_input("銀行名稱 (例如：中國信託, 台新銀行)")
    bank_balance = st.number_input("當前存款金額", min_value=0.0, step=1000.0)
    submit_bank = st.form_submit_button("儲存銀行帳戶")
    if submit_bank and bank_name:
      data.setdefault("banks", {})[bank_name] = bank_balance
      save_data(data)
      st.success(f"✅ 已成功儲存 {bank_name} 的存款金額！")

# -------------------------------------------------------------------
# 3. 新增日常收支
# -------------------------------------------------------------------
elif menu == "📝 新增日常收支":
  st.header("📝 記帳功能")

  account_options = ["現金"] + list(data.get("banks", {}).keys())

  with st.form("expense_form"):
    date = st.date_input("日期", datetime.now())
    t_type = st.selectbox("類型", ["支出", "收入"])
    account = st.selectbox("資金來源/入帳帳戶", account_options)
    category = st.text_input("類別 (例如：餐飲、交通、薪水)")
    amount = st.number_input("金額", min_value=0.0, step=10.0)
    note = st.text_input("備註 (可留空)")

    submitted = st.form_submit_button("確認新增紀錄")
    if submitted and amount > 0:
      date_str = date.strftime("%Y-%m-%d")
      data.setdefault("transactions", []).append({
          "date": date_str,
          "type": t_type,
          "account": account,
          "category": category,
          "amount": amount,
          "note": note,
      })

      # 扣款/入帳金額連動
      if account == "現金":
        data["cash"] = data.get("cash", 0.0) + (
            amount if t_type == "收入" else -amount
        )
      elif account in data.get("banks", {}):
        data["banks"][account] += amount if t_type == "收入" else -amount

      save_data(data)
      st.success("✅ 記帳成功並已自動更新對應帳戶餘額！")

  st.markdown("### 📜 歷史記帳明細")
  txs = data.get("transactions", [])
  if txs:
    st.dataframe(txs, use_container_width=True)

# -------------------------------------------------------------------
# 4. 股票持股管理
# -------------------------------------------------------------------
elif menu == "📈 股票持股管理":
  st.header("📈 新增股票持股")

  stock_market = st.radio("選擇市場", ["🇹🇼 台股", "🇺🇸 美股"])

  with st.form("stock_form"):
    if stock_market == "🇹🇼 台股":
      st.caption("提示：台股代號請加上 `.TW`（例如 `2330.TW`）")
      symbol = st.text_input("台股代號 (如 2330.TW)").upper()
    else:
      st.caption("提示：美股請直接輸入代號（例如 `AAPL`, `NVDA`）")
      symbol = st.text_input("美股代號 (如 AAPL)").upper()

    buy_price = st.number_input("買入均價", min_value=0.0, step=0.1)
    shares = st.number_input("持有股數", min_value=0.0, step=1.0)

    submitted = st.form_submit_button("確認新增股票")
    if submitted and symbol:
      if stock_market == "🇹🇼 台股":
        data.setdefault("stocks_tw", []).append(
            {"symbol": symbol, "buy_price": buy_price, "shares": shares}
        )
      else:
        data.setdefault("stocks_us", []).append(
            {"symbol": symbol, "buy_price": buy_price, "shares": shares}
        )
      save_data(data)
      st.success(f"✅ 已成功新增 {stock_market} {symbol}！")

# -------------------------------------------------------------------
# 5. 資料刪除與管理
# -------------------------------------------------------------------
elif menu == "🗑️ 資料刪除與管理":
  st.header("🗑️ 清理與刪除錯誤資料")

  # 刪除銀行帳戶
  st.subheader("🏦 刪除銀行帳戶")
  banks = list(data.get("banks", {}).keys())
  if banks:
    bank_to_del = st.selectbox("選擇要刪除的銀行帳戶", banks)
    if st.button("刪除選擇的銀行帳戶"):
      del data["banks"][bank_to_del]
      save_data(data)
      st.success(f"✅ 已成功刪除 {bank_to_del}")
      st.rerun()

  st.markdown("---")

  # 刪除台股持股
  st.subheader("🇹🇼 刪除台股持股")
  tw_stocks = data.get("stocks_tw", [])
  if tw_stocks:
    tw_symbols = [s["symbol"] for s in tw_stocks]
    tw_to_del = st.selectbox("選擇要刪除的台股代號", tw_symbols)
    if st.button("刪除此台股"):
      data["stocks_tw"] = [
          s for s in tw_stocks if s["symbol"] != tw_to_del
      ]
      save_data(data)
      st.success(f"✅ 已刪除台股 {tw_to_del}")
      st.rerun()

  st.markdown("---")

  # 刪除美股持股
  st.subheader("🇺🇸 刪除美股持股")
  us_stocks = data.get("stocks_us", [])
  if us_stocks:
    us_symbols = [s["symbol"] for s in us_stocks]
    us_to_del = st.selectbox("選擇要刪除的美股代號", us_symbols)
    if st.button("刪除此美股"):
      data["stocks_us"] = [
          s for s in us_stocks if s["symbol"] != us_to_del
      ]
      save_data(data)
      st.success(f"✅ 已刪除美股 {us_to_del}")
      st.rerun()