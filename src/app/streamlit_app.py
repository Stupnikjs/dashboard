import streamlit as st
from ..config import DATA_DIR, load_watchlist
from ..storage.parquet_cache import ParquetCache
from ..ingestion.yfinance_adapter import YFinanceAdapter
from ..ingestion.updater import Updater
from ..viz.charts import build_candlestick

def main():
    st.set_page_config(layout="wide")
    st.title("Dashboard financier")

    watchlist = load_watchlist()
    updater = Updater(ParquetCache(DATA_DIR), YFinanceAdapter())

    @st.cache_data(ttl=3600)
    def get_data():
        return updater.update_all(watchlist)

    if st.button("🔄 Forcer le refresh"):
        get_data.clear()

    data = get_data()

    cols = st.columns(2)
    for i, symbol in enumerate(watchlist):
        df = data[symbol]
        with cols[i % 2]:
            st.plotly_chart(build_candlestick(df, symbol), use_container_width=True)
            st.caption(f"Dernière donnée : {df.index.max().date()}")

if __name__ == "__main__":
    main()