import streamlit as st
from core.config import DATA_DIR, load_watchlist
from storage.parquet_cache import ParquetCache
from ingestion.yfinance_adapter import YFinanceAdapter
from ingestion.updater import Updater
from visualize.charts import build_candlestick, resample_weekly

def main():
    st.set_page_config(layout="wide")
    st.title("Dashboard financier")

    watchlist = load_watchlist()
    tickers = [entry.ticker for entry in watchlist]
    updater = Updater(ParquetCache(DATA_DIR), YFinanceAdapter())

    @st.cache_data(ttl=3600)
    def get_data():
        return updater.update_all(tickers)

    if st.button("🔄 Forcer le refresh"):
        get_data.clear()

    data = get_data()

    cols = st.columns(2)
    for i, entry in enumerate(watchlist):
        df = data[entry.ticker]
        with cols[i % 2]:
            if df is None:
                st.error(f"{entry.ticker} : échec de récupération")
                continue
            weekly_df = resample_weekly(df)
            st.plotly_chart(build_candlestick(weekly_df, entry.label or entry.ticker), use_container_width=True)
            st.caption(f"Dernière donnée : {weekly_df.index.max().date()}")

if __name__ == "__main__":
    main()