import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading

class BitgetFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bitget 선물 종목 필터")
        self.root.geometry("800x600")

        # 상단 필터 입력 프레임
        filter_frame = ttk.LabelFrame(root, text=" 필터 조건 설정 ")
        filter_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(filter_frame, text="최소 24H 거래대금(USDT):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.min_vol_entry = ttk.Entry(filter_frame, width=15)
        self.min_vol_entry.insert(0, "10000000")  # 기본 1,000만 USDT
        self.min_vol_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(filter_frame, text="최소 24H 변동률(%):").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.min_change_entry = ttk.Entry(filter_frame, width=10)
        self.min_change_entry.insert(0, "-100")
        self.min_change_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(filter_frame, text="최대 24H 변동률(%):").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.max_change_entry = ttk.Entry(filter_frame, width=10)
        self.max_change_entry.insert(0, "100")
        self.max_change_entry.grid(row=0, column=5, padx=5, pady=5)

        # 조회 버튼
        self.search_btn = ttk.Button(filter_frame, text="조회하기", command=self.start_fetch_data)
        self.search_btn.grid(row=0, column=6, padx=10, pady=5)

        # 결과 테이블 (Treeview)
        columns = ("symbol", "price", "change", "high", "low", "volume")
        self.tree = ttk.Treeview(root, columns=columns, show="headings")
        
        self.tree.heading("symbol", text="종목 (Symbol)")
        self.tree.heading("price", text="현재가")
        self.tree.heading("change", text="24H 변동률")
        self.tree.heading("high", text="24H 고가")
        self.tree.heading("low", text="24H 저가")
        self.tree.heading("volume", text="24H 거래대금(USDT)")

        self.tree.column("symbol", anchor="center", width=120)
        self.tree.column("price", anchor="e", width=100)
        self.tree.column("change", anchor="e", width=100)
        self.tree.column("high", anchor="e", width=100)
        self.tree.column("low", anchor="e", width=100)
        self.tree.column("volume", anchor="e", width=160)

        # 스크롤바 추가
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=(10,0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0,10), pady=10)

    def start_fetch_data(self):
        self.search_btn.config(state="disabled")
        threading.Thread(target=self.fetch_and_filter, daemon=True).start()

    def fetch_and_filter(self):
        try:
            min_vol = float(self.min_vol_entry.get())
            min_change = float(self.min_change_entry.get())
            max_change = float(self.max_change_entry.get())

            # Bitget V2 API - 선물 Ticker 조회
            url = "https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES"
            res = requests.get(url, timeout=10).json()

            if res.get("code") != "00000":
                raise Exception(res.get("msg", "API 호출 실패"))

            tickers = res.get("data", [])

            # 기존 데이터 삭제
            for row in self.tree.get_children():
                self.tree.delete(row)

            # 필터링 및 데이터 추가
            for t in tickers:
                symbol = t.get("symbol", "")
                price = float(t.get("lastPr", 0))
                change_pct = float(t.get("change24h", 0)) * 100
                high = float(t.get("high24h", 0))
                low = float(t.get("low24h", 0))
                volume = float(t.get("usdtVolume", 0))

                # 조건 필터링
                if volume >= min_vol and (min_change <= change_pct <= max_change):
                    self.tree.insert("", "end", values=(
                        symbol,
                        f"{price:,.4f}",
                        f"{change_pct:+.2f}%",
                        f"{high:,.4f}",
                        f"{low:,.4f}",
                        f"{volume:,.0f}"
                    ))

        except ValueError:
            messagebox.showerror("입력 오류", "숫자 형식으로 올바르게 입력해주세요.")
        except Exception as e:
            messagebox.showerror("오류 발생", str(e))
        finally:
            self.search_btn.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = BitgetFilterApp(root)
    root.mainloop()
