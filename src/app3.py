"""
Project: Dynamic Wind Profile Visualizer
Version: 2.4 (Stable Vector Mode)
Last Updated: 2026-04-01

Execution Command:
------------------
streamlit run src/app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

# --- 1. 環境初始化與路徑配置 ---
# 使用 Pathlib 確保在 Windows 環境下（如 K: 或 J: 槽）路徑能正確解析
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "wind_data_master.parquet"

st.set_page_config(page_title="Professional Wind Visualizer", layout="wide")

@st.cache_data
def load_data():
    """載入 Parquet 數據並預處理時間標籤"""
    if not DATA_PATH.exists():
        st.error(f"數據檔案缺失: {DATA_PATH}")
        st.stop()
    df = pd.read_parquet(DATA_PATH)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    # 建立用於 Slider 的時間顯示字串
    df['time_label'] = df['timestamp'].dt.strftime('%H:%M:%S')
    return df

def main():
    df = load_data()
    
    # 使用純黑標題，提升專業儀表板質感
    st.markdown("<h2 style='text-align: center; color: #000000;'>🌬️ 垂直風場動態演繹 (Vector Analysis Mode)</h2>", unsafe_allow_html=True)

    # --- 2. 側邊欄控制面板 ---
    st.sidebar.header("⚙️ 控制面板")
    
    # 日期選擇器
    available_dates = sorted(df['timestamp'].dt.date.unique())
    selected_date = st.sidebar.selectbox("觀測日期", available_dates)

    # 動畫播放參數：預設 200ms 以獲得平滑視覺體驗
    frame_dur = st.sidebar.select_slider("⚡ 播放速度 (ms/frame)", options=[500, 200, 100, 80, 50, 30], value=200)
    
    # 物理量邊界設定
    max_h_limit = st.sidebar.slider("📏 高度上限 (m)", 500, 6000, 2000, step=100)
    max_v_limit = st.sidebar.slider("🌬️ 風速上限 (m/s)", 5, 80, 40, step=1)
    
    # 向量視覺比例控制：預設 18.5
    arrow_scale = st.sidebar.slider("📐 箭頭整體大小", 4.0, 35.0, 18.5, step=0.5)

    # 數據過濾：僅保留選定日期與高度範圍內的資料
    day_df = df[df['timestamp'].dt.date == selected_date].copy()
    plot_df = day_df[day_df['height'] <= max_h_limit].reset_index(drop=True)

    if plot_df.empty:
        st.warning("該日期或高度範圍內無有效數據")
        return

    unique_times = sorted(plot_df['time_label'].unique())

    # --- 3. 核心繪圖邏輯：標量曲線與向量場 ---
    def get_traces(data_slice):
        # 藍色曲線：代表風速的大小 (Scalar Magnitude)
        line_trace = go.Scatter(
            x=data_slice['speed'], y=data_slice['height'],
            mode='lines+markers', name='風速 (m/s)',
            line=dict(color='#00d1ff', width=3),
            marker=dict(size=5, color='#00d1ff')
        )

        tail_x, tail_y = [], []
        head_x, head_y = [], []
        angles = []
        
        # 向量抽樣密度：每 3 個數據點繪製一個向量，避免畫面過於擁擠
        sample = data_slice.iloc[::3]

        for _, row in sample.iterrows():
            x0 = float(row['speed'])
            y0 = float(row['height'])
            direction = float(row['direction'])

            # 物理座標轉換：氣象 0 度為正北，Plotly 極座標補償 -90 度
            theta = np.deg2rad(direction - 90)
            length = arrow_scale * 0.22  # 向量恆定長度係數

            # 計算向量終點偏移量
            dx = length * np.cos(theta)
            dy = length * np.sin(theta)

            # 構建不連續線段數據：[起點, 終點, None] 循環以提升渲染效率
            tail_x.extend([x0, x0 + dx, None])
            tail_y.extend([y0, y0 + dy, None])
            
            # 儲存箭頭頭部位置
            head_x.append(x0 + dx)
            head_y.append(y0 + dy)
            # 箭頭旋轉角度，配合 angleref='up'
            angles.append(direction - 90)

        # 向量紅線：代表箭身 (Tail)
        tail_trace = go.Scatter(
            x=tail_x, y=tail_y, mode='lines',
            line=dict(color='#ff4b4b', width=3.2),
            showlegend=False, hoverinfo='skip'
        )

        # 向量箭頭：代表指向 (Head)
        head_trace = go.Scatter(
            x=head_x, y=head_y, mode='markers',
            marker=dict(
                symbol='arrow', angle=angles, angleref='up',
                size=arrow_scale * 1.35, color='#ff4b4b'
            ),
            showlegend=False,
            customdata=sample['direction'].values,
            hovertemplate="高度: %{y:.0f} m<br>風向: %{customdata:.0f}°<extra></extra>"
        )

        return [line_trace, tail_trace, head_trace]

    # --- 4. 構建動畫圖表 ---
    init_traces = get_traces(plot_df[plot_df['time_label'] == unique_times[0]])
    # 建立每一時間步的動畫幀
    frames = [go.Frame(data=get_traces(plot_df[plot_df['time_label'] == t]), name=t) for t in unique_times]

    fig = go.Figure(
        data=init_traces,
        frames=frames,
        layout=go.Layout(
            xaxis=dict(range=[0, max_v_limit], title="Wind Speed (m/s)", gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(range=[0, max_h_limit], title="Height (m)", gridcolor='rgba(255,255,255,0.1)'),
            template="plotly_dark",
            height=820,
            margin=dict(l=80, r=40, t=100, b=170),
            # 播放控制器與按鈕設定
            updatemenus=[{
                "type": "buttons", "x": 0.08, "y": -0.13,
                "buttons": [
                    {"label": "▶ 播放", "method": "animate", 
                     "args": [None, {"frame": {"duration": frame_dur, "redraw": True}, "fromcurrent": True}]},
                    {"label": "❚❚ 暫停", "method": "animate", 
                     "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]}
                ]
            }],
            # 時間軸拖動條
            sliders=[{
                "active": 0, "y": -0.19, "x": 0.1, "len": 0.88,
                "currentvalue": {"prefix": "時刻: ", "font": {"size": 18, "color": "#00d1ff"}},
                "steps": [
                    {"args": [[t], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}], 
                     "label": t, "method": "animate"} for t in unique_times
                ]
            }]
        )
    )

    # 將 Plotly 圖表渲染至 Streamlit 介面
    st.plotly_chart(fig, width="stretch", key="wind_v24_final")

if __name__ == "__main__":
    main()