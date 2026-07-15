"""
Machine Learning service for advanced financial analytics
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from app.core.logging import get_logger
from app.core.monitoring import metrics_collector
from app.core.config import settings
from app.services.analytics.model_registry import model_registry

# Try to import ML libraries with fallbacks
try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.preprocessing import StandardScaler, MinMaxScaler
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

ml_logger = get_logger("ml_service")


class ModelType(Enum):
    """Available ML model types"""
    LINEAR_REGRESSION = "linear_regression"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    RIDGE_REGRESSION = "ridge_regression"


class PredictionType(Enum):
    """Types of predictions available"""
    STOCK_PRICE = "stock_price"
    PORTFOLIO_RETURN = "portfolio_return"
    RISK_ASSESSMENT = "risk_assessment"
    VOLATILITY = "volatility"
    TREND_ANALYSIS = "trend_analysis"


@dataclass
class MLPrediction:
    """ML prediction result"""
    prediction_type: PredictionType
    symbol: str
    predicted_value: float
    confidence_score: float
    prediction_date: datetime
    model_used: ModelType
    features_used: List[str]
    metadata: Dict[str, Any]


@dataclass
class ModelPerformance:
    """Model performance metrics"""
    model_type: ModelType
    mse: float
    mae: float
    r2_score: float
    cross_val_score: float
    training_samples: int
    last_updated: datetime


class FinancialMLService:
    """Advanced ML service for financial analytics"""
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, Any] = {}
        self.model_performance: Dict[str, ModelPerformance] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        if not ML_AVAILABLE:
            ml_logger.warning("ML libraries not available. Using mock predictions.")
    
    async def predict_stock_price(
        self,
        symbol: str,
        days_ahead: int = 30,
        model_type: ModelType = ModelType.RANDOM_FOREST
    ) -> MLPrediction:
        """Predict stock price using ML models"""
        try:
            if not ML_AVAILABLE:
                return self._mock_stock_prediction(symbol, days_ahead)
            
            # Get historical data
            historical_data = await self._get_historical_data(symbol)
            
            if historical_data is None or len(historical_data) < 100:
                ml_logger.warning(f"Insufficient data for {symbol}, using mock prediction")
                return self._mock_stock_prediction(symbol, days_ahead)
            
            # Prepare features
            features = self._prepare_stock_features(historical_data)
            
            # Train or get existing model
            model_key = f"{symbol}_{model_type.value}_price"
            model = await self._get_or_train_model(model_key, features, model_type)
            
            # Make prediction
            latest_features = features.iloc[-1:].drop('target', axis=1)
            predicted_price = model.predict(latest_features)[0]
            
            # Calculate confidence score
            confidence = await self._calculate_confidence(model, features, model_type)
            
            return MLPrediction(
                prediction_type=PredictionType.STOCK_PRICE,
                symbol=symbol,
                predicted_value=predicted_price,
                confidence_score=confidence,
                prediction_date=datetime.now(),
                model_used=model_type,
                features_used=list(features.columns[:-1]),
                metadata={
                    "days_ahead": days_ahead,
                    "data_points": len(historical_data),
                    "current_price": historical_data['close'].iloc[-1]
                }
            )
            
        except Exception as e:
            ml_logger.error(f"Error predicting stock price for {symbol}: {str(e)}")
            return self._mock_stock_prediction(symbol, days_ahead)
    
    async def analyze_portfolio_risk(
        self,
        portfolio_data: Dict[str, float],
        time_horizon: int = 252  # Trading days in a year
    ) -> Dict[str, Any]:
        """Analyze portfolio risk using ML techniques"""
        try:
            if not ML_AVAILABLE:
                return self._mock_risk_analysis(portfolio_data)
            
            risk_metrics = {}
            
            # Get historical data for all symbols
            historical_data = {}
            for symbol, weight in portfolio_data.items():
                data = await self._get_historical_data(symbol)
                if data is not None:
                    historical_data[symbol] = data
            
            if not historical_data:
                return self._mock_risk_analysis(portfolio_data)
            
            # Calculate returns
            returns_data = {}
            for symbol, data in historical_data.items():
                returns_data[symbol] = data['close'].pct_change().dropna()
            
            returns_df = pd.DataFrame(returns_data)
            
            # Portfolio returns
            weights = np.array([portfolio_data.get(symbol, 0) for symbol in returns_df.columns])
            weights = weights / weights.sum()  # Normalize weights
            
            portfolio_returns = (returns_df * weights).sum(axis=1)
            
            # Risk metrics
            risk_metrics = {
                "var_95": np.percentile(portfolio_returns, 5),
                "var_99": np.percentile(portfolio_returns, 1),
                "expected_return": portfolio_returns.mean() * time_horizon,
                "volatility": portfolio_returns.std() * np.sqrt(time_horizon),
                "sharpe_ratio": (portfolio_returns.mean() * time_horizon) / (portfolio_returns.std() * np.sqrt(time_horizon)),
                "max_drawdown": self._calculate_max_drawdown(portfolio_returns),
                "correlation_matrix": returns_df.corr().to_dict(),
                "beta": self._calculate_portfolio_beta(returns_df, weights),
                "time_horizon_days": time_horizon
            }
            
            # ML-based risk prediction
            risk_features = self._prepare_risk_features(returns_df, portfolio_returns)
            risk_prediction = await self._predict_future_risk(risk_features)
            risk_metrics["predicted_risk_score"] = risk_prediction
            
            return risk_metrics
            
        except Exception as e:
            ml_logger.error(f"Error analyzing portfolio risk: {str(e)}")
            return self._mock_risk_analysis(portfolio_data)
    
    async def generate_trading_signals(
        self,
        symbol: str,
        signal_type: str = "momentum"
    ) -> Dict[str, Any]:
        """Generate ML-based trading signals"""
        try:
            if not ML_AVAILABLE:
                return self._mock_trading_signals(symbol)
            
            # Get historical data
            historical_data = await self._get_historical_data(symbol)
            
            if historical_data is None or len(historical_data) < 50:
                return self._mock_trading_signals(symbol)
            
            # Prepare technical indicators
            signals_data = self._prepare_signal_features(historical_data)
            
            # Generate signals based on type
            if signal_type == "momentum":
                signals = self._generate_momentum_signals(signals_data)
            elif signal_type == "mean_reversion":
                signals = self._generate_mean_reversion_signals(signals_data)
            else:
                signals = self._generate_combined_signals(signals_data)
            
            return {
                "symbol": symbol,
                "signal_type": signal_type,
                "current_signal": signals["current_signal"],
                "signal_strength": signals["signal_strength"],
                "confidence": signals["confidence"],
                "entry_price": signals.get("entry_price"),
                "stop_loss": signals.get("stop_loss"),
                "take_profit": signals.get("take_profit"),
                "generated_at": datetime.now().isoformat(),
                "technical_indicators": signals.get("indicators", {})
            }
            
        except Exception as e:
            ml_logger.error(f"Error generating trading signals for {symbol}: {str(e)}")
            return self._mock_trading_signals(symbol)
    
    async def optimize_portfolio(
        self,
        symbols: List[str],
        risk_tolerance: float = 0.5,
        expected_return_target: Optional[float] = None
    ) -> Dict[str, Any]:
        """Optimize portfolio allocation using ML techniques"""
        try:
            if not ML_AVAILABLE:
                return self._mock_portfolio_optimization(symbols, risk_tolerance)
            
            # Get historical data for all symbols
            historical_data = {}
            for symbol in symbols:
                data = await self._get_historical_data(symbol)
                if data is not None:
                    historical_data[symbol] = data
            
            if len(historical_data) < 2:
                return self._mock_portfolio_optimization(symbols, risk_tolerance)
            
            # Calculate returns and covariance matrix
            returns_data = {}
            for symbol, data in historical_data.items():
                returns_data[symbol] = data['close'].pct_change().dropna()
            
            returns_df = pd.DataFrame(returns_data)
            
            # Expected returns (using historical mean)
            expected_returns = returns_df.mean() * 252  # Annualized
            
            # Covariance matrix
            cov_matrix = returns_df.cov() * 252  # Annualized
            
            # Optimize using simplified mean-variance optimization
            optimal_weights = self._optimize_weights(
                expected_returns, 
                cov_matrix, 
                risk_tolerance,
                expected_return_target
            )
            
            # Calculate portfolio metrics
            portfolio_return = np.sum(optimal_weights * expected_returns)
            portfolio_risk = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights)))
            sharpe_ratio = portfolio_return / portfolio_risk if portfolio_risk > 0 else 0
            
            return {
                "optimized_weights": {symbol: float(weight) for symbol, weight in zip(symbols, optimal_weights)},
                "expected_annual_return": float(portfolio_return),
                "expected_annual_risk": float(portfolio_risk),
                "sharpe_ratio": float(sharpe_ratio),
                "risk_tolerance_used": risk_tolerance,
                "optimization_date": datetime.now().isoformat(),
                "symbols_analyzed": len(historical_data),
                "recommendation": self._generate_portfolio_recommendation(optimal_weights, symbols, portfolio_return, portfolio_risk)
            }
            
        except Exception as e:
            ml_logger.error(f"Error optimizing portfolio: {str(e)}")
            return self._mock_portfolio_optimization(symbols, risk_tolerance)
    
    async def _get_historical_data(self, symbol: str, period: str = "2y") -> Optional[pd.DataFrame]:
        """Get historical stock data"""
        try:
            if YFINANCE_AVAILABLE and settings.YFINANCE_ENABLED:
                # Run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                ticker = yf.Ticker(symbol)
                data = await loop.run_in_executor(
                    self.executor, 
                    lambda: ticker.history(period=period)
                )
                
                if not data.empty:
                    data.columns = data.columns.str.lower()
                    return data
            
            # Fallback: generate mock data
            return self._generate_mock_historical_data(symbol)
            
        except Exception as e:
            ml_logger.warning(f"Error fetching data for {symbol}: {str(e)}")
            return self._generate_mock_historical_data(symbol)
    
    def _prepare_stock_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for stock price prediction"""
        df = data.copy()
        
        # Technical indicators
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['rsi'] = self._calculate_rsi(df['close'])
        df['macd'] = self._calculate_macd(df['close'])
        df['bollinger_upper'], df['bollinger_lower'] = self._calculate_bollinger_bands(df['close'])
        
        # Price-based features
        df['price_change'] = df['close'].pct_change()
        df['volume_change'] = df['volume'].pct_change()
        df['high_low_ratio'] = df['high'] / df['low']
        df['close_open_ratio'] = df['close'] / df['open']
        
        # Lag features
        for lag in [1, 2, 3, 5, 10]:
            df[f'close_lag_{lag}'] = df['close'].shift(lag)
            df[f'volume_lag_{lag}'] = df['volume'].shift(lag)
        
        # Target variable (next day's closing price)
        df['target'] = df['close'].shift(-1)
        
        # Drop NaN values
        df = df.dropna()
        
        return df
    
    def _prepare_risk_features(self, returns_df: pd.DataFrame, portfolio_returns: pd.Series) -> pd.DataFrame:
        """Prepare features for risk analysis"""
        features = pd.DataFrame()
        
        # Rolling volatility
        features['volatility_30d'] = portfolio_returns.rolling(30).std()
        features['volatility_60d'] = portfolio_returns.rolling(60).std()
        
        # Rolling correlations
        features['avg_correlation'] = returns_df.rolling(30).corr().mean(axis=1).groupby(level=0).mean()
        
        # Market stress indicators
        features['max_daily_loss'] = portfolio_returns.rolling(30).min()
        features['positive_days_ratio'] = (portfolio_returns > 0).rolling(30).mean()
        
        return features.dropna()
    
    def _prepare_signal_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for trading signals"""
        df = data.copy()
        
        # Technical indicators
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        df['rsi'] = self._calculate_rsi(df['close'])
        df['macd'] = self._calculate_macd(df['close'])
        df['stoch_k'], df['stoch_d'] = self._calculate_stochastic(df)
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df.dropna()
    
    async def _get_or_train_model(self, model_key: str, features: pd.DataFrame, model_type: ModelType):
        """Get existing model or train a new one"""
        if model_key in self.models:
            return self.models[model_key]

        # Try the on-disk registry (survives process restarts) before retraining.
        cached = model_registry.get(model_key)
        if cached is not None:
            model, scaler, performance = cached
            self.models[model_key] = model
            self.scalers[model_key] = scaler
            if performance is not None:
                self.model_performance[model_key] = performance
            ml_logger.info(f"Restored model {model_key} from registry cache")
            return model

        # Train new model
        X = features.drop('target', axis=1)
        y = features['target']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Create model based on type
        if model_type == ModelType.LINEAR_REGRESSION:
            model = LinearRegression()
        elif model_type == ModelType.RANDOM_FOREST:
            model = RandomForestRegressor(n_estimators=100, random_state=42)
        elif model_type == ModelType.GRADIENT_BOOSTING:
            model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        else:  # RIDGE_REGRESSION
            model = Ridge(alpha=1.0)
        
        # Train model
        model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test_scaled)
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        cv_score = cross_val_score(model, X_train_scaled, y_train, cv=5).mean()
        
        # Store model and performance
        self.models[model_key] = model
        self.scalers[model_key] = scaler
        self.model_performance[model_key] = ModelPerformance(
            model_type=model_type,
            mse=mse,
            mae=mae,
            r2_score=r2,
            cross_val_score=cv_score,
            training_samples=len(X_train),
            last_updated=datetime.now()
        )

        # Persist to the on-disk registry so the next process restart reuses it
        # instead of retraining. Best-effort; failures are logged, not raised.
        model_registry.save(model_key, model, scaler, self.model_performance[model_key])

        ml_logger.info(f"Trained new model {model_key} with R² score: {r2:.3f}")
        
        return model
    
    async def _calculate_confidence(self, model, features: pd.DataFrame, model_type: ModelType) -> float:
        """Calculate prediction confidence score"""
        if model_type in [ModelType.RANDOM_FOREST, ModelType.GRADIENT_BOOSTING]:
            # For ensemble methods, use prediction variance
            X = features.drop('target', axis=1).iloc[-10:]  # Last 10 samples
            predictions = []
            
            if hasattr(model, 'estimators_'):
                for estimator in model.estimators_[:10]:  # Sample 10 estimators
                    pred = estimator.predict(X)
                    predictions.append(pred)
                
                variance = np.var(predictions, axis=0).mean()
                confidence = max(0.1, min(0.9, 1.0 - variance))
            else:
                confidence = 0.7  # Default confidence
        else:
            # For linear models, use R² score as confidence proxy
            model_key = next((k for k, v in self.models.items() if v == model), None)
            if model_key and model_key in self.model_performance:
                r2 = self.model_performance[model_key].r2_score
                confidence = max(0.1, min(0.9, r2))
            else:
                confidence = 0.6
        
        return confidence
    
    # Technical indicator calculations
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series) -> pd.Series:
        """Calculate MACD indicator"""
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        return ema_12 - ema_26
    
    def _calculate_bollinger_bands(self, prices: pd.Series, window: int = 20) -> Tuple[pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        return upper, lower
    
    def _calculate_stochastic(self, data: pd.DataFrame, k_window: int = 14) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic oscillator"""
        low_min = data['low'].rolling(window=k_window).min()
        high_max = data['high'].rolling(window=k_window).max()
        k_percent = 100 * ((data['close'] - low_min) / (high_max - low_min))
        d_percent = k_percent.rolling(window=3).mean()
        return k_percent, d_percent
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    def _calculate_portfolio_beta(self, returns_df: pd.DataFrame, weights: np.ndarray) -> float:
        """Calculate portfolio beta (simplified)"""
        # This is a simplified beta calculation
        # In practice, you'd compare against a market index
        portfolio_returns = (returns_df * weights).sum(axis=1)
        market_proxy = returns_df.mean(axis=1)  # Using average as market proxy
        
        covariance = np.cov(portfolio_returns, market_proxy)[0, 1]
        market_variance = np.var(market_proxy)
        
        return covariance / market_variance if market_variance > 0 else 1.0
    
    def _optimize_weights(
        self, 
        expected_returns: pd.Series, 
        cov_matrix: pd.DataFrame, 
        risk_tolerance: float,
        target_return: Optional[float] = None
    ) -> np.ndarray:
        """Simplified portfolio optimization"""
        n_assets = len(expected_returns)
        
        if target_return is None:
            # Risk parity approach with risk tolerance adjustment
            inv_vol = 1 / np.sqrt(np.diag(cov_matrix))
            weights = inv_vol / inv_vol.sum()
            
            # Adjust for risk tolerance
            if risk_tolerance > 0.5:
                # Higher risk tolerance: tilt towards higher expected returns
                return_tilt = expected_returns / expected_returns.sum()
                weights = (1 - risk_tolerance) * weights + risk_tolerance * return_tilt
            
        else:
            # Simple mean-variance optimization
            weights = np.ones(n_assets) / n_assets  # Equal weights as fallback
        
        # Ensure weights sum to 1 and are non-negative
        weights = np.maximum(weights, 0)
        weights = weights / weights.sum()
        
        return weights
    
    def _generate_portfolio_recommendation(
        self, 
        weights: np.ndarray, 
        symbols: List[str], 
        expected_return: float, 
        expected_risk: float
    ) -> str:
        """Generate portfolio recommendation text"""
        max_weight_idx = np.argmax(weights)
        max_symbol = symbols[max_weight_idx]
        max_weight = weights[max_weight_idx]
        
        risk_level = "Low" if expected_risk < 0.15 else "Medium" if expected_risk < 0.25 else "High"
        
        return f"Recommended allocation with {max_symbol} as largest position ({max_weight:.1%}). " \
               f"Expected annual return: {expected_return:.1%}, Risk level: {risk_level}"
    
    # Mock functions for when ML libraries are not available
    def _mock_stock_prediction(self, symbol: str, days_ahead: int) -> MLPrediction:
        """Mock stock price prediction"""
        # Generate a reasonable mock prediction
        base_price = 100.0 + hash(symbol) % 200
        predicted_price = base_price * (1 + np.random.normal(0, 0.1))
        
        return MLPrediction(
            prediction_type=PredictionType.STOCK_PRICE,
            symbol=symbol,
            predicted_value=predicted_price,
            confidence_score=0.65,
            prediction_date=datetime.now(),
            model_used=ModelType.LINEAR_REGRESSION,
            features_used=["mock_feature"],
            metadata={"days_ahead": days_ahead, "mock": True}
        )
    
    def _mock_risk_analysis(self, portfolio_data: Dict[str, float]) -> Dict[str, Any]:
        """Mock portfolio risk analysis"""
        return {
            "var_95": -0.05,
            "var_99": -0.08,
            "expected_return": 0.08,
            "volatility": 0.15,
            "sharpe_ratio": 0.53,
            "max_drawdown": -0.12,
            "predicted_risk_score": 0.6,
            "mock": True
        }
    
    def _mock_trading_signals(self, symbol: str) -> Dict[str, Any]:
        """Mock trading signals"""
        signals = ["BUY", "SELL", "HOLD"]
        return {
            "symbol": symbol,
            "signal_type": "momentum",
            "current_signal": np.random.choice(signals),
            "signal_strength": np.random.uniform(0.3, 0.9),
            "confidence": np.random.uniform(0.5, 0.8),
            "mock": True
        }
    
    def _mock_portfolio_optimization(self, symbols: List[str], risk_tolerance: float) -> Dict[str, Any]:
        """Mock portfolio optimization"""
        n_symbols = len(symbols)
        weights = np.random.dirichlet(np.ones(n_symbols))
        
        return {
            "optimized_weights": {symbol: float(weight) for symbol, weight in zip(symbols, weights)},
            "expected_annual_return": 0.08,
            "expected_annual_risk": 0.15,
            "sharpe_ratio": 0.53,
            "risk_tolerance_used": risk_tolerance,
            "mock": True
        }
    
    def _generate_mock_historical_data(self, symbol: str, days: int = 500) -> pd.DataFrame:
        """Generate mock historical data"""
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        
        # Generate realistic price data with random walk
        initial_price = 50 + hash(symbol) % 100
        returns = np.random.normal(0.0005, 0.02, days)  # Daily returns
        prices = initial_price * np.exp(np.cumsum(returns))
        
        # Generate OHLCV data
        data = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.01, days)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.02, days))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.02, days))),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, days)
        }, index=dates)
        
        # Ensure high >= close >= low and high >= open >= low
        data['high'] = np.maximum(data['high'], np.maximum(data['open'], data['close']))
        data['low'] = np.minimum(data['low'], np.minimum(data['open'], data['close']))
        
        return data
    
    # Signal generation methods
    def _generate_momentum_signals(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate momentum-based trading signals"""
        latest = data.iloc[-1]
        
        # Simple momentum rules
        signal_score = 0
        
        if latest['close'] > latest['sma_20']:
            signal_score += 1
        if latest['sma_20'] > latest['sma_50']:
            signal_score += 1
        if latest['rsi'] > 50:
            signal_score += 1
        if latest['macd'] > 0:
            signal_score += 1
        
        if signal_score >= 3:
            signal = "BUY"
        elif signal_score <= 1:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        return {
            "current_signal": signal,
            "signal_strength": signal_score / 4.0,
            "confidence": 0.7,
            "entry_price": latest['close'],
            "stop_loss": latest['close'] * 0.95,
            "take_profit": latest['close'] * 1.1,
            "indicators": {
                "rsi": latest['rsi'],
                "macd": latest['macd'],
                "sma_20": latest['sma_20'],
                "sma_50": latest['sma_50']
            }
        }
    
    def _generate_mean_reversion_signals(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate mean reversion trading signals"""
        latest = data.iloc[-1]
        
        # Mean reversion rules
        signal_score = 0
        
        if latest['rsi'] < 30:  # Oversold
            signal_score += 2
        elif latest['rsi'] > 70:  # Overbought
            signal_score -= 2
        
        if latest['close'] < latest['sma_20'] * 0.95:  # Significantly below MA
            signal_score += 1
        elif latest['close'] > latest['sma_20'] * 1.05:  # Significantly above MA
            signal_score -= 1
        
        if signal_score >= 2:
            signal = "BUY"
        elif signal_score <= -2:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        return {
            "current_signal": signal,
            "signal_strength": abs(signal_score) / 3.0,
            "confidence": 0.6,
            "entry_price": latest['close'],
            "indicators": {
                "rsi": latest['rsi'],
                "sma_20": latest['sma_20']
            }
        }
    
    def _generate_combined_signals(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate combined trading signals"""
        momentum = self._generate_momentum_signals(data)
        mean_reversion = self._generate_mean_reversion_signals(data)
        
        # Combine signals with weights
        momentum_weight = 0.6
        mean_reversion_weight = 0.4
        
        signal_values = {"BUY": 1, "HOLD": 0, "SELL": -1}
        
        combined_score = (
            signal_values[momentum["current_signal"]] * momentum_weight +
            signal_values[mean_reversion["current_signal"]] * mean_reversion_weight
        )
        
        if combined_score > 0.3:
            final_signal = "BUY"
        elif combined_score < -0.3:
            final_signal = "SELL"
        else:
            final_signal = "HOLD"
        
        return {
            "current_signal": final_signal,
            "signal_strength": abs(combined_score),
            "confidence": (momentum["confidence"] + mean_reversion["confidence"]) / 2,
            "entry_price": momentum["entry_price"],
            "indicators": {**momentum["indicators"], **mean_reversion["indicators"]}
        }
    
    async def _predict_future_risk(self, risk_features: pd.DataFrame) -> float:
        """Predict future risk score using ML"""
        if len(risk_features) < 10:
            return 0.5  # Default risk score
        
        # Simple risk prediction based on recent volatility trends
        recent_volatility = risk_features['volatility_30d'].iloc[-10:].mean()
        historical_volatility = risk_features['volatility_30d'].mean()
        
        risk_score = min(1.0, max(0.0, recent_volatility / historical_volatility))
        return risk_score


# Global ML service instance
ml_service = FinancialMLService()

# Module-level functions for backward compatibility
async def predict_stock_price(symbol: str, days_ahead: int = 30, model_type: str = "random_forest") -> Dict[str, Any]:
    """Predict stock price"""
    return await ml_service.predict_stock_price(symbol, days_ahead, ModelType(model_type))

async def predict_portfolio_return(portfolio_data: Dict[str, Any], time_horizon: int = 30) -> Dict[str, Any]:
    """Predict portfolio return"""
    return await ml_service.predict_portfolio_return(portfolio_data, time_horizon)

async def assess_portfolio_risk(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Assess portfolio risk"""
    return await ml_service.assess_portfolio_risk(portfolio_data)