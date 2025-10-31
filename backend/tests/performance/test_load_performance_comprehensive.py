"""
Comprehensive Performance Tests - Load Testing and Benchmarking
"""
import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, Mock
import psutil
import gc
from datetime import datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient
from app.main import app
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User


class TestAPIPerformance:
    """Performance tests for API endpoints under load"""
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user for performance tests"""
        return User(
            id="perf-test-user-id",
            email="perf.test@example.com",
            full_name="Performance Test User",
            is_active=True,
            is_verified=True
        )
    
    @pytest.mark.asyncio
    async def test_health_endpoint_performance(self):
        """Test health endpoint performance under load"""
        
        async def make_health_request():
            async with AsyncClient(app=app, base_url="http://test") as client:
                start_time = time.time()
                response = await client.get("/api/v1/health")
                end_time = time.time()
                
                return {
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200
                }
        
        # Performance test with 100 concurrent requests
        tasks = [make_health_request() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        # Analyze performance metrics
        response_times = [r["response_time"] for r in results]
        success_count = sum(1 for r in results if r["success"])
        
        # Performance assertions
        assert success_count >= 95, f"Success rate {success_count}% below 95% threshold"
        assert statistics.mean(response_times) < 1.0, f"Average response time {statistics.mean(response_times):.3f}s exceeds 1s"
        assert max(response_times) < 5.0, f"Max response time {max(response_times):.3f}s exceeds 5s"
        assert statistics.median(response_times) < 0.5, f"Median response time {statistics.median(response_times):.3f}s exceeds 0.5s"
        
        # Calculate percentiles
        sorted_times = sorted(response_times)
        p95_time = sorted_times[int(0.95 * len(sorted_times))]
        p99_time = sorted_times[int(0.99 * len(sorted_times))]
        
        assert p95_time < 2.0, f"95th percentile {p95_time:.3f}s exceeds 2s"
        assert p99_time < 3.0, f"99th percentile {p99_time:.3f}s exceeds 3s"
    
    @pytest.mark.asyncio
    async def test_portfolio_crud_performance(self, mock_user):
        """Test portfolio CRUD operations performance"""
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            async def portfolio_crud_cycle(portfolio_index):
                """Complete CRUD cycle for a single portfolio"""
                async with AsyncClient(app=app, base_url="http://test") as client:
                    start_time = time.time()
                    
                    # Mock portfolio service responses
                    with patch('app.services.portfolio.portfolio_service.create_portfolio') as mock_create, \
                         patch('app.services.portfolio.portfolio_service.get_portfolio') as mock_get, \
                         patch('app.services.portfolio.portfolio_service.update_portfolio') as mock_update, \
                         patch('app.services.portfolio.portfolio_service.delete_portfolio') as mock_delete:
                        
                        portfolio_id = f"perf-test-portfolio-{portfolio_index}"
                        
                        # Setup mocks
                        mock_create.return_value = {
                            "id": portfolio_id,
                            "name": f"Performance Test Portfolio {portfolio_index}",
                            "user_id": mock_user.id,
                            "total_value": 10000.00
                        }
                        mock_get.return_value = mock_create.return_value
                        mock_update.return_value = {**mock_create.return_value, "name": f"Updated Portfolio {portfolio_index}"}
                        mock_delete.return_value = True
                        
                        # CREATE
                        create_start = time.time()
                        create_response = await client.post("/api/v1/portfolios", json={
                            "name": f"Performance Test Portfolio {portfolio_index}",
                            "description": f"Performance testing portfolio {portfolio_index}"
                        })
                        create_time = time.time() - create_start
                        
                        # READ
                        read_start = time.time()
                        read_response = await client.get(f"/api/v1/portfolios/{portfolio_id}")
                        read_time = time.time() - read_start
                        
                        # UPDATE
                        update_start = time.time()
                        update_response = await client.put(f"/api/v1/portfolios/{portfolio_id}", json={
                            "name": f"Updated Portfolio {portfolio_index}"
                        })
                        update_time = time.time() - update_start
                        
                        # DELETE
                        delete_start = time.time()
                        delete_response = await client.delete(f"/api/v1/portfolios/{portfolio_id}")
                        delete_time = time.time() - delete_start
                        
                        total_time = time.time() - start_time
                        
                        return {
                            "portfolio_index": portfolio_index,
                            "create_time": create_time,
                            "read_time": read_time,
                            "update_time": update_time,
                            "delete_time": delete_time,
                            "total_time": total_time,
                            "create_success": create_response.status_code == 201,
                            "read_success": read_response.status_code == 200,
                            "update_success": update_response.status_code == 200,
                            "delete_success": delete_response.status_code == 204,
                            "all_success": all([
                                create_response.status_code == 201,
                                read_response.status_code == 200,
                                update_response.status_code == 200,
                                delete_response.status_code == 204
                            ])
                        }
            
            # Run 50 concurrent CRUD cycles
            tasks = [portfolio_crud_cycle(i) for i in range(50)]
            results = await asyncio.gather(*tasks)
            
            # Analyze performance
            successful_cycles = [r for r in results if r["all_success"]]
            success_rate = len(successful_cycles) / len(results)
            
            assert success_rate >= 0.9, f"CRUD success rate {success_rate:.2%} below 90%"
            
            if successful_cycles:
                # Analyze operation times
                create_times = [r["create_time"] for r in successful_cycles]
                read_times = [r["read_time"] for r in successful_cycles]
                update_times = [r["update_time"] for r in successful_cycles]
                delete_times = [r["delete_time"] for r in successful_cycles]
                total_times = [r["total_time"] for r in successful_cycles]
                
                # Performance assertions
                assert statistics.mean(create_times) < 0.5, f"Average CREATE time {statistics.mean(create_times):.3f}s exceeds 0.5s"
                assert statistics.mean(read_times) < 0.3, f"Average READ time {statistics.mean(read_times):.3f}s exceeds 0.3s"
                assert statistics.mean(update_times) < 0.5, f"Average UPDATE time {statistics.mean(update_times):.3f}s exceeds 0.5s"
                assert statistics.mean(delete_times) < 0.3, f"Average DELETE time {statistics.mean(delete_times):.3f}s exceeds 0.3s"
                assert statistics.mean(total_times) < 2.0, f"Average total CRUD time {statistics.mean(total_times):.3f}s exceeds 2s"
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_analytics_performance_under_load(self, mock_user):
        """Test analytics endpoints performance under load"""
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            async def analytics_request_cycle():
                """Single analytics request cycle"""
                async with AsyncClient(app=app, base_url="http://test") as client:
                    
                    with patch('app.services.analytics.ml_service.predict_stock_price') as mock_predict, \
                         patch('app.services.analytics.ml_service.analyze_portfolio_risk') as mock_risk:
                        
                        # Setup mocks for consistent performance testing
                        mock_predict.return_value = {
                            "symbol": "AAPL",
                            "predicted_price": 165.50,
                            "confidence_score": 0.78,
                            "current_price": 155.00,
                            "model_used": "random_forest"
                        }
                        
                        mock_risk.return_value = {
                            "expected_return": 0.12,
                            "volatility": 0.18,
                            "var_95": -0.08,
                            "sharpe_ratio": 0.67
                        }
                        
                        # Stock prediction request
                        prediction_start = time.time()
                        prediction_response = await client.post("/api/v1/analytics/predict/stock-price", json={
                            "symbol": "AAPL",
                            "days_ahead": 30
                        })
                        prediction_time = time.time() - prediction_start
                        
                        # Risk analysis request
                        risk_start = time.time()
                        risk_response = await client.post("/api/v1/analytics/analyze/portfolio-risk", json={
                            "portfolio": {"AAPL": 0.5, "GOOGL": 0.3, "MSFT": 0.2}
                        })
                        risk_time = time.time() - risk_start
                        
                        return {
                            "prediction_time": prediction_time,
                            "risk_time": risk_time,
                            "prediction_success": prediction_response.status_code == 200,
                            "risk_success": risk_response.status_code == 200,
                            "total_time": prediction_time + risk_time
                        }
            
            # Run 30 concurrent analytics cycles
            tasks = [analytics_request_cycle() for _ in range(30)]
            results = await asyncio.gather(*tasks)
            
            # Analyze performance
            successful_results = [r for r in results if r["prediction_success"] and r["risk_success"]]
            success_rate = len(successful_results) / len(results)
            
            assert success_rate >= 0.85, f"Analytics success rate {success_rate:.2%} below 85%"
            
            if successful_results:
                prediction_times = [r["prediction_time"] for r in successful_results]
                risk_times = [r["risk_time"] for r in successful_results]
                total_times = [r["total_time"] for r in successful_results]
                
                # Performance assertions for ML operations (can be slower)
                assert statistics.mean(prediction_times) < 2.0, f"Average prediction time {statistics.mean(prediction_times):.3f}s exceeds 2s"
                assert statistics.mean(risk_times) < 1.5, f"Average risk analysis time {statistics.mean(risk_times):.3f}s exceeds 1.5s"
                assert statistics.mean(total_times) < 3.0, f"Average total analytics time {statistics.mean(total_times):.3f}s exceeds 3s"
        
        finally:
            app.dependency_overrides.clear()


class TestDatabasePerformance:
    """Performance tests for database operations"""
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_performance(self):
        """Test database connection pool performance under load"""
        
        async def database_operation():
            """Single database operation"""
            try:
                # Simulate database session usage
                db = next(get_db())
                start_time = time.time()
                
                # Simulate query execution time
                await asyncio.sleep(0.01)  # 10ms simulated query
                
                end_time = time.time()
                db.close()
                
                return {
                    "success": True,
                    "response_time": end_time - start_time,
                    "error": None
                }
            except Exception as e:
                return {
                    "success": False,
                    "response_time": 0,
                    "error": str(e)
                }
        
        # Test with 100 concurrent database operations
        tasks = [database_operation() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful_ops = [r for r in results if r["success"]]
        success_rate = len(successful_ops) / len(results)
        
        assert success_rate >= 0.95, f"Database operation success rate {success_rate:.2%} below 95%"
        
        if successful_ops:
            response_times = [r["response_time"] for r in successful_ops]
            
            # Performance assertions
            assert statistics.mean(response_times) < 0.1, f"Average DB response time {statistics.mean(response_times):.3f}s exceeds 0.1s"
            assert max(response_times) < 0.5, f"Max DB response time {max(response_times):.3f}s exceeds 0.5s"
    
    def test_large_dataset_processing_performance(self):
        """Test performance with large datasets"""
        
        # Simulate processing large portfolio with many holdings
        large_portfolio_data = {
            "id": "large-portfolio-perf-test",
            "holdings": []
        }
        
        # Create 1000 holdings
        for i in range(1000):
            holding = {
                "id": f"holding-{i}",
                "symbol": f"STOCK{i:04d}",
                "shares": Decimal(str(100 + i)),
                "purchase_price": Decimal(str(50.00 + (i * 0.1))),
                "current_price": Decimal(str(55.00 + (i * 0.1)))
            }
            large_portfolio_data["holdings"].append(holding)
        
        # Test portfolio value calculation performance
        start_time = time.time()
        
        total_value = Decimal("0")
        for holding in large_portfolio_data["holdings"]:
            holding_value = holding["shares"] * holding["current_price"]
            total_value += holding_value
        
        calculation_time = time.time() - start_time
        
        # Performance assertions
        assert calculation_time < 0.1, f"Large portfolio calculation time {calculation_time:.3f}s exceeds 0.1s"
        assert total_value > 0, "Portfolio calculation should produce positive value"
        assert len(large_portfolio_data["holdings"]) == 1000, "All holdings should be processed"
    
    def test_concurrent_portfolio_calculations(self):
        """Test concurrent portfolio calculations performance"""
        
        def calculate_portfolio_performance(portfolio_id):
            """Simulate portfolio performance calculation"""
            start_time = time.time()
            
            # Simulate complex calculations
            holdings_count = 50
            total_value = 0
            
            for i in range(holdings_count):
                # Simulate price calculations
                shares = 100 + i
                current_price = 50.0 + (i * 0.5)
                holding_value = shares * current_price
                total_value += holding_value
                
                # Simulate some processing time
                time.sleep(0.001)  # 1ms per holding
            
            calculation_time = time.time() - start_time
            
            return {
                "portfolio_id": portfolio_id,
                "total_value": total_value,
                "calculation_time": calculation_time,
                "holdings_processed": holdings_count
            }
        
        # Test with 20 concurrent portfolio calculations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(calculate_portfolio_performance, f"portfolio-{i}")
                for i in range(20)
            ]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze performance
        calculation_times = [r["calculation_time"] for r in results]
        
        assert len(results) == 20, "All portfolio calculations should complete"
        assert statistics.mean(calculation_times) < 0.2, f"Average calculation time {statistics.mean(calculation_times):.3f}s exceeds 0.2s"
        assert max(calculation_times) < 0.5, f"Max calculation time {max(calculation_times):.3f}s exceeds 0.5s"
        
        # Verify all calculations produced results
        for result in results:
            assert result["total_value"] > 0
            assert result["holdings_processed"] == 50


class TestMemoryPerformance:
    """Performance tests for memory usage and garbage collection"""
    
    def test_memory_usage_under_load(self):
        """Test memory usage during sustained operations"""
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate sustained operations
        portfolios = []
        for i in range(1000):
            portfolio = {
                "id": f"memory-test-portfolio-{i}",
                "name": f"Memory Test Portfolio {i}",
                "holdings": [
                    {
                        "symbol": f"STOCK{j}",
                        "shares": 100 + j,
                        "price": 50.0 + j
                    }
                    for j in range(10)  # 10 holdings per portfolio
                ]
            }
            portfolios.append(portfolio)
            
            # Simulate processing
            total_value = sum(
                holding["shares"] * holding["price"]
                for holding in portfolio["holdings"]
            )
            portfolio["total_value"] = total_value
            
            # Force garbage collection every 100 iterations
            if i % 100 == 0:
                gc.collect()
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Performance assertions
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB, exceeds 100MB limit"
        assert len(portfolios) == 1000, "All portfolios should be created"
        
        # Cleanup
        del portfolios
        gc.collect()
    
    def test_garbage_collection_performance(self):
        """Test garbage collection impact on performance"""
        
        # Create objects that will need garbage collection
        large_objects = []
        
        start_time = time.time()
        
        for i in range(10000):
            # Create objects with circular references
            obj = {
                "id": i,
                "data": [j for j in range(100)],
                "timestamp": datetime.utcnow()
            }
            obj["self_ref"] = obj  # Circular reference
            large_objects.append(obj)
        
        creation_time = time.time() - start_time
        
        # Force garbage collection
        gc_start = time.time()
        collected = gc.collect()
        gc_time = time.time() - gc_start
        
        # Performance assertions
        assert creation_time < 1.0, f"Object creation time {creation_time:.3f}s exceeds 1s"
        assert gc_time < 0.1, f"Garbage collection time {gc_time:.3f}s exceeds 0.1s"
        
        # Cleanup
        del large_objects
        gc.collect()
    
    def test_memory_leak_detection(self):
        """Test for potential memory leaks in repeated operations"""
        
        def simulate_request_cycle():
            """Simulate a complete request processing cycle"""
            # Simulate user authentication
            user = {
                "id": "leak-test-user",
                "email": "leak.test@example.com",
                "portfolios": []
            }
            
            # Simulate portfolio operations
            for i in range(10):
                portfolio = {
                    "id": f"portfolio-{i}",
                    "user_id": user["id"],
                    "holdings": [
                        {"symbol": f"STOCK{j}", "shares": 100, "price": 50.0}
                        for j in range(5)
                    ]
                }
                user["portfolios"].append(portfolio)
            
            # Simulate analytics calculations
            for portfolio in user["portfolios"]:
                total_value = sum(
                    holding["shares"] * holding["price"]
                    for holding in portfolio["holdings"]
                )
                portfolio["performance"] = {
                    "total_value": total_value,
                    "return_percentage": (total_value - 2500) / 2500 * 100
                }
            
            return user
        
        # Measure memory before cycles
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run many request cycles
        for cycle in range(100):
            user_data = simulate_request_cycle()
            
            # Simulate request completion (cleanup)
            del user_data
            
            # Periodic garbage collection
            if cycle % 10 == 0:
                gc.collect()
        
        # Measure memory after cycles
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory leak assertion
        assert memory_increase < 50, f"Potential memory leak detected: {memory_increase:.2f}MB increase"


class TestConcurrencyPerformance:
    """Performance tests for concurrent operations"""
    
    @pytest.mark.asyncio
    async def test_concurrent_user_sessions(self):
        """Test performance with multiple concurrent user sessions"""
        
        async def simulate_user_session(user_id):
            """Simulate a complete user session"""
            session_start = time.time()
            
            # Simulate user authentication
            auth_time = 0.01  # 10ms auth simulation
            await asyncio.sleep(auth_time)
            
            # Simulate portfolio operations
            portfolio_ops_start = time.time()
            
            # Create portfolio
            await asyncio.sleep(0.02)  # 20ms create simulation
            
            # Add holdings
            for _ in range(5):
                await asyncio.sleep(0.01)  # 10ms per holding
            
            # Calculate performance
            await asyncio.sleep(0.03)  # 30ms calculation simulation
            
            portfolio_ops_time = time.time() - portfolio_ops_start
            total_session_time = time.time() - session_start
            
            return {
                "user_id": user_id,
                "auth_time": auth_time,
                "portfolio_ops_time": portfolio_ops_time,
                "total_session_time": total_session_time,
                "success": True
            }
        
        # Simulate 50 concurrent user sessions
        tasks = [simulate_user_session(f"user-{i}") for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        # Analyze performance
        successful_sessions = [r for r in results if r["success"]]
        success_rate = len(successful_sessions) / len(results)
        
        assert success_rate >= 0.95, f"Concurrent session success rate {success_rate:.2%} below 95%"
        
        if successful_sessions:
            session_times = [r["total_session_time"] for r in successful_sessions]
            portfolio_times = [r["portfolio_ops_time"] for r in successful_sessions]
            
            # Performance assertions
            assert statistics.mean(session_times) < 0.2, f"Average session time {statistics.mean(session_times):.3f}s exceeds 0.2s"
            assert statistics.mean(portfolio_times) < 0.15, f"Average portfolio ops time {statistics.mean(portfolio_times):.3f}s exceeds 0.15s"
            assert max(session_times) < 0.5, f"Max session time {max(session_times):.3f}s exceeds 0.5s"
    
    def test_thread_pool_performance(self):
        """Test thread pool performance for CPU-intensive tasks"""
        
        def cpu_intensive_calculation(data_size):
            """Simulate CPU-intensive financial calculation"""
            start_time = time.time()
            
            # Simulate complex financial calculations
            result = 0
            for i in range(data_size):
                # Simulate portfolio value calculation
                price = 50.0 + (i * 0.01)
                shares = 100 + i
                value = price * shares
                
                # Simulate risk calculation
                volatility = 0.15 + (i * 0.0001)
                risk_adjusted_value = value * (1 - volatility)
                
                result += risk_adjusted_value
            
            calculation_time = time.time() - start_time
            
            return {
                "data_size": data_size,
                "result": result,
                "calculation_time": calculation_time
            }
        
        # Test with different data sizes and thread pool
        data_sizes = [1000, 2000, 3000, 4000, 5000]
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(cpu_intensive_calculation, size)
                for size in data_sizes
            ]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze performance
        calculation_times = [r["calculation_time"] for r in results]
        
        assert len(results) == len(data_sizes), "All calculations should complete"
        assert statistics.mean(calculation_times) < 0.1, f"Average calculation time {statistics.mean(calculation_times):.3f}s exceeds 0.1s"
        
        # Verify results are reasonable
        for result in results:
            assert result["result"] > 0, "Calculations should produce positive results"
            assert result["calculation_time"] > 0, "Calculation time should be positive"


class TestScalabilityLimits:
    """Tests to identify scalability limits and bottlenecks"""
    
    @pytest.mark.asyncio
    async def test_maximum_concurrent_requests(self):
        """Test system behavior at maximum concurrent request load"""
        
        async def stress_test_request():
            """Single stress test request"""
            try:
                async with AsyncClient(app=app, base_url="http://test") as client:
                    start_time = time.time()
                    response = await client.get("/api/v1/health")
                    end_time = time.time()
                    
                    return {
                        "success": response.status_code == 200,
                        "response_time": end_time - start_time,
                        "status_code": response.status_code
                    }
            except Exception as e:
                return {
                    "success": False,
                    "response_time": 0,
                    "status_code": 0,
                    "error": str(e)
                }
        
        # Gradually increase load to find limits
        load_levels = [50, 100, 200, 300, 500]
        results_by_load = {}
        
        for load_level in load_levels:
            print(f"Testing with {load_level} concurrent requests...")
            
            tasks = [stress_test_request() for _ in range(load_level)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and analyze results
            valid_results = [r for r in results if isinstance(r, dict)]
            successful_results = [r for r in valid_results if r["success"]]
            
            success_rate = len(successful_results) / len(valid_results) if valid_results else 0
            avg_response_time = statistics.mean([r["response_time"] for r in successful_results]) if successful_results else 0
            
            results_by_load[load_level] = {
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "total_requests": len(valid_results),
                "successful_requests": len(successful_results)
            }
            
            # Stop if success rate drops below 80%
            if success_rate < 0.8:
                print(f"Success rate dropped to {success_rate:.2%} at {load_level} concurrent requests")
                break
        
        # Analyze scalability limits
        max_successful_load = max([
            load for load, metrics in results_by_load.items()
            if metrics["success_rate"] >= 0.9
        ])
        
        assert max_successful_load >= 100, f"System should handle at least 100 concurrent requests, max successful: {max_successful_load}"
        
        # Performance degradation analysis
        for load_level, metrics in results_by_load.items():
            print(f"Load {load_level}: {metrics['success_rate']:.2%} success, {metrics['avg_response_time']:.3f}s avg response")
    
    def test_memory_scalability_limits(self):
        """Test memory usage scalability limits"""
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Gradually increase data size to find memory limits
        data_sizes = [1000, 5000, 10000, 20000, 50000]
        memory_usage_by_size = {}
        
        for data_size in data_sizes:
            # Create large dataset
            large_dataset = []
            
            for i in range(data_size):
                portfolio = {
                    "id": f"scalability-portfolio-{i}",
                    "name": f"Scalability Test Portfolio {i}",
                    "user_id": f"user-{i % 100}",  # 100 different users
                    "holdings": [
                        {
                            "symbol": f"STOCK{j}",
                            "shares": 100 + j,
                            "purchase_price": 50.0 + (j * 0.1),
                            "current_price": 55.0 + (j * 0.1)
                        }
                        for j in range(10)  # 10 holdings per portfolio
                    ],
                    "performance_history": [
                        {
                            "date": f"2024-{(k % 12) + 1:02d}-01",
                            "value": 10000 + (k * 100),
                            "return": k * 0.5
                        }
                        for k in range(12)  # 12 months of history
                    ]
                }
                large_dataset.append(portfolio)
            
            # Measure memory usage
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            memory_usage_by_size[data_size] = {
                "memory_mb": memory_increase,
                "memory_per_item_kb": (memory_increase * 1024) / data_size if data_size > 0 else 0
            }
            
            # Clean up
            del large_dataset
            gc.collect()
            
            # Stop if memory usage exceeds 500MB
            if memory_increase > 500:
                print(f"Memory usage exceeded 500MB at {data_size} items")
                break
        
        # Analyze memory scalability
        max_items_under_limit = max([
            size for size, metrics in memory_usage_by_size.items()
            if metrics["memory_mb"] <= 200  # 200MB limit
        ])
        
        assert max_items_under_limit >= 5000, f"System should handle at least 5000 items under 200MB, max: {max_items_under_limit}"
        
        # Memory efficiency analysis
        for data_size, metrics in memory_usage_by_size.items():
            print(f"Data size {data_size}: {metrics['memory_mb']:.2f}MB total, {metrics['memory_per_item_kb']:.2f}KB per item")


class TestPerformanceBenchmarks:
    """Benchmark tests to establish performance baselines"""
    
    def test_financial_calculation_benchmarks(self):
        """Benchmark financial calculation performance"""
        
        def benchmark_portfolio_calculations():
            """Benchmark various portfolio calculations"""
            
            # Setup test data
            holdings = [
                {
                    "symbol": f"STOCK{i:04d}",
                    "shares": Decimal(str(100 + i)),
                    "purchase_price": Decimal(str(50.00 + (i * 0.1))),
                    "current_price": Decimal(str(55.00 + (i * 0.1)))
                }
                for i in range(100)
            ]
            
            benchmarks = {}
            
            # Benchmark 1: Portfolio value calculation
            start_time = time.time()
            total_value = sum(
                holding["shares"] * holding["current_price"]
                for holding in holdings
            )
            benchmarks["portfolio_value"] = time.time() - start_time
            
            # Benchmark 2: Return calculation
            start_time = time.time()
            total_cost = sum(
                holding["shares"] * holding["purchase_price"]
                for holding in holdings
            )
            total_return = ((total_value - total_cost) / total_cost) * 100
            benchmarks["return_calculation"] = time.time() - start_time
            
            # Benchmark 3: Asset allocation calculation
            start_time = time.time()
            allocations = {}
            for holding in holdings:
                holding_value = holding["shares"] * holding["current_price"]
                allocation_percentage = (holding_value / total_value) * 100
                allocations[holding["symbol"]] = allocation_percentage
            benchmarks["asset_allocation"] = time.time() - start_time
            
            # Benchmark 4: Risk metrics calculation (simplified)
            start_time = time.time()
            returns = [
                ((holding["current_price"] - holding["purchase_price"]) / holding["purchase_price"])
                for holding in holdings
            ]
            avg_return = statistics.mean(returns)
            volatility = statistics.stdev(returns) if len(returns) > 1 else 0
            benchmarks["risk_metrics"] = time.time() - start_time
            
            return benchmarks, {
                "total_value": float(total_value),
                "total_return": float(total_return),
                "avg_return": avg_return,
                "volatility": volatility,
                "holdings_count": len(holdings)
            }
        
        # Run benchmark multiple times for accuracy
        benchmark_runs = []
        for _ in range(10):
            benchmarks, results = benchmark_portfolio_calculations()
            benchmark_runs.append(benchmarks)
        
        # Calculate average benchmark times
        avg_benchmarks = {}
        for operation in benchmark_runs[0].keys():
            times = [run[operation] for run in benchmark_runs]
            avg_benchmarks[operation] = {
                "avg_time": statistics.mean(times),
                "min_time": min(times),
                "max_time": max(times),
                "std_dev": statistics.stdev(times) if len(times) > 1 else 0
            }
        
        # Performance assertions (benchmarks for 100 holdings)
        assert avg_benchmarks["portfolio_value"]["avg_time"] < 0.001, f"Portfolio value calculation too slow: {avg_benchmarks['portfolio_value']['avg_time']:.6f}s"
        assert avg_benchmarks["return_calculation"]["avg_time"] < 0.002, f"Return calculation too slow: {avg_benchmarks['return_calculation']['avg_time']:.6f}s"
        assert avg_benchmarks["asset_allocation"]["avg_time"] < 0.005, f"Asset allocation calculation too slow: {avg_benchmarks['asset_allocation']['avg_time']:.6f}s"
        assert avg_benchmarks["risk_metrics"]["avg_time"] < 0.003, f"Risk metrics calculation too slow: {avg_benchmarks['risk_metrics']['avg_time']:.6f}s"
        
        # Print benchmark results
        print("\nFinancial Calculation Benchmarks (100 holdings):")
        for operation, metrics in avg_benchmarks.items():
            print(f"  {operation}: {metrics['avg_time']:.6f}s avg, {metrics['min_time']:.6f}s min, {metrics['max_time']:.6f}s max")
    
    @pytest.mark.asyncio
    async def test_api_response_time_benchmarks(self):
        """Benchmark API response times for different endpoints"""
        
        async def benchmark_endpoint(endpoint, method="GET", json_data=None):
            """Benchmark a single API endpoint"""
            
            response_times = []
            
            for _ in range(20):  # 20 requests per endpoint
                async with AsyncClient(app=app, base_url="http://test") as client:
                    start_time = time.time()
                    
                    if method == "GET":
                        response = await client.get(endpoint)
                    elif method == "POST":
                        response = await client.post(endpoint, json=json_data)
                    
                    end_time = time.time()
                    
                    if response.status_code < 500:  # Don't count server errors
                        response_times.append(end_time - start_time)
            
            if response_times:
                return {
                    "avg_time": statistics.mean(response_times),
                    "min_time": min(response_times),
                    "max_time": max(response_times),
                    "p95_time": sorted(response_times)[int(0.95 * len(response_times))],
                    "requests_count": len(response_times)
                }
            else:
                return None
        
        # Benchmark different endpoints
        endpoints_to_benchmark = [
            ("/api/v1/health", "GET", None),
            ("/api/v1/monitoring/metrics", "GET", None),
        ]
        
        benchmark_results = {}
        
        for endpoint, method, json_data in endpoints_to_benchmark:
            print(f"Benchmarking {method} {endpoint}...")
            result = await benchmark_endpoint(endpoint, method, json_data)
            if result:
                benchmark_results[f"{method} {endpoint}"] = result
        
        # Performance assertions
        for endpoint_key, metrics in benchmark_results.items():
            assert metrics["avg_time"] < 0.5, f"{endpoint_key} average response time {metrics['avg_time']:.3f}s exceeds 0.5s"
            assert metrics["p95_time"] < 1.0, f"{endpoint_key} 95th percentile {metrics['p95_time']:.3f}s exceeds 1.0s"
            assert metrics["max_time"] < 2.0, f"{endpoint_key} max response time {metrics['max_time']:.3f}s exceeds 2.0s"
        
        # Print benchmark results
        print("\nAPI Response Time Benchmarks:")
        for endpoint, metrics in benchmark_results.items():
            print(f"  {endpoint}:")
            print(f"    Average: {metrics['avg_time']:.3f}s")
            print(f"    95th percentile: {metrics['p95_time']:.3f}s")
            print(f"    Max: {metrics['max_time']:.3f}s")
            print(f"    Requests: {metrics['requests_count']}")


# Performance Test Configuration
PERFORMANCE_THRESHOLDS = {
    "api_response_time": {
        "average": 0.5,  # 500ms
        "p95": 1.0,      # 1 second
        "p99": 2.0       # 2 seconds
    },
    "database_operations": {
        "average": 0.1,  # 100ms
        "max": 0.5       # 500ms
    },
    "memory_usage": {
        "max_increase": 100,  # 100MB
        "per_operation": 1    # 1MB per operation
    },
    "concurrent_users": {
        "min_supported": 100,
        "success_rate": 0.9   # 90%
    }
}