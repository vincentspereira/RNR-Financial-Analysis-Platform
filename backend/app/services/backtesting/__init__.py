"""
Backtesting services for strategy evaluation.
"""
from app.services.backtesting.engine import BacktestEngine

backtest_engine = BacktestEngine()

__all__ = ["backtest_engine", "BacktestEngine"]
