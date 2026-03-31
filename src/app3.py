"""
Project: Dynamic Wind Profile Visualizer
Version: 2.4 (Simple Rotating Arrow + Tail - Most Reliable)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="Professional Wind Visualizer", layout="wide")

@st.cache_data
def load_data():
    DATA_PATH = Path("data/processed/wind_data_master.parquet")
    if not DATA_PATH.exists():
        st.error(f"數據檔案缺失: {DATA_PATH}")
        st.stop()
    df = pd.read_parquet(DATA_PATH)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['time_label'] = df['timestamp'].dt.strftime('%H:%M:%S')
    return df


def main():
    df = load_data()
    st.title("🌬️ 專業垂直風場動態演繹 (簡單清晰旋轉箭頭版)")

    st.sidebar.header("⚙️ 控制面板")
    available_dates = sorted(df['timestamp'].dt.date.unique())
    selected_date = st.sidebar.selectbox("觀測日期", available_dates)

    frame_dur = st.sidebar.select_slider("動畫速度 (ms/frame)", options=[500, 200, 100, 80, 50, 30], value=80)

    max_h_limit = st.sidebar.slider("高度上限 (m)", 500, 6000, 3000, step=100)
    max_v_limit = st.sidebar.slider("風速上限 (m/s)", 5, 80, 40, step=1)
    arrow_scale = st.sidebar.slider("箭頭整體大小", 4.0, 25.0, 12.0, step=0.5)

    day_df = df[df['timestamp'].dt.date == selected_date].copy()
    plot_df = day_df[day_df['height'] <= max_h_limit].reset_index(drop=True)

    if plot_df.empty:
        st.warning("該日期無有效數據")
        return

    unique_times = sorted(plot_df['time_label'].unique())

    def get_traces(data_slice):
        # 藍色風速線
        line_trace = go.Scatter(
            x=data_slice['speed'], y=data_slice['height'],
            mode='lines+markers', name='風速 (m/s)',
            line=dict(color='#00d1ff', width=3),
            marker=dict(size=6, color='#00d1ff')
        )

        tail_x, tail_y = [], []
        head_x, head_y = [], []
        angles = []
        sample = data_slice.iloc[::3]   # 調整密度

        for _, row in sample.iterrows():
            x0 = float(row['speed'])
            y0 = float(row['height'])
            direction = float(row['direction'])

            # Change -90 to +90 or 0 if arrows point wrong way
            theta = np.deg2rad(direction - 90)

            length = arrow_scale * 0.22   # fixed length

            dx = length * np.cos(theta)
            dy = length * np.sin(theta)

            # Tail (short line)
            tail_x.extend([x0, x0 + dx, None])
            tail_y.extend([y0, y0 + dy, None])

            # Arrow head position
            head_x.append(x0 + dx)
            head_y.append(y0 + dy)
            angles.append(direction - 90)

        # Tail trace
        tail_trace = go.Scatter(
            x=tail_x, y=tail_y, mode='lines',
            line=dict(color='#ff4b4b', width=3.2),
            showlegend=False, hoverinfo='skip'
        )

        # Arrow head trace
        head_trace = go.Scatter(
            x=head_x, y=head_y, mode='markers',
            marker=dict(
                symbol='arrow',
                angle=angles,
                angleref='up',
                size=arrow_scale * 1.35,      # big arrow head
                color='#ff4b4b'
            ),
            showlegend=False,
            hovertemplate="高度: %{y:.0f} m<br>風向: %{customdata:.0f}°<extra></extra>",
            customdata=sample['direction'].values
        )

        return [line_trace, tail_trace, head_trace]

    init_traces = get_traces(plot_df[plot_df['time_label'] == unique_times[0]])
    frames = [go.Frame(data=get_traces(plot_df[plot_df['time_label'] == t]), name=t) for t in unique_times]

    fig = go.Figure(
        data=init_traces,
        frames=frames,
        layout=go.Layout(
            xaxis=dict(range=[0, max_v_limit], title="Wind Speed (m/s)"),
            yaxis=dict(range=[0, max_h_limit], title="Height (m)"),
            template="plotly_dark",
            height=820,
            margin=dict(l=80, r=40, t=100, b=170),
            legend=dict(x=0.02, y=0.98),
            updatemenus=[{"type": "buttons", "x": 0.08, "y": -0.13,
                "buttons": [
                    {"label": "▶ Play", "method": "animate", "args": [None, {"frame": {"duration": frame_dur, "redraw": True}, "fromcurrent": True}]},
                    {"label": "❚❚ Pause", "method": "animate", "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}]}
                ]}],
            sliders=[{
                "active": 0, "y": -0.19, "x": 0.1, "len": 0.88,
                "currentvalue": {"prefix": "時間: ", "font": {"size": 18, "color": "#00d1ff"}},
                "steps": [{"args": [[t], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}], "label": t, "method": "animate"} for t in unique_times]
            }]
        )
    )

    st.plotly_chart(fig, width="stretch", key="wind_arrow_v24")


if __name__ == "__main__":
    main()