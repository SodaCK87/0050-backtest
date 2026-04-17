import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from backtest_engine import BacktestEngine
import numpy as np

# Page Config
st.set_page_config(page_title="0050 投資策略深度回測", layout="wide", page_icon="📈")

# Custom CSS for Premium Look
st.markdown("""
<style>
    /* Force Light Mode / Pastel Style for Cards */
    :root {
        --card-bg: #fdfdfd;
        --card-text: #2c3e50;
        --card-subtext: #555555;
        --card-shadow: rgba(0,0,0,0.05);
    }

    @media (prefers-color-scheme: dark) {
        :root {
            /* Keep cards light even in dark mode for contrast */
            --card-bg: #f4f6f9;
            --card-text: #1a252f;
            --card-subtext: #4a5568;
            --card-shadow: rgba(255,255,255,0.05);
        }
    }

    .metric-card {
        background-color: var(--card-bg);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px var(--card-shadow), 0 1px 3px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 10px;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
    }
    .metric-title {
        font-size: 0.95em;
        font-weight: 600;
        color: var(--card-text);
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 1.8em;
        font-weight: 800;
        margin-bottom: 4px;
    }
    .metric-subtext {
        font-size: 0.85em;
        color: var(--card-subtext);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🚀 0050 投資策略深度回測大賽")
st.markdown("---")

# Major Market Events History
HISTORICAL_EVENTS = [
    {"Date": "2011-08-05", "Event": "美債降評 & 歐債危機", "Story": "標普調降美國 AAA 評等，引發全球金融市場動盪與歐債問題。"},
    {"Date": "2015-08-24", "Event": "陸股崩盤全球股災", "Story": "陸股跌停板限制失效引發 Panic Sell，台股當日盤中重挫近 600 點。"},
    {"Date": "2018-10-11", "Event": "中美貿易戰恐慌", "Story": "貿易關係極度惡化，債券殖利率飆升導致恐慌性拋售，台股跌破萬點。"},
    {"Date": "2020-03-12", "Event": "COVID-19 全球大流行", "Story": "WHO 宣佈大流行，全球同步進入熊市並觸發多次熔斷機制。"},
    {"Date": "2022-02-24", "Event": "俄烏戰爭爆發", "Story": "俄羅斯入侵烏克蘭，引發全球能源通膨與避險資金撤離風險市場。"},
    {"Date": "2024-04-19", "Event": "地緣政治與升息恐懼", "Story": "中東局勢緊張加上通膨數據黏著，台股盤中創下史上最大點數跌幅(1009點)。"}
]

# Sidebar
st.sidebar.header("⚙️ 模擬參數設定")

csv_file = "0050_historical_adj.csv"

# Pre-load to determine date bounds for slider
@st.cache_data
def get_date_bounds(path):
    temp_df = pd.read_csv(path)
    temp_df['Date'] = pd.to_datetime(temp_df['Date'])
    return temp_df['Date'].min().to_pydatetime(), temp_df['Date'].max().to_pydatetime()

min_dt, max_dt = get_date_bounds(csv_file)

st.sidebar.subheader("📅 回測時間範圍")
date_range = st.sidebar.slider(
    "選擇區間 (不只是縮放，會重新計算回測)",
    min_value=min_dt,
    max_value=max_dt,
    value=(min_dt, max_dt),
    format="YYYY/MM/DD"
)

salary = st.sidebar.number_input("每月投入金額 (月薪)", value=5000, step=1000, help="每個月發薪日會投入的閒置資金")
payday = st.sidebar.slider("發薪日 (每月)", 1, 28, 5, help="每個月資金到帳的日期")
bs_threshold = st.sidebar.slider("黑天鵝觸發門檻 (%)", 1, 50, 10, help="價格從歷史高點回落多少百分比時觸發大舉買入") / 100

with st.spinner("回測計算中，請稍候..."):
    # Defensive check for slider output
    if isinstance(date_range, (list, tuple)) and len(date_range) >= 2:
        s_dt, e_dt = date_range[0], date_range[1]
    else:
        s_dt, e_dt = min_dt, max_dt

    try:
        engine = BacktestEngine(
            csv_file, 
            monthly_salary=salary, 
            payday=payday, 
            black_swan_threshold=bs_threshold,
            start_date=s_dt,
            end_date=e_dt
        )
        all_results = engine.run_all()
    except TypeError as e:
        st.error(f"⚠️ 回測引擎啟動失敗。請確認 backtest_engine.py 是否已更新至最新版本。錯誤訊息: {e}")
        st.stop()

if engine.df.empty:
    st.warning("⚠️ 所選日期區間內無交易數據，請重新選擇範圍。")
    st.stop()

dates = engine.df['Date'].dt.strftime('%Y年%m月%d日')
start_date_str = engine.df['Date'].iloc[0].strftime('%Y年%m月%d日')
end_date_str = engine.df['Date'].iloc[-1].strftime('%Y年%m月%d日')

# Summary Metrics
st.subheader("📊 績效總覽 (Performance Summary)")
st.markdown(f"**回測期間：** `{start_date_str}` 至 `{end_date_str}`")

# Determine the winner based on best ROI
best_roi = max(res['metrics']['ROI'] for res in all_results.values())

cols = st.columns(5)
colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

for i, (name, res) in enumerate(all_results.items()):
    with cols[i]:
        m = res['metrics']
        crown_icon = "<span style='position: relative; top: -3px; margin-right: 4px; font-size: 1.15em;'>👑</span>" if m['ROI'] == best_roi and best_roi > 0 else ""
        
        st.markdown(f"""
        <div class="metric-card" style="border-top: 5px solid {colors[i]}; position: relative;">
            <div class="metric-title" style="font-size: 1.1em; display: flex; align-items: center; justify-content: center;">{crown_icon}{name}</div>
            <div class="metric-value" style="color:{colors[i]};">{m['ROI']:.2f}%</div>
            <div class="metric-subtext" style="font-weight: bold; color: {colors[i]}; margin-bottom: 4px;">最終資產: ${res['equity'][-1]:,.0f}</div>
            <div class="metric-subtext">投入本金: ${m['TotalInvested']:,.0f}</div>
            <div class="metric-subtext">MDD: {m['MDD']:.1f}%</div>
            <div class="metric-subtext">現金閒置: {m['CashDrag']:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

# Main Visualization
st.markdown("### 📈 趨勢分析")
tab_p, tab_v, tab1, tab2, tab3 = st.tabs(["🕯️ K線與股價 (K-Line)", "⚖️ 績效對照 (vs Stock)", "💰 資產總體價值 (Equity)", "📦 持股張數 (Shares)", "💵 現金流向 (Cash)"])

with tab_p:
    df_price = engine.df
    fig_k = go.Figure()

    # Candlestick
    fig_k.add_trace(go.Candlestick(
        x=dates,
        open=df_price['Open'],
        high=df_price['High'],
        low=df_price['Low'],
        close=df_price['Close'],
        name="0050還原K線",
        increasing_line_color='#e74c3c', # Red for Taiwan Up
        decreasing_line_color='#27ae60'  # Green for Taiwan Down
    ))
    
    # SMA Overlays
    fig_k.add_trace(go.Scatter(x=dates, y=df_price['SMA5'], name="SMA5", line=dict(color='rgba(0,0,0,0.3)', width=1)))
    fig_k.add_trace(go.Scatter(x=dates, y=df_price['SMA20'], name="SMA20", line=dict(color='rgba(218,165,32,0.6)', width=1.2)))
    fig_k.add_trace(go.Scatter(x=dates, y=df_price['SMA60'], name="SMA60", line=dict(color='rgba(199,21,133,0.6)', width=1.5)))

    # Historical Event Markers
    event_dates_dt = pd.to_datetime([e['Date'] for e in HISTORICAL_EVENTS])
    df_events = df_price[df_price['Date'].isin(event_dates_dt)]
    
    if not df_events.empty:
        # Match each row in df_events back to its title/story to prevent mapping errors
        event_dict = {e['Date']: e for e in HISTORICAL_EVENTS}
        hover_texts = []
        for d in df_events['Date'].dt.strftime('%Y-%m-%d'):
            if d in event_dict:
                hover_texts.append(f"<b>{event_dict[d]['Event']}</b><br>{event_dict[d]['Story']}")
        
        fig_k.add_trace(go.Scatter(
            x=df_events['Date'].dt.strftime('%Y年%m月%d日'),
            y=df_events['High'] * 1.03,
            mode='markers+text',
            name="重大歷史事件",
            marker=dict(symbol='triangle-down', size=15, color='#e67e22', line=dict(width=1, color='white')),
            text=['⚠️'] * len(df_events),
            textposition='top center',
            hovertext=hover_texts,
            hoverinfo='text'
        ))

    fig_k.update_layout(
        title="0050 還原股價走勢圖 (包含歷史重大事件標記)",
        yaxis_title="價格 (TWD)",
        height=1200,
        hovermode='x unified',
        template="plotly_white", # Default to professional Light template
        xaxis=dict(
            type='category',
            rangeslider=dict(visible=False),
            tickangle=-45
        )
    )
    st.plotly_chart(fig_k, use_container_width=True)

with tab_v:
    df_v = engine.df
    # Create subplots with secondary Y axis
    fig_v = make_subplots(specs=[[{"secondary_y": True}]])

    # Add Equity curves to primary axis
    for i, (name, res) in enumerate(all_results.items()):
        fig_v.add_trace(
            go.Scatter(x=dates, y=res['equity'], name=f"{name}資產", line=dict(color=colors[i], width=2)),
            secondary_y=False,
        )

    # Add Stock Price K-Line to secondary axis
    fig_v.add_trace(
        go.Candlestick(
            x=dates,
            open=df_v['Open'],
            high=df_v['High'],
            low=df_v['Low'],
            close=df_v['Close'],
            name="0050還原K線",
            increasing_line_color='rgba(231, 76, 60, 0.4)', # Semi-transparent Red
            decreasing_line_color='rgba(39, 174, 96, 0.4)', # Semi-transparent Green
            opacity=0.6
        ),
        secondary_y=True,
    )

    fig_v.update_layout(
        title="策略資產 (左) vs 標的股價 (右) 對照圖",
        hovermode='x unified',
        height=1200,
        template="plotly_white",
        xaxis=dict(type='category', rangeslider=dict(visible=False), tickangle=-45)
    )

    fig_v.update_yaxes(title_text="資產價值 (TWD)", secondary_y=False)
    fig_v.update_yaxes(title_text="0050 股價 (TWD)", secondary_y=True)

    st.plotly_chart(fig_v, use_container_width=True)

with tab1:
    fig_equity = go.Figure()
    for i, (name, res) in enumerate(all_results.items()):
        fig_equity.add_trace(go.Scatter(x=dates, y=res['equity'], name=name, line=dict(color=colors[i], width=2)))
    fig_equity.update_layout(
        hovermode='x unified',
        height=1200,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=0, r=0, t=30, b=0),
        yaxis_title="總資產價值 (TWD)",
        xaxis=dict(type='category', tickangle=-45),
        template="plotly_white"
    )
    st.plotly_chart(fig_equity, use_container_width=True)

with tab2:
    fig_shares = go.Figure()
    for i, (name, res) in enumerate(all_results.items()):
        fig_shares.add_trace(go.Scatter(x=dates, y=res['shares'], name=name, line=dict(color=colors[i], width=2)))
    fig_shares.update_layout(
        hovermode='x unified',
        height=1200,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=0, r=0, t=30, b=0),
        yaxis_title="持有股數",
        xaxis=dict(type='category', tickangle=-45),
        template="plotly_white"
    )
    st.plotly_chart(fig_shares, use_container_width=True)

with tab3:
    fig_cash = go.Figure()
    for i, (name, res) in enumerate(all_results.items()):
        fig_cash.add_trace(go.Scatter(x=dates, y=res['cash'], name=name, line=dict(color=colors[i], width=2)))
    fig_cash.update_layout(
        hovermode='x unified',
        height=1200,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=0, r=0, t=30, b=0),
        yaxis_title="帳戶現金 (TWD)",
        xaxis=dict(type='category', tickangle=-45),
        template="plotly_white"
    )
    st.plotly_chart(fig_cash, use_container_width=True)

# Strategy Details
st.markdown("---")
st.subheader("🕵️ 交易者特徵與策略邏輯")
trader_info = {
    "無腦投入派": "拿到薪水當天直接 ALL IN。信仰「留在市場的時間勝過擇時」。",
    "逢低買進派": "50% 發薪日買，50% 等待當月出現「下跌日」才買進。試圖在心理與成本間取得平衡。",
    "動能追高派": "50% 發薪日買，50% 連續三天上漲才買。信仰強者恆強，不接掉下來的刀子。",
    "技術狙擊派": "依賴指標波段。當 KD 在中低檔(<50)金叉，或 MACD 動能翻紅(突破0軸)時，切入 20% 資金做波段。買不到就存現金。",
    "黑天鵝獵人": "85% 資金死等大跌 (預設 20%) 才 ALL IN。平時僅以 15% 資金做 SMA 均線投機以保持盤感。"
}

cols_info = st.columns(len(trader_info))
for i, (name, desc) in enumerate(trader_info.items()):
    with cols_info[i]:
        st.info(f"**{name}**\n\n{desc}")

st.sidebar.markdown("---")
st.sidebar.caption(f"數據來源: 0050.TW 還原股價（Adj. Close）{start_date[:4]}年 至 {end_date}")
st.sidebar.caption("交易成本: 0.1425% 手續費 / 0.1% ETF 交易稅")
