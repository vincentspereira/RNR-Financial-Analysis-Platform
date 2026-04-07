"""
Analytics API endpoints for ML-powered financial analysis
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from app.services.analytics.ml_service import ml_service, ModelType, PredictionType
from app.core.logging import get_logger
from app.core.monitoring import metrics_collector

router = APIRouter()
analytics_logger = get_logger("analytics.api")


# Request/Response Models
class StockPredictionRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol to predict")
    days_ahead: int = Field(30, ge=1, le=365, description="Number of days to predict ahead")
    model_type: ModelType = Field(ModelType.RANDOM_FOREST, description="ML model type to use")


class StockPredictionResponse(BaseModel):
    symbol: str
    predicted_price: float
    confidence_score: float
    current_price: Optional[float]
    prediction_date: datetime
    model_used: str
    features_used: List[str]
    days_ahead: int
    metadata: Dict[str, Any]


class PortfolioRiskRequest(BaseModel):
    portfolio: Dict[str, float] = Field(..., description="Portfolio weights by symbol")
    time_horizon: int = Field(252, ge=30, le=1260, description="Time horizon in trading days")


class PortfolioRiskResponse(BaseModel):
    var_95: float = Field(..., description="Value at Risk (95% confidence)")
    var_99: float = Field(..., description="Value at Risk (99% confidence)")
    expected_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    predicted_risk_score: float
    correlation_matrix: Dict[str, Dict[str, float]]
    beta: float
    analysis_date: datetime


class TradingSignalsRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol for signals")
    signal_type: str = Field("momentum", description="Type of signal: momentum, mean_reversion, or combined")


class TradingSignalsResponse(BaseModel):
    symbol: str
    signal_type: str
    current_signal: str = Field(..., description="BUY, SELL, or HOLD")
    signal_strength: float = Field(..., ge=0, le=1, description="Signal strength (0-1)")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in signal (0-1)")
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    technical_indicators: Dict[str, float]
    generated_at: datetime


class PortfolioOptimizationRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=2, max_length=20, description="List of stock symbols")
    risk_tolerance: float = Field(0.5, ge=0, le=1, description="Risk tolerance (0=conservative, 1=aggressive)")
    expected_return_target: Optional[float] = Field(None, description="Target expected return")


class PortfolioOptimizationResponse(BaseModel):
    optimized_weights: Dict[str, float]
    expected_annual_return: float
    expected_annual_risk: float
    sharpe_ratio: float
    risk_tolerance_used: float
    recommendation: str
    optimization_date: datetime
    symbols_analyzed: int


class AnalyticsOverviewResponse(BaseModel):
    total_predictions_made: int
    models_trained: int
    average_prediction_confidence: float
    most_analyzed_symbols: List[str]
    system_status: str
    last_updated: datetime


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview():
    """Get overview of analytics system status and statistics"""
    try:
        # Get system statistics
        stats = {
            "total_predictions_made": len(ml_service.models) * 10,  # Mock calculation
            "models_trained": len(ml_service.models),
            "average_prediction_confidence": 0.72,  # Mock average
            "most_analyzed_symbols": ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"],
            "system_status": "operational",
            "last_updated": datetime.now()
        }
        
        return AnalyticsOverviewResponse(**stats)
        
    except Exception as e:
        analytics_logger.error(f"Error getting analytics overview: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics overview")


@router.post("/predict/stock-price", response_model=StockPredictionResponse)
async def predict_stock_price(request: StockPredictionRequest, background_tasks: BackgroundTasks):
    """Predict future stock price using ML models"""
    try:
        analytics_logger.info(f"Predicting stock price for {request.symbol}")
        
        # Make prediction
        prediction = await ml_service.predict_stock_price(
            symbol=request.symbol,
            days_ahead=request.days_ahead,
            model_type=request.model_type
        )
        
        # Log metrics
        metrics_collector.increment_counter("analytics_predictions_total", {"type": "stock_price"})
        
        # Background task to update model if needed
        background_tasks.add_task(
            _update_model_if_needed, 
            request.symbol, 
            request.model_type
        )
        
        return StockPredictionResponse(
            symbol=prediction.symbol,
            predicted_price=prediction.predicted_value,
            confidence_score=prediction.confidence_score,
            current_price=prediction.metadata.get("current_price"),
            prediction_date=prediction.prediction_date,
            model_used=prediction.model_used.value,
            features_used=prediction.features_used,
            days_ahead=request.days_ahead,
            metadata=prediction.metadata
        )
        
    except Exception as e:
        analytics_logger.error(f"Error predicting stock price for {request.symbol}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Stock price prediction failed. Please try again later.")


@router.post("/analyze/portfolio-risk", response_model=PortfolioRiskResponse)
async def analyze_portfolio_risk(request: PortfolioRiskRequest):
    """Analyze portfolio risk using ML techniques"""
    try:
        analytics_logger.info(f"Analyzing portfolio risk for {len(request.portfolio)} symbols")
        
        # Validate portfolio weights
        total_weight = sum(request.portfolio.values())
        if abs(total_weight - 1.0) > 0.01:
            raise HTTPException(
                status_code=400, 
                detail=f"Portfolio weights must sum to 1.0, got {total_weight:.3f}"
            )
        
        # Analyze risk
        risk_analysis = await ml_service.analyze_portfolio_risk(
            portfolio_data=request.portfolio,
            time_horizon=request.time_horizon
        )
        
        # Log metrics
        metrics_collector.increment_counter("analytics_risk_analyses_total")
        
        return PortfolioRiskResponse(
            var_95=risk_analysis["var_95"],
            var_99=risk_analysis["var_99"],
            expected_return=risk_analysis["expected_return"],
            volatility=risk_analysis["volatility"],
            sharpe_ratio=risk_analysis["sharpe_ratio"],
            max_drawdown=risk_analysis["max_drawdown"],
            predicted_risk_score=risk_analysis["predicted_risk_score"],
            correlation_matrix=risk_analysis["correlation_matrix"],
            beta=risk_analysis["beta"],
            analysis_date=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        analytics_logger.error(f"Error analyzing portfolio risk: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Portfolio risk analysis failed. Please try again later.")


@router.post("/signals/trading", response_model=TradingSignalsResponse)
async def generate_trading_signals(request: TradingSignalsRequest):
    """Generate ML-based trading signals"""
    try:
        analytics_logger.info(f"Generating {request.signal_type} signals for {request.symbol}")
        
        # Validate signal type
        valid_signal_types = ["momentum", "mean_reversion", "combined"]
        if request.signal_type not in valid_signal_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid signal type. Must be one of: {valid_signal_types}"
            )
        
        # Generate signals
        signals = await ml_service.generate_trading_signals(
            symbol=request.symbol,
            signal_type=request.signal_type
        )
        
        # Log metrics
        metrics_collector.increment_counter("analytics_signals_generated", {"type": request.signal_type})
        
        return TradingSignalsResponse(
            symbol=signals["symbol"],
            signal_type=signals["signal_type"],
            current_signal=signals["current_signal"],
            signal_strength=signals["signal_strength"],
            confidence=signals["confidence"],
            entry_price=signals.get("entry_price"),
            stop_loss=signals.get("stop_loss"),
            take_profit=signals.get("take_profit"),
            technical_indicators=signals.get("technical_indicators", {}),
            generated_at=datetime.fromisoformat(signals["generated_at"])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        analytics_logger.error(f"Error generating trading signals for {request.symbol}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Trading signal generation failed. Please try again later.")


@router.post("/optimize/portfolio", response_model=PortfolioOptimizationResponse)
async def optimize_portfolio(request: PortfolioOptimizationRequest):
    """Optimize portfolio allocation using ML techniques"""
    try:
        analytics_logger.info(f"Optimizing portfolio for {len(request.symbols)} symbols")
        
        # Validate symbols list
        if len(set(request.symbols)) != len(request.symbols):
            raise HTTPException(status_code=400, detail="Duplicate symbols in portfolio")
        
        # Optimize portfolio
        optimization = await ml_service.optimize_portfolio(
            symbols=request.symbols,
            risk_tolerance=request.risk_tolerance,
            expected_return_target=request.expected_return_target
        )
        
        # Log metrics
        metrics_collector.increment_counter("analytics_optimizations_total")
        
        return PortfolioOptimizationResponse(
            optimized_weights=optimization["optimized_weights"],
            expected_annual_return=optimization["expected_annual_return"],
            expected_annual_risk=optimization["expected_annual_risk"],
            sharpe_ratio=optimization["sharpe_ratio"],
            risk_tolerance_used=optimization["risk_tolerance_used"],
            recommendation=optimization["recommendation"],
            optimization_date=datetime.fromisoformat(optimization["optimization_date"]),
            symbols_analyzed=optimization["symbols_analyzed"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        analytics_logger.error(f"Error optimizing portfolio: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Portfolio optimization failed. Please try again later.")


@router.get("/models/performance")
async def get_model_performance():
    """Get performance metrics for all trained models"""
    try:
        performance_data = {}
        
        for model_key, performance in ml_service.model_performance.items():
            performance_data[model_key] = {
                "model_type": performance.model_type.value,
                "mse": performance.mse,
                "mae": performance.mae,
                "r2_score": performance.r2_score,
                "cross_val_score": performance.cross_val_score,
                "training_samples": performance.training_samples,
                "last_updated": performance.last_updated.isoformat()
            }
        
        return {
            "models": performance_data,
            "total_models": len(performance_data),
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        analytics_logger.error(f"Error getting model performance: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve model performance")


@router.get("/predictions/history")
async def get_prediction_history(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    prediction_type: Optional[str] = Query(None, description="Filter by prediction type"),
    limit: int = Query(50, ge=1, le=1000, description="Number of predictions to return")
):
    """Get historical predictions (mock implementation)"""
    try:
        # This would typically query a database of historical predictions
        # For now, return mock data
        
        mock_predictions = []
        for i in range(min(limit, 20)):
            mock_predictions.append({
                "id": f"pred_{i}",
                "symbol": symbol or f"STOCK{i % 5}",
                "prediction_type": prediction_type or "stock_price",
                "predicted_value": 100.0 + i * 5,
                "actual_value": 98.0 + i * 5.2 if i < 10 else None,  # Only for past predictions
                "confidence_score": 0.7 + (i % 3) * 0.1,
                "prediction_date": (datetime.now() - timedelta(days=i)).isoformat(),
                "model_used": "random_forest",
                "accuracy": abs(1 - abs(100.0 + i * 5 - (98.0 + i * 5.2)) / (100.0 + i * 5)) if i < 10 else None
            })
        
        return {
            "predictions": mock_predictions,
            "total_count": len(mock_predictions),
            "filters_applied": {
                "symbol": symbol,
                "prediction_type": prediction_type,
                "limit": limit
            }
        }
        
    except Exception as e:
        analytics_logger.error(f"Error getting prediction history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve prediction history")


@router.post("/models/retrain/{model_type}")
async def retrain_model(
    model_type: str,
    symbol: str = Query(..., description="Symbol to retrain model for"),
    background_tasks: BackgroundTasks = None
):
    """Trigger model retraining for a specific symbol and model type"""
    try:
        # Validate model type
        try:
            model_enum = ModelType(model_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model type. Must be one of: {[m.value for m in ModelType]}"
            )
        
        # Add retraining task to background
        if background_tasks:
            background_tasks.add_task(
                _retrain_model_background,
                symbol,
                model_enum
            )
        
        return {
            "message": f"Model retraining initiated for {symbol} using {model_type}",
            "symbol": symbol,
            "model_type": model_type,
            "initiated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        analytics_logger.error(f"Error initiating model retraining: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initiate model retraining")


# Background tasks
async def _update_model_if_needed(symbol: str, model_type: ModelType):
    """Background task to update model if needed"""
    try:
        model_key = f"{symbol}_{model_type.value}_price"
        
        # Check if model needs updating (simplified logic)
        if model_key in ml_service.model_performance:
            performance = ml_service.model_performance[model_key]
            days_since_update = (datetime.now() - performance.last_updated).days
            
            # Retrain if model is older than 30 days or performance is poor
            if days_since_update > 30 or performance.r2_score < 0.5:
                analytics_logger.info(f"Retraining model {model_key} due to age or poor performance")
                # This would trigger actual retraining
                # For now, just log the intent
        
    except Exception as e:
        analytics_logger.error(f"Error in background model update: {str(e)}")


async def _retrain_model_background(symbol: str, model_type: ModelType):
    """Background task for model retraining"""
    try:
        analytics_logger.info(f"Starting background retraining for {symbol} with {model_type.value}")
        
        # This would implement actual model retraining
        # For now, simulate the process
        await asyncio.sleep(2)  # Simulate training time
        
        analytics_logger.info(f"Completed background retraining for {symbol}")
        metrics_collector.increment_counter("analytics_models_retrained")
        
    except Exception as e:
        analytics_logger.error(f"Error in background model retraining: {str(e)}")


# Import required modules for background tasks
import asyncio
from datetime import timedelta