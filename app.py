from datetime import datetime
import json
import os
import streamlit as st
import yfinance as yf

DATA_FILE = "finance_data.json"


def load_data():
  """載入本地 JSON 資料"""
  if not os.path.exists(DATA_FILE):
    return {"cash": 0, "transactions": [], "stocks": []}
  with open(DATA_FILE, "r", encoding="utf-8") as f:
    return json.load(f)


def save_data(data):
  """儲存資料到本地 JSON"""
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


st.set_page_config(
    page_title="我的個人資產管理系統", page_icon="💰", layout="wide"
)

data = load_data()

st.title("💰 個人資產與即時股票追蹤系統")
st.markdown("---")

# 侧邊欄功能選單
menu = st.sidebar.selectbox(
    "選擇功能", ["📊 總資產與即時股價", "📝 新增日常收支", "📈 新增股票持股"]
)

# 1. 查看總資產與股票
if menu == "📊 總資產與即時股價":
  st.header("📊 資產總覽")

  cash = data.get("cash", 0)
  stock_value = 0

  col1, col2 = st.columns(2)
  col1.metric("💵 現金餘額", f"{cash:,.2f} 元")

  stocks = data.get("stocks", [])
  stock_data_list = []

  if stocks:
    for stock in stocks:
      symbol = stock["symbol"]
      buy_price = stock["buy_price"]
      shares = stock["shares"]
      try:
        ticker = yf.Ticker(symbol)
        current_price = ticker.history(period="1d")["Close"].iloc[-1]
      except Exception:
        current_price = buy_price

      market_value = current_price * shares
      cost = buy_price * shares
      profit = market_value - cost
      profit_pct = (profit / cost) * 100 if cost > 0 else 0
      stock_value += market_value

      stock_data_list.append({
          "股票代號": symbol,
          "持股數": shares,
          "買入均價": buy_price,
          "即時現價": round(current_price, 2),
          "總市值": round(market_value, 2),
          "未實現損益": round(profit, 2),
          "報酬率 (%)": round(profit_pct, 2),
      })

  col2.metric("📈 股票總市值", f"{stock_value:,.2f} 元")
  st.markdown("### 💎 淨資產總額")
  st.info(f"### 總資產 (現金 + 股票)：{cash + stock_value:,.2f} 元")

  st.markdown("---")
  st.subheader("📋 股票持股明細與即時損益")
  if stock_data_list:
    st.dataframe(stock_data_list, use_container_width=True)
  else:
    st.write("目前尚未新增任何股票。")

# 2. 新增日常收支
elif menu == "📝 新增日常收支":
  st.header("📝 記帳功能")

  with st.form("expense_form"):
    date = st.date_input("日期", datetime.now())
    t_type = st.selectbox("類型", ["支出", "收入"])
    category = st.text_input("類別 (例如：餐飲、交通、薪水)")
    amount = st.number_input("金額", min_value=0.0, step=10.0)
    note = st.text_input("備註 (可留空)")

    submitted = st.form_submit_button("確認新增")
    if submitted:
      date_str = date.strftime("%Y-%m-%d")
      data.setdefault("transactions", []).append({
          "date": date_str,
          "type": t_type,
          "category": category,
          "amount": amount,
          "note": note,
      })

      if t_type == "收入":
        data["cash"] = data.get("cash", 0) + amount
      else:
        data["cash"] = data.get("cash", 0) - amount

      save_data(data)
      st.success("✅ 記帳成功！")

  st.markdown("### 📜 近期收支紀錄")
  transactions = data.get("transactions", [])
  if transactions:
    st.dataframe(transactions, use_container_width=True)
  else:
    st.write("目前尚無記帳紀錄。")

# 3. 新增股票持股
elif menu == "📈 新增股票持股":
  st.header("📈 新增股票")

  with st.form("stock_form"):
    symbol = st.text_input(
        "股票代號 (台股請加 .TW，例如 2330.TW；美股直接輸入如 AAPL)"
    ).upper()
    buy_price = st.number_input("買入均價", min_value=0.0, step=0.1)
    shares = st.number_input("持有股數", min_value=0.0, step=1.0)

    submitted = st.form_submit_button("確認新增股票")
    if submitted and symbol:
      data.setdefault("stocks", []).append(
          {"symbol": symbol, "buy_price": buy_price, "shares": shares}
      )
      save_data(data)
      st.success(f"✅ 成功新增股票 {symbol}！")

  st.markdown("### 📋 目前持股清單")
  stocks = data.get("stocks", [])
  if stocks:
    st.dataframe(stocks, use_container_width=True)
  else:
    st.write("目前尚無持股。")