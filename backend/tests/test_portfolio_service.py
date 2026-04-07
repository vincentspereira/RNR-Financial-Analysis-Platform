"""
Tests for portfolio service database integration (Phase 2, Task 2.1)
"""
import pytest
from decimal import Decimal
from uuid import uuid4

from app.services.portfolio.portfolio_service import PortfolioService


@pytest.fixture
def service():
    return PortfolioService()


class TestPortfolioCRUD:
    """Test CRUD operations for portfolios"""

    @pytest.mark.asyncio
    async def test_create_portfolio(self, service, db_session, sample_portfolio_data):
        user_id = str(uuid4())
        portfolio = await service.create_portfolio(db_session, user_id, sample_portfolio_data)

        assert portfolio is not None
        assert portfolio.name == "Test Portfolio"
        assert portfolio.description == "A test portfolio"
        assert portfolio.cash_balance == Decimal("10000.00")
        assert portfolio.is_active is True

    @pytest.mark.asyncio
    async def test_get_portfolio(self, service, db_session, sample_portfolio_data):
        user_id = str(uuid4())
        created = await service.create_portfolio(db_session, user_id, sample_portfolio_data)

        fetched = await service.get_portfolio(db_session, str(created.id), user_id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "Test Portfolio"

    @pytest.mark.asyncio
    async def test_get_portfolio_wrong_user(self, service, db_session, sample_portfolio_data):
        user_id = str(uuid4())
        created = await service.create_portfolio(db_session, user_id, sample_portfolio_data)

        other_user = str(uuid4())
        fetched = await service.get_portfolio(db_session, str(created.id), other_user)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_get_portfolios(self, service, db_session):
        user_id = str(uuid4())
        for i in range(3):
            await service.create_portfolio(db_session, user_id, {
                "name": f"Portfolio {i}",
                "cash_balance": "1000.00",
            })

        portfolios = await service.get_portfolios(db_session, user_id)
        assert len(portfolios) == 3

    @pytest.mark.asyncio
    async def test_get_portfolios_paginated(self, service, db_session):
        user_id = str(uuid4())
        for i in range(5):
            await service.create_portfolio(db_session, user_id, {
                "name": f"Portfolio {i}",
                "cash_balance": "1000.00",
            })

        result = await service.get_portfolios_paginated(db_session, user_id, skip=0, limit=2)
        assert result["total"] == 5
        assert len(result["portfolios"]) == 2
        assert result["has_more"] is True

    @pytest.mark.asyncio
    async def test_update_portfolio(self, service, db_session, sample_portfolio_data):
        user_id = str(uuid4())
        created = await service.create_portfolio(db_session, user_id, sample_portfolio_data)

        updated = await service.update_portfolio(
            db_session, str(created.id), user_id,
            {"name": "Updated Name", "description": "Updated desc"}
        )
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "Updated desc"

    @pytest.mark.asyncio
    async def test_update_portfolio_wrong_field_ignored(self, service, db_session, sample_portfolio_data):
        user_id = str(uuid4())
        created = await service.create_portfolio(db_session, user_id, sample_portfolio_data)

        updated = await service.update_portfolio(
            db_session, str(created.id), user_id,
            {"id": str(uuid4()), "name": "Safe Update"}
        )
        assert str(updated.id) == str(created.id)
        assert updated.name == "Safe Update"

    @pytest.mark.asyncio
    async def test_delete_portfolio_soft(self, service, db_session, sample_portfolio_data):
        user_id = str(uuid4())
        created = await service.create_portfolio(db_session, user_id, sample_portfolio_data)

        deleted = await service.delete_portfolio(db_session, str(created.id), user_id)
        assert deleted is True

        # Verify soft delete
        fetched = await service.get_portfolio(db_session, str(created.id), user_id)
        assert fetched is None  # get_portfolio filters by is_active

    @pytest.mark.asyncio
    async def test_delete_nonexistent_portfolio(self, service, db_session):
        result = await service.delete_portfolio(db_session, str(uuid4()), str(uuid4()))
        assert result is False

    @pytest.mark.asyncio
    async def test_get_portfolio_performance_empty(self, service, db_session, sample_portfolio_data):
        user_id = str(uuid4())
        created = await service.create_portfolio(db_session, user_id, sample_portfolio_data)

        perf = await service.get_portfolio_performance(db_session, str(created.id), user_id)
        assert perf is not None
        assert perf["number_of_holdings"] == 0
        assert perf["total_invested"] == 0.0
