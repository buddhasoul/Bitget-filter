import tkinter as tk
from tkinter import ttk, messagebox
import requests
import pandas as pd
from datetime import datetime
import threading

class BitgetAdvanceFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bitget 선물 종목 상세 필터 및 정렬")
        self.root.geometry("1180x700")

        # 원본 전체 데이터를 저장할 리스트
        self.all_data = []
        self.sort_state = {}  # 컬럼별 정렬 상태 (True: 오름차순, False: 내림차순)

        # UI 필터 설정 영역
        filter_frame = ttk.LabelFrame(root, text=" 필터 조건 설정 (체크된 항목만 적용됩니다) ")
        filter_frame.pack(fill="x", padx=10, pady=5)

        # Row 0: 현재가, ATH 하락률, 거래량 배수
        self.chk_price_var = tk.BooleanVar(value=False)
        self.chk_price = ttk.Checkbutton(filter_frame, text="최대 현재가(USDT 이하):", variable=self.chk_price_var)
        self.chk_price.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.max_price_entry = ttk.Entry(filter_frame, width=10)
        self.max_price_entry.insert(0, "10.0")
        self.max_price_entry.grid(row=0, column=1, padx=5, pady=5)

        self.chk_drop_var = tk.BooleanVar(value=False)
        self.chk_drop = ttk.Checkbutton(filter_frame, text="최소 ATH 대비 하락률(% 이상 하락):", variable=self.chk_drop_var)
        self.chk_drop.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.min_drop_entry = ttk.Entry(filter_frame, width=10)
        self.min_drop_entry.insert(0, "50.0")
        self.min_drop_entry.grid(row=0, column=3, padx=5, pady=5)

        self.chk_vol_var = tk.BooleanVar(value=False)
        self.chk_vol = ttk.Checkbutton(filter_frame, text="최소 30일 평균 대비 거래량 배수:", variable=self.chk_vol_var)
        self.chk_vol.grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.min_vol_mult_entry = ttk.Entry(filter_frame, width=10)
        self.min_vol_mult_entry.insert(0, "2.0")
        self.min_vol_mult_entry.grid(row=0, column=5, padx=5, pady=5)

        # Row 1: 최대 거래량 발생일, 상장일 조건
        self.chk_max_vol_date_var = tk.BooleanVar(value=False)
        self.chk_max_vol_date = ttk.Checkbutton(filter_frame, text="최대 거래량 발생일 (이후, YYYY-MM-DD):", variable=self.chk_max_vol_date_var)
        self.chk_max_vol_date.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.max_vol_date_entry = ttk.Entry(filter_frame, width=10)
        self.max_vol_date_entry.insert(0, "2024-01-01")
        self.max_vol_date_entry.grid(row=1, column=1, padx=5, pady=5)

        self.chk_listing_date_var = tk.BooleanVar(value=False)
        self.chk_listing_date = ttk.Checkbutton(filter_frame, text="상장일 (이후, YYYY-MM-DD):", variable=self.chk_listing_date_var)
        self.chk_listing_date.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.listing_date_entry = ttk.Entry(filter_frame, width=10)
        self.listing_date_entry.insert(0, "2024-01-01")
        self.listing_date_entry.grid(row=1, column=3, padx=5, pady=5)

        # 버튼 영역
        btn_frame = ttk.Frame(filter_frame)
        btn_frame.grid(row=1, column=4, columnspan=2, padx=5, pady=5, sticky="e")

        self.apply_filter_btn = ttk.Button(btn_frame, text="필터 적용", command=self.apply_filter)
        self.apply_filter_btn.pack(side="left", padx=2)

        self.reset_filter_btn = ttk.Button(btn_frame, text="전체 초기화", command=self.reset_display)
        self.reset_filter_btn.pack(side="left", padx=2)

        self.status_label = ttk.Label(root, text="데이터 수집 준비 중...", foreground="blue")
        self.status_label.pack(anchor="w", padx=10, pady=2)

        # 결과 그리드 (Treeview)
        self.columns = ("symbol", "price", "ath_price", "ath_drop", "vol_mult", "max_vol_date", "listing_date")
        self.tree = ttk.Treeview(root, columns=self.columns, show="headings")

        # 헤더 텍스트 및 클릭 이벤트 등록 (클릭 시 정렬)
        self.col_names = {
            "symbol": "종목명",
            "price": "현재가",
            "ath_price": "실제 ATH",
            "ath_drop": "ATH 대비 하락률",
            "vol_mult": "30일 평균대비 거래량 배수",
            "max_vol_date": "최대 거래량 발생일",
            "listing_date": "실제 상장일"
        }

        for col in self.columns:
            self.tree.heading(col, text=self.col_names[col], command=lambda c=col: self.sort_by_column(c))
            self.sort_state[col] = False  # 초기 정렬 방향 설정

        self.tree.column("symbol", anchor="center", width=110)
        self.tree.column("price", anchor="e", width=100)
        self.tree.column("ath_price", anchor="e", width=100)
        self.tree.column("ath_drop", anchor="e", width=120)
        self.tree.column("vol_mult", anchor="e", width=160)
        self.tree.column("max_vol_date", anchor="center", width=130)
        self.tree.column("listing_date", anchor="center", width=130)

        scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

        # 프로그램 실행 시 바로 데이터 불러오기
        self.start_initial_fetch()

    def get_full_history_ath(self, symbol):
        """과거 전체 데이터를 역추적하여 진짜 ATH(역사적 고점) 조회"""
        max_ath = 0.0
        end_time = None
        
        # 최대 3회(3,000일 ≈ 8년) 데이터 역추적
        for _ in range(3):
            url = f"https://api.bitget.com/api/v2/mix/market/candles?symbol={symbol}&granularity=1D&limit=1000&productType=USDT-FUTURES"
            if end_time:
                url += f"&endTime={end_time}"
                
            res = requests.get(url, timeout=5).json()
            if res.get("code") != "00000" or not res.get("data"):
                break
                
            candles = res["data"]
            if not candles:
                break
                
            highs = [float(c[2]) for c in candles]
            current_max = max(highs)
            if current_max > max_ath:
                max_ath = current_max
                
            # 가장 오래된 봉의 타임스탬프를 다음 요청의 endTime으로 설정
            earliest_ts = int(candles[-1][0])
            end_time = earliest_ts - 1
            
            if len(candles) < 1000:
                break
                
        return max_ath

    def start_initial_fetch(self):
        self.apply_filter_btn.config(state="disabled")
        threading.Thread(target=self.fetch_all_data, daemon=True).start()

    def fetch_all_data(self):
        try:
            # 1. 실제 상장일 정보 받아오기
            self.status_label.config(text="비트겟 선물 상장 정보 조회 중...")
            contracts_url = "https://api.bitget.com/api/v2/mix/market/contracts?productType=USDT-FUTURES"
            c_res = requests.get(contracts_url, timeout=10).json()

            symbol_launch_map = {}
            if c_res.get("code") == "00000":
                for item in c_res.get("data", []):
                    sym = item.get("symbol")
                    launch_ts = item.get("launchTime")
                    if launch_ts and str(launch_ts).isdigit():
                        symbol_launch_map[sym] = pd.to_datetime(int(launch_ts), unit='ms').strftime("%Y-%m-%d")

            tickers_url = "https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES"
            res = requests.get(tickers_url, timeout=10).json()

            if res.get("code") != "00000":
                raise Exception("종목 목록을 받아올 수 없습니다.")

            symbols = [t["symbol"] for t in res.get("data", [])]
            total_symbols = len(symbols)

            fetched_list = []

            # 2. 모든 종목의 데이터 수집
            for idx, symbol in enumerate(symbols, 1):
                self.status_label.config(text=f"전체 종목 수집 중... [{idx}/{total_symbols}] {symbol}")

                # 최근 1000일 봉 데이터 (현재가, 최근 30일 거래량, 최대 거래량 발생일 추출용)
                kline_url = f"https://api.bitget.com/api/v2/mix/market/candles?symbol={symbol}&granularity=1D&limit=1000&productType=USDT-FUTURES"
                k_res = requests.get(kline_url, timeout=5).json()

                if k_res.get("code") != "00000" or not k_res.get("data"):
                    continue

                candles = k_res["data"]
                df = pd.DataFrame(candles, columns=['ts', 'open', 'high', 'low', 'close', 'volume', 'quote_volume'])
                df['ts'] = pd.to_datetime(pd.to_numeric(df['ts']), unit='ms')
                df['high'] = pd.to_numeric(df['high'])
                df['close'] = pd.to_numeric(df['close'])
                df['volume'] = pd.to_numeric(df['volume'])
                df = df.sort_values('ts').reset_index(drop=True)

                if len(df) == 0:
                    continue

                current_price = df['close'].iloc[-1]
                
                # 전체 히스토리 추적으로 정확한 ATH 수집
                ath_price = self.get_full_history_ath(symbol)
                if ath_price == 0:
                    ath_price = df['high'].max()
                    
                ath_drop = ((current_price - ath_price) / ath_price) * 100  # 음수 %

                recent_30 = df.tail(30)
                avg_vol_30 = recent_30['volume'].mean()
                current_vol = df['volume'].iloc[-1]
                vol_mult = (current_vol / avg_vol_30) if avg_vol_30 > 0 else 0.0

                max_vol_idx = df['volume'].idxmax()
                max_vol_date = df.loc[max_vol_idx, 'ts']

                # 실제 상장일 확인
                real_listing_str = symbol_launch_map.get(symbol, df['ts'].iloc[0].strftime("%Y-%m-%d"))

                item_data = {
                    "symbol": symbol,
                    "price": current_price,
                    "ath_price": ath_price,
                    "ath_drop": ath_drop,
                    "vol_mult": vol_mult,
                    "max_vol_date": max_vol_date,
                    "max_vol_date_str": max_vol_date.strftime("%Y-%m-%d"),
                    "listing_date_str": real_listing_str,
                    "listing_date": datetime.strptime(real_listing_str, "%Y-%m-%d") if real_listing_str != "N/A" else df['ts'].iloc[0]
                }
                fetched_list.append(item_data)

            self.all_data = fetched_list
            self.root.after(0, self.reset_display)
            self.status_label.config(text=f"수집 완료! 총 {len(self.all_data)}개 종목 로드됨. 헤더를 클릭하여 정렬 가능합니다.")

        except Exception as e:
            messagebox.showerror("수집 오류", str(e))
            self.status_label.config(text="데이터 수집 실패")
        finally:
            self.apply_filter_btn.config(state="normal")

    def populate_tree(self, data_list):
        """테이블 화면 업데이트"""
        for row in self.tree.get_children():
            self.tree.delete(row)

        for d in data_list:
            self.tree.insert("", "end", values=(
                d["symbol"],
                f"{d['price']:,.4f}",
                f"{d['ath_price']:,.4f}",
                f"{d['ath_drop']:.2f}%",
                f"{d['vol_mult']:.2f}배",
                d["max_vol_date_str"],
                d["listing_date_str"]
            ))

    def reset_display(self):
        """필터 없이 전체 데이터 표시"""
        self.populate_tree(self.all_data)
        self.status_label.config(text=f"전체 종목 표시 중 (총 {len(self.all_data)}개)")

    def apply_filter(self):
        """체크박스 조건에 맞춰 데이터 필터링"""
        if not self.all_data:
            return

        try:
            filtered = []
            
            # 필터 조건 값 파싱
            max_price_val = float(self.max_price_entry.get()) if self.chk_price_var.get() else None
            min_drop_val = float(self.min_drop_entry.get()) if self.chk_drop_var.get() else None
            min_vol_mult_val = float(self.min_vol_mult_entry.get()) if self.chk_vol_var.get() else None
            max_vol_date_val = datetime.strptime(self.max_vol_date_entry.get().strip(), "%Y-%m-%d") if self.chk_max_vol_date_var.get() else None
            listing_date_val = datetime.strptime(self.listing_date_entry.get().strip(), "%Y-%m-%d") if self.chk_listing_date_var.get() else None

            for d in self.all_data:
                # 1. 가격 조건
                if max_price_val is not None and d["price"] > max_price_val:
                    continue
                # 2. 하락률 조건 (절댓값 기준 % 이상 하락)
                if min_drop_val is not None and abs(d["ath_drop"]) < min_drop_val:
                    continue
                # 3. 거래량 배수 조건
                if min_vol_mult_val is not None and d["vol_mult"] < min_vol_mult_val:
                    continue
                # 4. 최대 거래량 발생일 조건
                if max_vol_date_val is not None and d["max_vol_date"] < max_vol_date_val:
                    continue
                # 5. 상장일 조건
                if listing_date_val is not None and d["listing_date"] < listing_date_val:
                    continue

                filtered.append(d)

            self.populate_tree(filtered)
            self.status_label.config(text=f"필터 적용 완료: {len(self.all_data)}개 중 {len(filtered)}개 조건 만족")

        except ValueError:
            messagebox.showerror("입력 오류", "입력한 숫자 또는 날짜 포맷(YYYY-MM-DD)을 확인해 주세요.")

    def sort_by_column(self, col):
        """헤더 클릭 시 오름차순/내림차순 정렬"""
        # 현재 화면에 표시되어 있는 항목들 추출
        current_rows = []
        for child in self.tree.get_children():
            values = self.tree.item(child)["values"]
            current_rows.append(values)

        if not current_rows:
            return

        # 정렬 방향 반전
        reverse = self.sort_state[col]
        self.sort_state[col] = not reverse

        # 정렬 키 정의
        col_idx = self.columns.index(col)

        def sort_key(row):
            val = row[col_idx]
            if col in ["price", "ath_price"]:
                return float(str(val).replace(",", ""))
            elif col == "ath_drop":
                return float(str(val).replace("%", ""))
            elif col == "vol_mult":
                return float(str(val).replace("배", ""))
            else:
                return str(val)

        current_rows.sort(key=sort_key, reverse=reverse)

        # 화면 갱신
        for row in self.tree.get_children():
            self.tree.delete(row)

        for row in current_rows:
            self.tree.insert("", "end", values=row)

        # 헤더 표시 업데이트 (▲ / ▼ 표시)
        for c in self.columns:
            arrow = " ▲" if self.sort_state[c] else " ▼"
            title = self.col_names[c] + (arrow if c == col else "")
            self.tree.heading(c, text=title)

if __name__ == "__main__":
    root = tk.Tk()
    app = BitgetAdvanceFilterApp(root)
    root.mainloop()
