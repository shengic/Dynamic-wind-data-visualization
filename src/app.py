"""
Project: Dynamic Wind Profile Visualizer
Version: 3.2.2 (Final Visual Polish)
Execution Command: streamlit run src/app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

# --- 1. 環境初始化 ---
CURRENT_SCRIPT = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_SCRIPT.parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

st.set_page_config(page_title="Professional Wind Dashboard", layout="wide")

# --- 2. 注入自定義 CSS (精確控制按鈕顏色與字體) ---
st.markdown("""
<style>
    /* 設定按鈕為淺灰色背景，並減少邊框干擾 */
    .updatemenu-button {
        fill: #F5F5F5 !important;      /* 淺灰色背景 (White Smoke) */
        stroke: #CCCCCC !important;    /* 柔和的灰色邊框 */
        stroke-width: 0.5px !important;
    }
    
    /* 修正文字：使用簡單字體，取消加粗以防模糊，顏色改為深灰 */
    .updatemenu-item-text {
        fill: #333333 !important;      /* 深灰色文字 */
        font-family: "Arial", "Helvetica", sans-serif !important; 
        font-weight: 400 !important;   /* 標準字重，不加粗 */
        font-size: 14px !important;
    }
    
    /* 修正播放/暫停圖示顏色 */
    .updatemenu-symbol {
        fill: #333333 !important;
    }
</style>
""", unsafe_allow_html=True)

def get_parquet_files():
    if not PROCESSED_DIR.exists():
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    return {f.name: f for f in sorted(list(PROCESSED_DIR.glob("wind_data_*.parquet")), reverse=True)}

@st.cache_data(show_spinner=False)
def load_data(file_path):
    df = pd.read_parquet(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['time_label'] = df['timestamp'].dt.strftime('%H:%M:%S')
    return df

# --- 3. 繪圖核心邏輯 (Frames 模式) ---
def get_traces(data_slice, v_max, h_max, a_size):
    # 確保數據類型正確
    if not isinstance(data_slice, pd.DataFrame):
        return []

    speed_trace = go.Scatter(
        x=data_slice['speed'], y=data_slice['height'],
        mode='lines', name='Wind Speed',
        fill='tozerox', fillcolor='rgba(0, 209, 255, 0.1)',
        line=dict(color='#00d1ff', width=3, shape='spline'),
        hovertemplate="風速: %{x:.1f} m/s<br>高度: %{y} m<extra></extra>"
    )

    sample = data_slice.iloc[::4]
    CONST_LEN = v_max * 0.08 
    y_aspect_fix = h_max / v_max 

    tail_x, tail_y, head_x, head_y, angles = [], [], [], [], []
    for _, row in sample.iterrows():
        x0, y0, ang = float(row['speed']), float(row['height']), float(row['direction'])
        theta_rad = np.deg2rad(ang)
        dx = CONST_LEN * np.sin(theta_rad)
        dy = (CONST_LEN * y_aspect_fix) * np.cos(theta_rad) * 0.12 
        tail_x.extend([x0, x0 + dx, None]); tail_y.extend([y0, y0 + dy, None])
        head_x.append(x0 + dx); head_y.append(y0 + dy); angles.append(ang)

    tail_trace = go.Scatter(x=tail_x, y=tail_y, mode='lines', line=dict(color='#ff4b4b', width=2.5), showlegend=False, hoverinfo='skip')
    head_trace = go.Scatter(x=head_x, y=head_y, mode='markers', marker=dict(symbol='arrow', angle=angles, angleref='up', size=a_size, color='#ff4b4b'), showlegend=False)
    
    max_idx = data_slice['speed'].idxmax()
    max_row = data_slice.loc[max_idx]
    max_mark = go.Scatter(x=[max_row['speed']], y=[max_row['height']], mode='markers+text', text=[f" Max: {max_row['speed']:.1f}"], textposition="top right", marker=dict(color='white', size=7, symbol='circle-open'), showlegend=False)

    return [speed_trace, tail_trace, head_trace, max_mark]

def main():
    st.markdown("<h2 style='text-align: center; color: #000000;'>🌪️ 大氣垂直風場動態分析系統</h2>", unsafe_allow_html=True)

    file_dict = get_parquet_files()
    if not file_dict:
        st.warning("數據目錄為空。請先執行 processor.py。")
        return

    # --- 4. 側邊欄控制面板 ---
    st.sidebar.header("📁 數據來源")
    selected_file = st.sidebar.selectbox("選擇觀測日期檔案", list(file_dict.keys()))
    full_df = load_data(file_dict[selected_file])

    st.sidebar.divider()
    st.sidebar.header("⚙️ 控制面板")
    frame_dur = st.sidebar.select_slider("⚡ 播放速度 (ms)", options=[500, 200, 100, 80, 50, 30], value=200)
    max_h = st.sidebar.slider("📏 高度上限 (m)", 500, 6000, 2000, 100)
    max_v = st.sidebar.slider("🌬️ 風速上限 (m/s)", 10, 80, 40)
    arrow_head_size = st.sidebar.slider("📐 箭頭頭部尺寸", 5.0, 35.0, 18.5, step=0.5)

    plot_df = full_df[full_df['height'] <= max_h].reset_index(drop=True)
    unique_times = sorted(plot_df['time_label'].unique())

    # --- 5. 構建 Figure ---
    init_data_slice = plot_df[plot_df['time_label'] == unique_times[0]]
    init_traces = get_traces(init_data_slice, max_v, max_h, arrow_head_size)
    
    # 建立動畫幀
    frames = [go.Frame(data=get_traces(plot_df[plot_df['time_label'] == t], max_v, max_h, arrow_head_size), name=t) for t in unique_times]

    fig = go.Figure(
        data=init_traces,
        frames=frames,
        layout=go.Layout(
            xaxis=dict(range=[0, max_v], title="Wind Speed (m/s)", gridcolor='rgba(255,255,255,0.08)'),
            yaxis=dict(range=[0, max_h], title="Height (m)", gridcolor='rgba(255,255,255,0.08)'),
            template="plotly_dark", height=850,
            margin=dict(l=60, r=60, t=120, b=100),
            updatemenus=[{
                "type": "buttons",
                "x": 0.05, "y": 1.08, "xanchor": "left", "yanchor": "top",
                "showactive": False, "direction": "left",    
                "buttons": [
                    {"label": "▶ 播放", "method": "animate", "args": [None, {"frame": {"duration": frame_dur, "redraw": True}, "fromcurrent": True}]},
                    {"label": "❚❚ 暫停", "method": "animate", "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]}
                ]
            }],
            sliders=[{
                "active": 0, "y": -0.05, "x": 0.05, "len": 0.95,
                "currentvalue": {"prefix": "時刻: ", "font": {"size": 20, "color": "#00d1ff"}},
                "steps": [{"args": [[t], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}], "label": t, "method": "animate"} for t in unique_times]
            }]
        )
    )

    st.plotly_chart(fig, width="stretch", key="final_wind_v322")

if __name__ == "__main__":
    main()