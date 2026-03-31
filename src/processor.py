"""
Project: Dynamic Wind Profile Visualizer
Module: Data Processor (ETL)
Description: Converts raw .hpl wind data files into a consolidated Parquet format.
             Features: 
             - Automatic Project Root Detection.
             - GUI Folder Selection (Tkinter).
             - Meteorological Vector Calculation (u, v).
             - Versioned Change Log.

Version: 1.1.3
Last Updated: 2026-03-31

Change Log:
-----------
v1.1.3 (2026-03-31):
    - Fixed SyntaxWarning: invalid escape sequence '\m' and '\s'.
    - Applied raw string literals (r"") to all paths and regex patterns.
v1.1.2 (2026-03-31):
    - Implemented Dynamic Path Discovery.
    - Aligned with project root at J:\\mypython\\Dynamic wind data visualization.
v1.1.1 (2026-03-31):
    - Added Tkinter GUI for interactive folder selection.
v1.0.0 (Initial):
    - Basic CSV parsing logic.
"""

import pandas as pd
import numpy as np
import os
import re
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import sys

class WindDataProcessor:
    __version__ = "1.1.3"

    def __init__(self):
        # 1. 自動偵測專案根目錄
        # 使用 resolve() 取得絕對路徑，避免轉義字元問題
        current_script = Path(__file__).resolve()
        self.project_root = current_script.parents[1]
        
        # 2. 設定輸出路徑 (使用 Path 物件自動處理斜線)
        self.processed_dir = self.project_root / "data" / "processed"
        
        # 確保資料夾存在
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始狀態
        self.raw_dir = None
        
        print(f"[*] 系統啟動 - 版本: v{self.__version__}")
        print(f"[*] 專案根目錄定位於: {self.project_root}")

    def select_folder(self):
        """彈出 GUI 視窗讓使用者選擇原始數據資料夾"""
        root = tk.Tk()
        root.withdraw()  # 隱藏主視窗
        root.attributes('-topmost', True)  # 確保彈跳視窗在最上層
        
        selected_path = filedialog.askdirectory(
            title=f"Wind Visualizer v{self.__version__} - 請選取包含 .hpl 檔案的資料夾"
        )
        root.destroy()
        
        if selected_path:
            self.raw_dir = Path(selected_path)
            print(f"[*] 已載入原始數據路徑: {self.raw_dir}")
            return True
        else:
            print("[!] 操作取消：未選取任何資料夾。")
            return False

    def parse_filename(self, filename):
        """從檔名提取時間戳 (使用原始字串 r"" 避免 \d 轉義錯誤)"""
        match = re.search(r'(\d{8})_(\d{6})', filename)
        if match:
            return pd.to_datetime(f"{match.group(1)} {match.group(2)}")
        return None

    def run_conversion(self):
        print("\n" + "="*50)
        print(f"開始執行數據轉換程序 (ETL Process)")
        print("="*50)
        
        # 要求使用者選擇資料夾
        if not self.select_folder():
            return
        
        all_data = []
        # 搜尋並排序所有 .hpl 檔案
        file_list = sorted(list(self.raw_dir.glob("*.hpl")))
        
        if not file_list:
            print(f"[ERROR] 找不到 .hpl 檔案於: {self.raw_dir}")
            return

        print(f"[*] 發現 {len(file_list)} 個觀測檔案，準備處理中...")

        for file in file_list:
            timestamp = self.parse_filename(file.name)
            if timestamp is None:
                continue
                
            try:
                # 讀取數據 (使用 r'\s+' 修正 SyntaxWarning)
                # 原始格式：高度(m) | 風向(deg) | 風速(m/s)
                df = pd.read_csv(file, skiprows=1, sep=r'\s+', 
                                 names=['height', 'direction', 'speed'])
                
                # 數據清洗：移除可能的 NaN 值
                df = df.dropna()
                
                # 附加時間標籤
                df['timestamp'] = timestamp
                
                # 計算向量分量 (氣象學慣用定義)
                rad = np.deg2rad(df['direction'])
                df['u'] = -df['speed'] * np.sin(rad)
                df['v'] = -df['speed'] * np.cos(rad)
                
                all_data.append(df)
                
            except Exception as e:
                print(f"[SKIP] 檔案 {file.name} 處理異常: {e}")

        if all_data:
            # 合併所有 DataFrame 並進行排序
            final_df = pd.concat(all_data).sort_values(['timestamp', 'height'])
            
            # 定義輸出檔案路徑
            output_file = self.processed_dir / "wind_data_master.parquet"
            
            # 存儲為 Parquet
            final_df.to_parquet(
                output_file, 
                engine='pyarrow', 
                index=False, 
                compression='snappy'
            )
            
            print("\n" + "-"*50)
            print(f"任務完成！")
            print(f"輸出位置: {output_file}")
            print(f"總處理行數: {len(final_df):,}")
            print(f"時間範圍: {final_df['timestamp'].min()} 至 {final_df['timestamp'].max()}")
            print("-"*50)
        else:
            print("[!] 未能產出有效數據。")

if __name__ == "__main__":
    try:
        processor = WindDataProcessor()
        processor.run_conversion()
    except Exception as fatal_error:
        print(f"[FATAL ERROR] 程式發生未預期的崩潰: {fatal_error}")