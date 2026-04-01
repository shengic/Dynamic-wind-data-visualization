"""
Project: Dynamic Wind Profile Visualizer
Version: 2.9.4 (Default Values & Black Title)
Description: 調整啟動預設值：播放速度 200ms、高度上限 2000m、風速上限 40m/s、箭頭尺寸 18.5。
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

# --- 1. 路徑與初始化 ---
CURRENT_SCRIPT = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_SCRIPT.parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

st.set_page_config(page_title="Professional Wind Dashboard", layout="wide")

def get_parquet_files():
    if not PROCESSED_DIR.exists():
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    return {f.name: f for f in sorted(list(PROCESSED_DIR.glob("wind_data_*.parquet")), reverse=True)}

@st.cache_data
def load_data(file_path):
    df = pd.read_parquet(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['time_label'] = df['timestamp'].dt.strftime('%H:%M:%S')
    return df

def main():
    # 修改：主標題顏色改為黑色 (Black)
    st.markdown("<h2 style='text-align: center; color: #000000;'>🌪️ 大氣垂直風場動態分析系統</h2>", unsafe_allow_html=True)

    file_dict = get_parquet_files()
    if not file_dict:
        st.warning("請先執行 processor.py 生成數據。")
        return

    selected_file = st.sidebar.selectbox("📅 選擇觀測日期", list(file_dict.keys()))
    df = load_data(file_dict[selected_file])

    st.sidebar.divider()
    
    # --- 2. 側邊欄控制 (設定截圖中的預設值) ---
    st.sidebar.header("⚙️ 控制面板")
    
    # 播放速度預設 200ms
    frame_dur = st.sidebar.select_slider(
        "⚡ 播放速度 (ms)", 
        options=[500, 200, 100, 80, 50, 30], 
        value=200
    )
    
    # 高度上限預設 2000m
    max_h = st.sidebar.slider("📏 高度上限 (m)", 500, 6000, 2000, 100)
    
    # 風速上限預設 40m/s
    max_v = st.sidebar.slider("🌬️ 風速上限 (m/s)", 10, 80, 40)
    
    # 箭頭頭部尺寸預設 18.5
    arrow_head_size = st.sidebar.slider("📐 箭頭頭部尺寸", 5.0, 35.0, 18.5, step=0.5)

    plot_df = df[df['height'] <= max_h].reset_index(drop=True)
    unique_times = sorted(plot_df['time_label'].unique())

    # --- 3. 繪圖核心邏輯 (固定長度向量) ---
    def get_traces(data_slice):
        speed_trace = go.Scatter(
            x=data_slice['speed'], y=data_slice['height'],
            mode='lines', name='Wind Speed',
            fill='tozerox', fillcolor='rgba(0, 209, 255, 0.1)',
            line=dict(color='#00d1ff', width=3, shape='spline'),
            hovertemplate="風速: %{x:.1f} m/s<br>高度: %{y} m<extra></extra>"
        )

        tail_x, tail_y, head_x, head_y, angles = [], [], [], [], []
        sample = data_slice.iloc[::4]

        # 向量物理長度計算
        CONST_LEN = max_v * 0.08 
        y_aspect_fix = max_h / max_v 

        for _, row in sample.iterrows():
            x0, y0, ang = float(row['speed']), float(row['height']), float(row['direction'])
            theta_rad = np.deg2rad(ang)
            
            dx = CONST_LEN * np.sin(theta_rad)
            dy = (CONST_LEN * y_aspect_fix) * np.cos(theta_rad) * 0.12 

            tail_x.extend([x0, x0 + dx, None])
            tail_y.extend([y0, y0 + dy, None])
            head_x.append(x0 + dx)
            head_y.append(y0 + dy)
            angles.append(ang)

        tail_trace = go.Scatter(
            x=tail_x, y=tail_y, mode='lines',
            line=dict(color='#ff4b4b', width=2.5),
            showlegend=False, hoverinfo='skip'
        )

        head_trace = go.Scatter(
            x=head_x, y=head_y, mode='markers',
            marker=dict(
                symbol='arrow', angle=angles, angleref='up',
                size=arrow_head_size, color='#ff4b4b'
            ),
            showlegend=False,
            customdata=sample['direction'].values,
            hovertemplate="風向: %{customdata:.0f}°<extra></extra>"
        )

        # 最大風速標註
        max_idx = data_slice['speed'].idxmax()
        max_row = data_slice.loc[max_idx]
        max_mark = go.Scatter(
            x=[max_row['speed']], y=[max_row['height']],
            mode='markers+text', text=[f"  Max: {max_row['speed']:.1f}"],
            textposition="top right", marker=dict(color='white', size=7, symbol='circle-open'),
            showlegend=False
        )

        return [speed_trace, tail_trace, head_trace, max_mark]

    # --- 4. 構建 Figure ---
    init_data = plot_df[plot_df['time_label'] == unique_times[0]]
    fig = go.Figure(
        data=get_traces(init_data),
        frames=[go.Frame(data=get_traces(plot_df[plot_df['time_label'] == t]), name=t) for t in unique_times],
        layout=go.Layout(
            xaxis=dict(range=[0, max_v], title="Wind Speed (m/s)", gridcolor='rgba(255,255,255,0.08)'),
            yaxis=dict(range=[0, max_h], title="Height (m)", gridcolor='rgba(255,255,255,0.08)'),
            template="plotly_dark", height=850,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=60, r=60, t=60, b=160),
            updatemenus=[{
                "type": "buttons", "x": 0.05, "y": -0.12, "xanchor": "left",
                "buttons": [
                    {"label": "▶ 播放", "method": "animate", "args": [None, {"frame": {"duration": frame_dur, "redraw": True}, "fromcurrent": True}]},
                    {"label": "❚❚ 暫停", "method": "animate", "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]}
                ]
            }],
            sliders=[{
                "active": 0, "y": -0.12, "x": 0.12, "len": 0.88,
                "currentvalue": {"prefix": "時刻: ", "font": {"size": 20, "color": "#00d1ff"}},
                "steps": [{"args": [[t], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}], "label": t, "method": "animate"} for t in unique_times]
            }]
        )
    )

    st.plotly_chart(fig, width="stretch", key="pro_dashboard_v294")

if __name__ == "__main__":
    main()