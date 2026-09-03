src/
├── app/
│   └── streamlit_app.py
│
├── core/
│   └── config.py
│
├── ingestion/
│   ├── base.py
│   ├── updater.py
│   └── yfinance_adapter.py
│
├── indicators/
│   ├── trend.py
│   └── momentum.py
│
├── screening/                 # NOUVEAU
│   ├── __init__.py
│   ├── models.py
│   ├── metrics.py
│   ├── criteria.py
│   └── screener.py
│
├── storage/
│   └── parquet_cache.py
│
└── visualize/
    └── charts.py