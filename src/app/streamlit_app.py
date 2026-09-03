import streamlit as st
from core.config import DATA_DIR, load_watchlist
from storage.parquet_cache import ParquetCache
from ingestion.yfinance_adapter import YFinanceAdapter
from ingestion.updater import Updater
from visualize.charts import build_chart, resample_weekly

def main():
    st.set_page_config(layout="wide")
    st.title("Dashboard financier")

    with st.sidebar:
        st.header("Indicateurs")
        show_sma = st.multiselect("SMA (semaines)", [10, 20, 50], default=[20])
        show_bollinger = st.checkbox("Bandes de Bollinger", value=False)
        show_rsi = st.checkbox("RSI", value=False)

    watchlist = load_watchlist()
    tickers = [entry.ticker for entry in watchlist]
    updater = Updater(ParquetCache(DATA_DIR), YFinanceAdapter())

    @st.cache_data(ttl=3600)
    def get_data():
        return updater.update_all(tickers)

    if st.button("🔄 Forcer le refresh"):
        get_data.clear()

    data = get_data()

    if "page_idx" not in st.session_state:
        st.session_state.page_idx = 0

    labels = [entry.label or entry.ticker for entry in watchlist]

    col_prev, col_select, col_next = st.columns([1, 6, 1])
    with col_prev:
        if st.button("◀", use_container_width=True):
            st.session_state.page_idx = (st.session_state.page_idx - 1) % len(watchlist)
    with col_select:
        st.session_state.page_idx = st.selectbox(
            "Actif", range(len(watchlist)),
            index=st.session_state.page_idx,
            format_func=lambda i: labels[i],
            label_visibility="collapsed",
        )
    with col_next:
        if st.button("▶", use_container_width=True):
            st.session_state.page_idx = (st.session_state.page_idx + 1) % len(watchlist)

    entry = watchlist[st.session_state.page_idx]
    df = data[entry.ticker]

    if df is None:
        st.error(f"{entry.ticker} : échec de récupération")
        return

    weekly_df = resample_weekly(df)
    fig = build_chart(
        weekly_df, entry.label or entry.ticker,
        show_sma=show_sma, show_bollinger=show_bollinger, show_rsi=show_rsi,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Dernière donnée : {df.index.max().date()}")

if __name__ == "__main__":
    main()