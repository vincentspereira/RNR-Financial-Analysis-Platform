"""
Performance tests for RNR Financial Analysis Platform
"""
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.services.calculator.financial_calculator import FinancialCalculator
from app.services.calculator.ratio_calculator import RatioCalculator


class TestLoadPerformance:
    """Load testing for system throughput and response times"""
    
    @pytest.fixture
    async def client(self):
        """Create test client for load testing"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.performance
    @pytest.mark.benchmark
    async def test_api_response_time_baseline(self, client, benchmark):
        """Establish baseline metrics for API response times"""
        
        async def health_check():
            response = await client.get("/api/v1/health")
            return response.status_code
        
        # Benchmark health check endpoint
        result = benchmark(lambda: asyncio.run(health_check()))
        assert result == 200
    
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_concurrent_api_requests(self, client):
        """Test API performance under concurrent load"""
        
        async def make_request():
            response = await client.get("/api/v1/health")
            return response.status_code, response.elapsed.total_seconds()
        
        # Test with increasing concurrent users
        concurrent_users = [10, 25, 50, 100]
        results = {}
        
        for users in concurrent_users:
            start_time = time.time()
            
            # Create concurrent tasks
            tasks = [make_request() for _ in range(users)]
            responses = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate metrics
            successful_requests = sum(1 for status, _ in responses if status == 200)
            avg_response_time = sum(elapsed for _, elapsed in responses) / len(responses)
            throughput = successful_requests / total_time
            
            results[users] = {
                'success_rate': successful_requests / users,
                'avg_response_time': avg_response_time,
                'throughput': throughput,
                'total_time': total_time
            }
            
            # Performance assertions
            assert successful_requests / users >= 0.95  # 95% success rate
            assert avg_response_time < 1.0  # Under 1 second average
        
        # Verify performance doesn't degrade significantly with load
        assert results[100]['avg_response_time'] < results[10]['avg_response_time'] * 3
    
    @pytest.mark.performance
    @pytest.mark.benchmark
    def test_financial_calculation_performance(self, benchmark):
        """Benchmark financial calculation performance"""
        
        calculator = RatioCalculator()
        
        sample_data = {
            'current_assets': 800000000,
            'current_liabilities': 400000000,
            'cash_and_equivalents': 200000000,
            'inventory': 100000000,
            'revenue': 1000000000,
            'net_income': 150000000,
            'total_assets': 2000000000,
            'shareholders_equity': 1000000000,
            'gross_profit': 400000000,
            'operating_income': 200000000,
            'ebitda': 250000000,
            'total_debt': 600000000,
            'cost_of_goods_sold': 600000000,
            'operating_cash_flow': 180000000,
            'shares_outstanding': 100000000,
            'stock_price': 50.0
        }
        
        def calculate_all_ratios():
            liquidity = calculator.calculate_liquidity_ratios(sample_data)
            profitability = calculator.calculate_profitability_ratios(sample_data)
            leverage = calculator.calculate_leverage_ratios(sample_data)
            efficiency = calculator.calculate_efficiency_ratios(sample_data)
            valuation = calculator.calculate_valuation_ratios(sample_data)
            
            return {
                **liquidity,
                **profitability,
                **leverage,
                **efficiency,
                **valuation
            }
        
        # Benchmark the calculation
        result = benchmark(calculate_all_ratios)
        
        # Performance assertions
        assert result is not None
        assert len(result) > 10  # Should calculate multiple ratios
    
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_batch_processing_performance(self):
        """Test batch processing performance with multiple companies"""
        
        calculator = FinancialCalculator()
        mock_db = AsyncMock()
        
        # Mock financial data for multiple companies
        sample_data = {
            'revenue': 1000000000,
            'net_income': 150000000,
            'total_assets': 2000000000,
            'current_assets': 800000000,
            'current_liabilities': 400000000,
            'shareholders_equity': 1000000000
        }
        
        with patch.object(calculator, 'get_company_financial_data') as mock_get_data:
            mock_get_data.return_value = sample_data
            
            # Test batch sizes
            batch_sizes = [5, 10, 25, 50]
            
            for batch_size in batch_sizes:
                company_ids = [f"company_{i}" for i in range(batch_size)]
                
                start_time = time.time()
                
                # Process batch concurrently
                tasks = []
                for company_id in company_ids:
                    task = calculator.calculate_financial_ratios(
                        company_id=company_id,
                        period_type='annual',
                        fiscal_year=2023,
                        db=mock_db
                    )
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                # Performance assertions
                successful_results = sum(1 for result in results if result is not None)
                assert successful_results == batch_size
                assert processing_time < batch_size * 0.1  # Should be faster than sequential
                
                # Calculate throughput
                throughput = batch_size / processing_time
                print(f"Batch size {batch_size}: {throughput:.2f} calculations/second")


class TestStressPerformance:
    """Stress testing to identify breaking points"""
    
    @pytest.mark.performance
    @pytest.mark.stress
    async def test_memory_usage_under_load(self):
        """Test memory usage under heavy calculation load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        calculator = RatioCalculator()
        
        # Generate large dataset
        large_datasets = []
        for i in range(1000):
            dataset = {
                'current_assets': 800000000 + i,
                'current_liabilities': 400000000 + i,
                'revenue': 1000000000 + i,
                'net_income': 150000000 + i,
                'total_assets': 2000000000 + i,
                'shareholders_equity': 1000000000 + i
            }
            large_datasets.append(dataset)
        
        # Process all datasets
        results = []
        for dataset in large_datasets:
            ratios = calculator.calculate_liquidity_ratios(dataset)
            results.append(ratios)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory usage assertions
        assert memory_increase < 100  # Should not increase by more than 100MB
        assert len(results) == 1000
        
        print(f"Memory usage: {initial_memory:.2f}MB -> {final_memory:.2f}MB (+{memory_increase:.2f}MB)")
    
    @pytest.mark.performance
    @pytest.mark.stress
    async def test_cpu_usage_under_load(self):
        """Test CPU usage under computational load"""
        import psutil
        
        calculator = RatioCalculator()
        
        # Monitor CPU usage
        cpu_percent_before = psutil.cpu_percent(interval=1)
        
        # Intensive calculation workload
        start_time = time.time()
        
        tasks = []
        for i in range(100):
            dataset = {
                'current_assets': 800000000,
                'current_liabilities': 400000000,
                'revenue': 1000000000,
                'net_income': 150000000,
                'total_assets': 2000000000,
                'shareholders_equity': 1000000000,
                'gross_profit': 400000000,
                'operating_income': 200000000,
                'ebitda': 250000000
            }
            
            # Calculate all ratio types
            liquidity = calculator.calculate_liquidity_ratios(dataset)
            profitability = calculator.calculate_profitability_ratios(dataset)
            leverage = calculator.calculate_leverage_ratios(dataset)
            efficiency = calculator.calculate_efficiency_ratios(dataset)
            
            tasks.append((liquidity, profitability, leverage, efficiency))
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        cpu_percent_after = psutil.cpu_percent(interval=1)
        
        # Performance assertions
        assert len(tasks) == 100
        assert processing_time < 10.0  # Should complete within 10 seconds
        
        print(f"CPU usage: {cpu_percent_before}% -> {cpu_percent_after}%")
        print(f"Processing time: {processing_time:.2f} seconds")
    
    @pytest.mark.performance
    @pytest.mark.stress
    async def test_concurrent_user_breaking_point(self):
        """Test system behavior at concurrent user limits"""
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            
            async def simulate_user_session():
                try:
                    # Simulate user workflow
                    health_response = await client.get("/api/v1/health")
                    
                    if health_response.status_code == 200:
                        return True
                    return False
                except Exception:
                    return False
            
            # Test increasing concurrent users until breaking point
            max_users = 500
            step_size = 50
            breaking_point = None
            
            for concurrent_users in range(step_size, max_users + 1, step_size):
                start_time = time.time()
                
                # Create concurrent user sessions
                tasks = [simulate_user_session() for _ in range(concurrent_users)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                end_time = time.time()
                
                # Calculate success metrics
                successful_sessions = sum(1 for result in results if result is True)
                success_rate = successful_sessions / concurrent_users
                avg_response_time = (end_time - start_time) / concurrent_users
                
                print(f"Users: {concurrent_users}, Success Rate: {success_rate:.2%}, Avg Response: {avg_response_time:.3f}s")
                
                # Check if we've hit breaking point
                if success_rate < 0.90 or avg_response_time > 5.0:
                    breaking_point = concurrent_users
                    break
            
            # System should handle at least 100 concurrent users
            assert breaking_point is None or breaking_point >= 100


class TestEndurancePerformance:
    """Endurance testing for long-running operations"""
    
    @pytest.mark.performance
    @pytest.mark.endurance
    @pytest.mark.slow
    async def test_long_running_calculation_stability(self):
        """Test system stability during long-running calculations"""
        
        calculator = RatioCalculator()
        
        # Run calculations for extended period
        duration_minutes = 5  # 5 minute endurance test
        end_time = time.time() + (duration_minutes * 60)
        
        calculation_count = 0
        error_count = 0
        
        while time.time() < end_time:
            try:
                sample_data = {
                    'current_assets': 800000000,
                    'current_liabilities': 400000000,
                    'revenue': 1000000000,
                    'net_income': 150000000,
                    'total_assets': 2000000000,
                    'shareholders_equity': 1000000000
                }
                
                ratios = calculator.calculate_liquidity_ratios(sample_data)
                
                if ratios and 'current_ratio' in ratios:
                    calculation_count += 1
                else:
                    error_count += 1
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)
                
            except Exception as e:
                error_count += 1
                print(f"Calculation error: {e}")
        
        # Endurance assertions
        total_operations = calculation_count + error_count
        error_rate = error_count / total_operations if total_operations > 0 else 0
        
        assert calculation_count > 0
        assert error_rate < 0.01  # Less than 1% error rate
        assert calculation_count > 1000  # Should complete many calculations
        
        print(f"Endurance test: {calculation_count} successful calculations, {error_count} errors")
        print(f"Error rate: {error_rate:.2%}")
    
    @pytest.mark.performance
    @pytest.mark.endurance
    async def test_memory_leak_detection(self):
        """Test for memory leaks during extended operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Record initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_samples = [initial_memory]
        
        calculator = RatioCalculator()
        
        # Run operations and sample memory usage
        for cycle in range(100):
            # Perform calculations
            for i in range(10):
                sample_data = {
                    'current_assets': 800000000 + i,
                    'current_liabilities': 400000000 + i,
                    'revenue': 1000000000 + i,
                    'net_income': 150000000 + i,
                    'total_assets': 2000000000 + i,
                    'shareholders_equity': 1000000000 + i
                }
                
                ratios = calculator.calculate_liquidity_ratios(sample_data)
                del ratios  # Explicit cleanup
            
            # Sample memory every 10 cycles
            if cycle % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
        
        final_memory = process.memory_info().rss / 1024 / 1024
        
        # Analyze memory trend
        memory_increase = final_memory - initial_memory
        max_memory = max(memory_samples)
        
        # Memory leak assertions
        assert memory_increase < 50  # Should not increase by more than 50MB
        assert max_memory < initial_memory + 100  # Peak should not exceed 100MB increase
        
        print(f"Memory trend: {initial_memory:.2f}MB -> {final_memory:.2f}MB (peak: {max_memory:.2f}MB)")
    
    @pytest.mark.performance
    @pytest.mark.endurance
    async def test_database_connection_stability(self):
        """Test database connection stability over time"""
        
        from app.services.auth.auth_service import auth_service
        
        mock_db = AsyncMock()
        
        # Simulate long-running database operations
        operation_count = 0
        error_count = 0
        
        for i in range(1000):
            try:
                # Mock successful database operation
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none.return_value = None
                mock_db.execute.return_value = mock_result
                
                # Simulate user registration (database operation)
                with patch("app.services.auth.password_handler.PasswordHandler.hash_password") as mock_hash:
                    mock_hash.return_value = "hashed_password"
                    
                    result = await auth_service.register_user(
                        email=f"test{i}@example.com",
                        password="password123",
                        name=f"Test User {i}",
                        db=mock_db
                    )
                    
                    if result:
                        operation_count += 1
                    else:
                        error_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"Database operation error: {e}")
        
        # Stability assertions
        total_operations = operation_count + error_count
        success_rate = operation_count / total_operations if total_operations > 0 else 0
        
        assert success_rate > 0.99  # 99% success rate
        assert operation_count > 900  # Most operations should succeed
        
        print(f"Database stability: {operation_count}/{total_operations} successful operations")


class TestPerformanceMetrics:
    """Performance metrics collection and validation"""
    
    @pytest.mark.performance
    @pytest.mark.monitoring
    def test_performance_baseline_establishment(self):
        """Establish performance baselines for monitoring"""
        
        calculator = RatioCalculator()
        
        sample_data = {
            'current_assets': 800000000,
            'current_liabilities': 400000000,
            'revenue': 1000000000,
            'net_income': 150000000,
            'total_assets': 2000000000,
            'shareholders_equity': 1000000000
        }
        
        # Measure baseline performance
        iterations = 100
        start_time = time.time()
        
        for _ in range(iterations):
            ratios = calculator.calculate_liquidity_ratios(sample_data)
        
        end_time = time.time()
        
        # Calculate baseline metrics
        total_time = end_time - start_time
        avg_time_per_calculation = total_time / iterations
        calculations_per_second = iterations / total_time
        
        # Performance baselines
        baseline_metrics = {
            'avg_calculation_time': avg_time_per_calculation,
            'calculations_per_second': calculations_per_second,
            'total_time_100_calculations': total_time
        }
        
        # Baseline assertions
        assert avg_time_per_calculation < 0.01  # Under 10ms per calculation
        assert calculations_per_second > 100    # At least 100 calculations/second
        
        print(f"Performance Baselines:")
        print(f"  Average calculation time: {avg_time_per_calculation:.4f}s")
        print(f"  Calculations per second: {calculations_per_second:.2f}")
        print(f"  Total time (100 calcs): {total_time:.4f}s")
        
        return baseline_metrics