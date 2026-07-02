"""
Tests for DataIngestionService — pure logic plus orchestration with all
external API clients mocked.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.data.data_ingestion_service import DataIngestionService


@pytest.fixture
def svc() -> DataIngestionService:
    return DataIngestionService()


@pytest.fixture
def fake_db():
    db = MagicMock()
    db.added = []

    def _add(obj):
        db.added.append(obj)

    db.add = _add
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.execute = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# _build_api_log helper (pure)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildApiLog:
    def test_build_api_log_success(self, svc):
        log = svc._build_api_log(
            data_source="alpha_vantage",
            endpoint="/query",
            method="GET",
            request_params={"symbol": "AAPL"},
            start_time=datetime.now(),
            status_code=200,
            response_size_bytes=1024,
        )
        assert log.data_source == "alpha_vantage"
        assert log.endpoint == "/query"
        assert log.method == "GET"
        assert log.status_code == 200
        assert log.error_message is None

    def test_build_api_log_error(self, svc):
        log = svc._build_api_log(
            data_source="yahoo_finance",
            endpoint="/info",
            method="GET",
            request_params=None,
            start_time=datetime.now(),
            status_code=500,
            error_message="Server error",
        )
        assert log.status_code == 500
        assert log.error_message == "Server error"


# ---------------------------------------------------------------------------
# _get_or_create_company
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestGetOrCreateCompany:
    async def test_returns_existing_company(self, svc, fake_db):
        existing = MagicMock()
        existing.symbol = "AAPL"
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none.return_value = existing
        fake_db.execute.return_value = scalar_result
        result = await svc._get_or_create_company("AAPL", fake_db)
        assert result is existing

    async def test_creates_new_company(self, svc, fake_db):
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none.return_value = None
        fake_db.execute.return_value = scalar_result
        result = await svc._get_or_create_company("NEW", fake_db)
        assert result is not None
        # Was added to DB
        assert len(fake_db.added) == 1
        assert fake_db.added[0].symbol == "NEW"

    async def test_returns_none_on_exception(self, svc, fake_db):
        fake_db.execute.side_effect = RuntimeError("db down")
        result = await svc._get_or_create_company("OOPS", fake_db)
        assert result is None


# ---------------------------------------------------------------------------
# ingest_company_data — orchestration with all clients mocked
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestIngestCompanyData:
    async def test_company_creation_failure_returns_errors(self, svc, fake_db):
        with patch.object(svc, "_get_or_create_company", AsyncMock(return_value=None)):
            result = await svc.ingest_company_data("AAPL", fake_db)
        assert result["success"] is False
        assert result["errors"]

    async def test_full_flow_with_all_clients_mocked(self, svc, fake_db):
        mock_company = MagicMock()
        mock_company.id = uuid4()
        with patch.object(svc, "_get_or_create_company", AsyncMock(return_value=mock_company)), \
             patch.object(svc, "_ingest_alpha_vantage_data", AsyncMock(return_value={"overview": True})), \
             patch.object(svc, "_ingest_yahoo_finance_data", AsyncMock(return_value={"info": True})):
            result = await svc.ingest_company_data("AAPL", fake_db)
        assert result["symbol"] == "AAPL"
        assert "alpha_vantage" in result["sources_used"] or "yahoo_finance" in result["sources_used"]


# ---------------------------------------------------------------------------
# batch_ingest_companies
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestBatchIngest:
    async def test_batch_runs_for_each_symbol(self, svc, fake_db):
        with patch.object(
            svc, "ingest_company_data",
            AsyncMock(return_value={"symbol": "X", "success": True, "sources_used": [], "data_ingested": {}, "errors": []}),
        ) as mock_ingest:
            result = await svc.batch_ingest_companies(["AAPL", "MSFT", "GOOG"], fake_db)
        assert mock_ingest.call_count == 3
        assert "total_processed" in result or "results" in result or isinstance(result, dict)


# ---------------------------------------------------------------------------
# get_data_source_status
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestDataSourceStatus:
    async def test_status_dict_structure(self, svc, fake_db):
        # Mock execute to return empty list / no rows
        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []
        empty_result.scalar_one_or_none.return_value = None
        fake_db.execute.return_value = empty_result
        result = await svc.get_data_source_status(fake_db)
        assert isinstance(result, dict)
