"""
Project: Dynamic Wind Profile Visualizer
Module: Data Processor (Precise File Filtering & Multi-Date)
Version: 1.2.2
Last Updated: 2026-03-31

Change Log:
-----------
v1.2.2 (2026-03-31):
    - Fixed SyntaxWarning: invalid escape sequence in docstring/comments.
    - Standardized path handling using pathlib to avoid backslash issues.
v1.2.1 (2026-03-31):
    - Refined file search to specific prefix 'Processed_Wind_Profile_*.hpl'.
    - Implemented automatic date grouping for Parquet generation.
"""

import pandas as pd
import numpy as np
import re
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

class WindDataProcessor:
    __version__ = "1.2.2"

    def __init__(self):
        # 動態偵測專案根目錄，使用 resolve() 確保路徑格式正確
        current_script = Path(__file__).resolve()
        self.project_root = current_script.parents[1]
        self.processed_dir = self.project_root / "data" / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir = None

    def select_folder(self):
        """彈出資料夾選取視窗"""
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        selected_path = filedialog.askdirectory(title="請選取原始數據資料夾 (包含 Processed_Wind_Profile 檔案)")
        root.destroy()
        if selected_path:
            self.raw_dir = Path(selected_path)
            return True
        return False

    def parse_filename(self, filename):
        """從檔名提取時間戳，使用 raw string r'' 避免轉義錯誤"""
        match = re.search(r'(\d{8})_(\d{6})', filename)
        if match:
            return pd.to_datetime(f"{match.group(1)} {match.group(2)}")
        return None

    def run_conversion(self):
        print(f"=== Wind Data Processor v{self.__version__} ===")
        
        if not self.select_folder(): 
            return
        
        # 使用 raw string 定義檔案過濾模式
        file_pattern = r"Processed_Wind_Profile_*.hpl"
        all_files = sorted(list(self.raw_dir.glob(file_pattern)))
        
        if not all_files:
            print(f"[!] 錯誤：在 {self.raw_dir} 中找不到符合格式的檔案。")
            return

        print(f"[*] 偵測到 {len(all_files)} 個數據檔案，開始處理...")
        
        all_data = []
        for file in all_files:
            ts = self.parse_filename(file.name)
            if ts is None: 
                continue
            try:
                # 讀取數據：sep 使用 raw string r'\s+'
                df = pd.read_csv(file, skiprows=1, sep=r'\s+', names=['height', 'direction', 'speed'])
                df['timestamp'] = ts
                
                # 預計算向量分量 (u, v)
                rad = np.deg2rad(df['direction'])
                df['u'] = -df['speed'] * np.sin(rad)
                df['v'] = -df['speed'] * np.cos(rad)
                
                all_data.append(df)
            except Exception as e:
                print(f"[跳過] 檔案 {file.name} 讀取失敗: {e}")

        if all_data:
            master_df = pd.concat(all_data)
            # 按日期分組儲存 (YYYYMMDD)
            master_df['date_str'] = master_df['timestamp'].dt.strftime('%Y%m%d')
            
            print("\n--- 正在生成 Parquet 分日檔案 ---")
            for date_str, group in master_df.groupby('date_str'):
                output_file = self.processed_dir / f"wind_data_{date_str}.parquet"
                # 排序並儲存，使用 snappy 壓縮優化讀取效能
                group.sort_values(['timestamp', 'height']).to_parquet(
                    output_file, engine='pyarrow', index=False, compression='snappy'
                )
                print(f"[成功] {output_file.name} | 紀錄數: {len(group):,}")
            print("-" * 40)
        else:
            print("[!] 未能產出任何有效數據。")

if __name__ == "__main__":
    try:
        processor = WindDataProcessor()
        processor.run_conversion()
    except Exception as e:
        print(f"[致命錯誤] 程式崩潰: {e}")