# -------------------------------------------------------------------
# 2. 📸 截圖自動辨識持股 (OCR)
# -------------------------------------------------------------------
elif menu == "📸 截圖自動辨識持股":
  st.header("📸 上傳券商持股截圖自動辨識")
  st.write("上傳庫存截圖，系統會自動辨識台股 4 碼代號、買入均價與股數！")

  uploaded_file = st.file_uploader(
      "選擇券商 App 庫存截圖...", type=["jpg", "jpeg", "png"]
  )

  if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="已上傳截圖", use_column_width=True)

    if st.button("🔍 開始辨識截圖內容"):
      with st.spinner("系統辨識中..."):
        try:
          # 自動進行 OCR 文字辨識
          text = pytesseract.image_to_string(image, lang="chi_tra+eng")

          # 抓取 4 碼台股代號 (如 2303, 3234, 6239, 6274)
          found_codes = re.findall(r"\b\d{4}\b", text)
          found_codes = list(dict.fromkeys(found_codes))  # 去重保持順序

          if found_codes:
            st.success(f"🎉 辨識成功！找到股票代號：{', '.join(found_codes)}")

            for code in found_codes:
              symbol = f"{code}.TW"
              name, price = get_stock_info(symbol)

              st.markdown(f"### 📌 {symbol} ({name})")
              with st.form(f"form_ocr_{code}"):
                col1, col2 = st.columns(2)
                buy_price = col1.number_input(
                    "買入均價", value=float(price if price > 0 else 100.0), step=0.5
                )
                shares = col2.number_input("持有股數", value=1000.0, step=100.0)

                if st.form_submit_button(f"➕ 加入 {code} 到持股"):
                  data.setdefault("stocks_tw", []).append({
                      "symbol": symbol,
                      "buy_price": buy_price,
                      "shares": shares,
                  })
                  save_data(data)
                  st.success(f"✅ 已成功加入 {symbol} ({name})！")
                  st.rerun()
          else:
            st.warning("⚠️ 未能清楚辨識出 4 碼股票代號，請確定圖片清晰。")

          with st.expander("查看辨識出的原始文字"):
            st.text(text)

        except Exception as e:
          st.error(f"辨識引擎未就緒，請確定 packages.txt 已推送至 GitHub：{e}")