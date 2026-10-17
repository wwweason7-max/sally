from datetime import datetime
import json
import os
import re
import pandas as pd
from PIL import Image, ImageEnhance, ImageFilter
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


def preprocess_image(image):
  """影像增強：轉灰階、提高對比度以增加 OCR 辨識率"""
  img = image.convert("L")  # 轉灰階
  img = ImageEnhance.Contrast(img).enhance(2.0)  # 提高對比
  return img


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
# 2. 📸 截圖自動辨識與調整
# -------------------------------------------------------------------
elif menu == "📸 截圖自動辨識與調整":
  st.header("📸 截圖辨識與手動微調表格")
  st.write(
      "上傳截圖後，系統會自動辨識台股代號、均價與股數。你可以在下方表格中自由修改或新增，無誤後點擊批量匯入！"
  )

  uploaded_file = st.file_uploader(
      "選擇券商 App 庫存截圖...", type=["jpg", "jpeg", "png"]
  )

  if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="已上傳截圖", width=300)

    if st.button("🔍 開始辨識圖片內容"):
      with st.spinner("辨識與處理中..."):
        try:
          # 影像預處理提高辨識精準度
          processed_img = preprocess_image(image)

          # 使用 Tesseract 提取文字
          raw_text = pytesseract.image_to_string(
              processed_img, lang="chi_tra+eng"
          )

          # 抓取 4 碼台股代號
          found_codes = re.findall(r"\b\d{4}\b", raw_text)
          found_codes = list(dict.fromkeys(found_codes))  # 去重

          # 抓取浮點數價格 (例如 135.5, 308.5, 1670)
          prices_found = re.findall(
              r"\b\d{2,4}(?:\.\d{1,2})?\b", raw_text
          )

          editable_data = []
          for idx, code in enumerate(found_codes):
            symbol = f"{code}.TW"
            _, price = get_stock_info(symbol)

            # 如果抓到的價格合理就採用
            estimated_price = (
                float(price)
                if price > 0
                else (
                    float(prices_found[idx])
                    if idx < len(prices_found)
                    else 100.0
                )
            )

            editable_data.append({
                "代號": symbol,
                "買入均價": float(estimated_price),
                "持有股數": 1000.0,
            })

          # 若沒辨識出任何代號，預先載入兩列給使用者手動修改
          if not editable_data:
            editable_data = [
                {"代號": "2303.TW", "買入均價": 135.5, "持有股數": 1000.0},
                {"代號": "3234.TW", "買入均價": 179.0, "持有股數": 1000.0},
            ]

          st.session_state["ocr_table"] = pd.DataFrame(editable_data)
          st.success("🎉 辨識完成！請在下方表格核對與修正資料。")
        except Exception as e:
          st.error(f"解析發生錯誤：{e}")

    if "ocr_table" in st.session_state:
      st.markdown("### ✏️ 修正與調整持股表格")
      st.caption(
          "💡 提示：可直接修改數字/文字。如果表格底部有空白列，系統會自動忽略。"
      )

      edited_df = st.data_editor(
          st.session_state["ocr_table"], num_rows="dynamic", use_container_width=True
      )

      if st.button("🚀 確認無誤，批量加入持股清單"):
        added_count = 0
        for index, row in edited_df.iterrows():
          # 安全檢查：若代號、均價、股數為 None，直接忽略該列
          if (
              pd.isna(row.get("代號"))
              or pd.isna(row.get("買入均價"))
              or pd.isna(row.get("持有股數"))
          ):
            continue

          sym = str(row["代號"]).strip().upper()
          if not sym or sym.lower() == "none":
            continue

          if not sym.endswith(".TW") and sym.isdigit() and len(sym) == 4:
            sym = f"{sym}.TW"

          try:
            b_price = float(row["買入均價"])
            s_shares = float(row["持有股數"])
          except (ValueError, TypeError):
            continue  # 若轉換失敗則安全跳過

          data.setdefault("stocks_tw", []).append({
              "symbol": sym,
              "buy_price": b_price,
              "shares": s_shares,
          })
          added_count += 1

        save_data(data)
        st.success(f"✅ 成功批量匯入 {added_count} 筆持股資料！")
        del st.session_state["ocr_table"]  # 清除 Session 狀態，重置表格

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
  if txs:
    st.dataframe(txs, use_container_width=True)

# -------------------------------------------------------------------
# 5. 📈 手動新增股票
# -------------------------------------------------------------------
elif menu == "📈 手動新增股票":
  st.header("📈 手動新增股票持股")
  stock_market = st.radio("選擇市場", ["🇹🇼 台股", "🇺🇸 美股"])

  with st.form("stock_form"):
    if stock_market == "🇹🇼 台股":
      symbol = st.text_input("台股代號 (如 2330.TW)").upper()
    else:
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
# 6. 🗑️ 資料刪除與管理
# -------------------------------------------------------------------
elif menu == "🗑️ 資料刪除與管理":
  st.header("🗑️ 清理與刪除錯誤資料")

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