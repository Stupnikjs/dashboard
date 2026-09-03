import plotly.graph_objects as go
import pandas as pd

def build_candlestick(df: pd.DataFrame, symbol: str) -> go.Figure:
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name=symbol
    )])
    fig.update_layout(
        title=symbol,
        xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=40, b=20),
        height=400,
    )
    return fig