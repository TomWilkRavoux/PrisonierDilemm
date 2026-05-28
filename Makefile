.PHONY: generate load transform all clean test dashboard

generate:
	uv run python -m src.generate

load:
	uv run python -m src.load

transform:
	uv run python -m src.transform

all: generate load transform

clean:
	rm -rf data/bronze data/silver data/gold data/*.duckdb data/*.duckdb.wal

test:
	uv run pytest tests/ -v

dashboard:
	uv run streamlit run dashboard.py
