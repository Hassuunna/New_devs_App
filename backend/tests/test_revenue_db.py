"""Integration test for calculate_total_revenue against a DB seeded from database/seed.sql.

Run with: REVENUE_TEST_DATABASE_URL=postgresql://user:pass@host:port/propertyflow pytest tests/test_revenue_db.py
"""
import asyncio
import os

import pytest

from app.config import settings
from app.core import database_pool
from app.services.reservations import calculate_total_revenue

DB_URL = os.getenv("REVENUE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB_URL, reason="REVENUE_TEST_DATABASE_URL not set")


def _run(coro_fn, monkeypatch, url):
    monkeypatch.setattr(settings, "database_url", url)
    monkeypatch.setattr(database_pool, "db_pool", database_pool.DatabasePool())

    async def wrapper():
        try:
            return await coro_fn()
        finally:
            await database_pool.db_pool.close()

    return asyncio.run(wrapper())


@pytest.mark.parametrize(
    "property_id,tenant_id,total,count",
    [
        ("prop-001", "tenant-a", "2250.000", 4),
        ("prop-001", "tenant-b", "0.00", 0),
        ("prop-002", "tenant-a", "4975.500", 4),
        ("prop-004", "tenant-b", "1776.500", 4),
        ("prop-004", "tenant-a", "0.00", 0),
        ("prop-005", "tenant-b", "3256.000", 3),
    ],
)
def test_total_revenue_from_db_is_tenant_scoped(monkeypatch, property_id, tenant_id, total, count):
    result = _run(lambda: calculate_total_revenue(property_id, tenant_id), monkeypatch, DB_URL)
    assert result == {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "total": total,
        "currency": "USD",
        "count": count,
    }


def test_db_failure_is_raised_not_mocked(monkeypatch):
    bad_url = "postgresql://postgres:wrong@127.0.0.1:1/propertyflow"
    with pytest.raises(Exception):
        _run(lambda: calculate_total_revenue("prop-001", "tenant-a"), monkeypatch, bad_url)
