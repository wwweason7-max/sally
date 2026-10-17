from datetime import datetime
import json
import os
import re
from datetime import datetime
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
        "📸 截圖自動辨識與調整",
        "🏦 銀行與現金管理",
        "📝 新增日常收支",
        "📈 手動新增股票",
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
  col2.metric("🏦 銀行存款總計", f"NT$ {bank_total:,.2f}")
  col3.metric("🇹🇼 台股總市值", f"NT$ {tw_stock_value:,.2f}")
  col4.metric("🇺🇸 美股總市值", f"US$ {us_stock_value:,.2f}")

  st.markdown("---")
  st.subheader("🇹🇼 台股持股明細")
  if tw_list:
    st.dataframe(tw_list, use_container_width=True)
  else:
    st.info("尚無台股持股")

  st.subheader("🇺🇸 美股持股明細")
  if us_list:
    st.dataframe(us_list, use_container_width=True)
  else:
    st.info("尚無美股持股")

# -------------------------------------------------------------------
# 2. 📸 截圖自動辨識與互動式表格調整
# -------------------------------------------------------------------
elif menu == "📸 截圖自動辨識與調整":
  st.header("📸 截圖辨識與手動微調表格")
  st.write(
      "上傳截圖後，系統會列出辨識結果。你可以**直接在下方表格中修改代號、均價、股數**，確認無誤後一鍵批量匯入！"
  )

  uploaded_file = st.file_uploader(
      "選擇券商 App 庫存截圖...", type=["jpg", "jpeg", "png"]
  )

  if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="已上傳截圖", width=300)

    if st.button("🔍 解析截圖並產生編輯表格"):
      with st.spinner("辨識中..."):
        try:
          text = pytesseract.image_to_string(image, lang="chi_tra+eng")
          found_codes = re.findall(r"\b\d{4}\b", text)
          found_codes = list(dict.fromkeys(found_codes))

          # 建立預設暫存清單給表格編輯
          editable_data = []
          for code in found_codes:
            symbol = f"{code}.TW"
            _, price = get_stock_info(symbol)
            editable_data.append({
                "代號": symbol,
                "買入均價": float(price if price > 0 else 100.0),
                "持有股數": 1000.0,
            })

          # 如果沒抓到代號，給一行空白範例讓用戶手動填
          if not editable_data:
            editable_data.append(
                {"代號": "2330.TW", "買入均價": 600.0, "持有股數": 1000.0}
            )

          st.session_state["ocr_table"] = pd.DataFrame(editable_data)
          st.success("🎉 表格已產生，請在下方直接修改資料！")
        except Exception as e:
          st.error(f"解析失敗：{e}")

    # 如果已經產生表格，顯示互動式編輯器
    if "ocr_table" in st.session_state:
      st.markdown("### ✏️ 修正與調整持股表格")
      st.caption("提示：點擊表格內的格子即可直接修改數字或股票代號。")

      edited_df = st.data_editor(
          st.session_state["ocr_table"], num_rows="dynamic", use_container_width=True
      )

      if st.button("🚀 確認無誤，批量加入持股清單"):
        added_count = 0
        for index, row in edited_df.iterrows():
          sym = str(row["代號"]).strip().upper()
          if not sym.endswith(".TW") and sym.isdigit() and len(sym) == 4:
            sym = f"{sym}.TW"

          data.setdefault("stocks_tw", []).append({
              "symbol": sym,
              "buy_price": float(row["買入均價"]),
              "shares": float(row["持有股數"]),
          })
          added_count += 1

        save_data(data)
        st.success(f"✅ 成功批量匯入 {added_count} 筆持股資料！")
        del st.session_state["ocr_table"]  # 清除暫存

# -------------------------------------------------------------------
# 3. 🏦 銀行與現金管理
# -------------------------------------------------------------------
elif menu == "🏦 銀行與現金管理":
  st.header("🏦 銀行帳戶與現金設定")
  new_cash = st.number_input(
      "目前現金總額",
      min_value=0.0,
      value=float(data.get("cash", 0.0)),
      step=100.0,
  )
  if st.button("更新現金金額"):
    data["cash"] = new_cash
    save_data(data)
    st.success("✅ 現金總額更新成功！")

  st.markdown("---")
  with st.form("add_bank_form"):
    bank_name = st.text_input("銀行名稱 (例如：中國信託)")
    bank_balance = st.number_input("當前存款金額", min_value=0.0, step=1000.0)
    submit_bank = st.form_submit_button("儲存銀行帳戶")
    if submit_bank and bank_name:
      data.setdefault("banks", {})[bank_name] = bank_balance
      save_data(data)
      st.success(f"✅ 已成功儲存 {bank_name} 的存款金額！")

# -------------------------------------------------------------------
# 4. 📝 新增日常收支
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
  if