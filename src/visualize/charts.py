import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from indicators.trend import sma, bollinger_bands
from indicators.momentum import rsi

def resample_weekly(df: pd.DataFrame) -> pd.DataFrame:
    return df.resample("W").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()

def build_chart(df: pd.DataFrame, symbol: str, show_sma: list[int] | None = None,
                 show_bollinger: bool = False, show_rsi: bool = False) -> go.Figure:
    rows = 2 if show_rsi else 1
    row_heights = [0.7, 0.3] if show_rsi else [1.0]

    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True,
        row_heights=row_heights, vertical_spacing=0.05,
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name=symbol
    ), row=1, col=1)

    for window in (show_sma or []):
        fig.add_trace(go.Scatter(
            x=df.index, y=sma(df, window), name=f"SMA {window}",
            line=dict(width=1),
        ), row=1, col=1)

    if show_bollinger:
        upper, mid, lower = bollinger_bands(df)
        for series, name in [(upper, "Bollinger haut"), (lower, "Bollinger bas")]:
            fig.add_trace(go.Scatter(
                x=df.index, y=series, name=name,
                line=dict(width=1, dash="dot"), opacity=0.6,
            ), row=1, col=1)

    if show_rsi:
        fig.add_trace(go.Scatter(
            x=df.index, y=rsi(df), name="RSI",
        ), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

    fig.update_layout(
        title=symbol,
        xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=40, b=20),
        height=400 if not show_rsi else 550,
        showlegend=True,
    )
    return fig