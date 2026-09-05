import tkinter as tk
from tkinter import ttk, messagebox
import requests
import pandas as pd
from datetime import datetime, timedelta
import threading

class BitgetAdvanceFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bitget 선물 일봉 기반 상세 필터")
        self.root.geometry("1100x650")

        # UI 필터 설정 영역
        filter_frame = ttk.LabelFrame(root, text=" 필터 조건 설정 ")
        filter_frame.pack(fill="x", padx=10, pady=5)

        # Row 0: 가격, ATH 하락률, 거래량 배수
        ttk.Label(filter_frame, text="최대 현재가(USDT 이하):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.max_price_entry = ttk.Entry(filter_frame, width=12)
        self.max_price_entry.insert(0, "999999")
        self.max_price_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(filter_frame, text="최소 ATH 대비 하락률(% 이상 하락):").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.min_drop_entry = ttk.Entry(filter_frame, width=10)
        self.min_drop_entry.insert(0, "0")  # 예: 50 입력 시 -50% 이상 하락한 종목
        self.min_drop_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(filter_frame, text="최소 30일 평균 대비 거래량 배수:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.min_vol_mult_entry = ttk.Entry(filter_frame, width=10)
        self.min_vol_mult_entry.insert(0, "1.0")
        self.min_vol_mult_entry.grid(row=0, column=5, padx=5, pady=5)

        # Row 1: 최대 거래량 발생일, 상장일 조건
        ttk.Label(filter_frame, text="최대 거래량 발생일 (이후, YYYY-MM-DD):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.max_vol_date_entry = ttk.Entry(filter_frame, width=12)
        self.max_vol_date_entry.insert(0, "2000-01-01")
        self.max_vol_date_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(filter_frame, text="상장일 (이후, YYYY-MM-DD):").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.listing_date_entry = ttk.Entry(filter_frame, width=10)
        self.listing_date_entry.insert(0, "2000-01-01")
        self.listing_date_entry.grid(row=1, column=3, padx=5, pady=5)

        # 버튼 & 상태 표시
        self.search_btn = ttk.Button(filter_frame, text="데이터 수집 및 필터 실행", command=self.start_fetch)
        self.search_btn.grid(row=1, column=4, columnspan=2, padx=10, pady=5, sticky="ew")

        self.status_label = ttk.Label(root, text="조건 설정 후 실행 버튼을 눌러주세요. (전체 종목 분석 시 10~20초 소요)", foreground="blue")
        self.status_label.pack(anchor="w", padx=10, pady=2)

        # 결과 그리드
        columns = ("symbol", "price", "ath_drop", "vol_mult", "max_vol_date", "listing_date")
        self.tree = ttk.Treeview(root, columns=columns, show="headings")

        self.tree.heading("symbol", text="종목명")
        self.tree.heading("price", text="현재가")
        self.tree.heading("ath_drop", text="ATH 대비 하락률")
        self.tree.heading("vol_mult", text="30일 평균 대비 거래량 배수")
        self.tree.heading("max_vol_date", text="최대 거래량 발생일")
        self.tree.heading("listing_date", text="상장일")

        self.tree.column("symbol", anchor="center", width=120)
        self.tree.column("price", anchor="e", width=100)
        self.tree.column("ath_drop", anchor="e", width=120)
        self.tree.column("vol_mult", anchor="e", width=160)
        self.tree.column("max_vol_date", anchor="center", width=140)
        self.tree.column("listing_date", anchor="center", width=140)

        scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

    def start_fetch(self):
        self.search_btn.config(state="disabled")
        for row in self.tree.get_children():
            self.tree.delete(row)
        threading.Thread(target=self.process_data, daemon=True).start()

    def process_data(self):
        try:
            max_price = float(self.max_price_entry.get())
            min_drop = float(self.min_drop_entry.get())
            min_vol_mult = float(self.min_vol_mult_entry.get())
            max_vol_date_limit = datetime.strptime(self.max_vol_date_entry.get().strip(), "%Y-%m-%d")
            listing_date_limit = datetime.strptime(self.listing_date_entry.get().strip(), "%Y-%m-%d")

            # 1. 전체 선물 종목 가져오기
            self.status_label.config(text="비트겟 선물 종목 목록을 조회하는 중...")
            tickers_url = "https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES"
            res = requests.get(tickers_url, timeout=10).json()

            if res.get("code") != "00000":
                raise Exception("종목 목록을 가져오지 못했습니다.")

            symbols = [t["symbol"] for t in res.get("data", [])]
            total_symbols = len(symbols)

            # 2. 종목별 일봉 데이터 수집 및 분석
            for idx, symbol in enumerate(symbols, 1):
                self.status_label.config(text=f"분석 중... [{idx}/{total_symbols}] {symbol}")

                # 일봉 K-Line 조회 (최대 1000개)
                kline_url = f"https://api.bitget.com/api/v2/mix/market/candles?symbol={symbol}&granularity=1D&limit=1000&productType=USDT-FUTURES"
                k_res = requests.get(kline_url, timeout=5).json()

                if k_res.get("code") != "00000" or not k_res.get("data"):
                    continue

                candles = k_res["data"]
                # 데이터 포맷: [timestamp, open, high, low, close, volume, ...]
                df = pd.DataFrame(candles, columns=['ts', 'open', 'high', 'low', 'close', 'volume', 'quote_volume'])
                df['ts'] = pd.to_datetime(pd.to_numeric(df['ts']), unit='ms')
                df['high'] = pd.to_numeric(df['high'])
                df['close'] = pd.to_numeric(df['close'])
                df['volume'] = pd.to_numeric(df['volume'])
                df = df.sort_values('ts').reset_index(drop=True)

                if len(df) == 0:
                    continue

                # 핵심 지표 계산
                current_price = df['close'].iloc[-1]
                ath_price = df['high'].max()
                ath_drop = ((current_price - ath_price) / ath_price) * 100  # 음수 값

                # 30일 평균 거래량 대비 배수
                recent_30 = df.tail(30)
                avg_vol_30 = recent_30['volume'].mean()
                current_vol = df['volume'].iloc[-1]
                vol_mult = (current_vol / avg_vol_30) if avg_vol_30 > 0 else 0

                # 최대 거래량 발생일
                max_vol_idx = df['volume'].idxmax()
                max_vol_date = df.loc[max_vol_idx, 'ts']

                # 상장일 (데이터 상 첫 일봉 날짜)
                listing_date = df['ts'].iloc[0]

                # 조건 필터링
                cond_price = current_price <= max_price
                cond_drop = abs(ath_drop) >= min_drop
                cond_vol_mult = vol_mult >= min_vol_mult
                cond_max_vol_date = max_vol_date >= max_vol_date_limit
                cond_listing_date = listing_date >= listing_date_limit

                if cond_price and cond_drop and cond_vol_mult and cond_max_vol_date and cond_listing_date:
                    self.tree.insert("", "end", values=(
                        symbol,
                        f"{current_price:,.4f}",
                        f"{ath_drop:.2f}%",
                        f"{vol_mult:.2f}배",
                        max_vol_date.strftime("%Y-%m-%d"),
                        listing_date.strftime("%Y-%m-%d")
                    ))

            self.status_label.config(text=f"완료! 전체 {total_symbols}개 중 조건에 맞는 종목 출력이 끝났습니다.")

        except ValueError:
            messagebox.showerror("입력 오류", "날짜 포맷(YYYY-MM-DD) 또는 숫자 형식을 확인해 주세요.")
        except Exception as e:
            messagebox.showerror("오류 발생", str(e))
        finally:
            self.search_btn.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = BitgetAdvanceFilterApp(root)
    root.mainloop()
