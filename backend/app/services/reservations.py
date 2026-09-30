from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
from sqlalchemy import text
from app.core.database_pool import db_pool

async def calculate_monthly_revenue(property_id: str, tenant_id: str, month: int, year: int, db_session) -> Decimal:
    """
    Calculates revenue for a specific month.

    Month boundaries are evaluated in the property's local timezone
    (properties.timezone), not UTC, so e.g. a check-in at 2024-02-29 23:30 UTC
    for a Europe/Paris property counts toward March.
    """

    start_date = datetime(year, month, 1)
    if month < 12:
        end_date = datetime(year, month + 1, 1)
    else:
        end_date = datetime(year + 1, 1, 1)

    query = text("""
        SELECT SUM(r.total_amount) as total
        FROM reservations r
        JOIN properties p ON p.id = r.property_id AND p.tenant_id = r.tenant_id
        WHERE r.property_id = :property_id
        AND r.tenant_id = :tenant_id
        AND (r.check_in_date AT TIME ZONE p.timezone) >= :start_date
        AND (r.check_in_date AT TIME ZONE p.timezone) < :end_date
    """)

    result = await db_session.execute(query, {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "start_date": start_date,
        "end_date": end_date
    })
    return result.scalar() or Decimal('0')

async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    await db_pool.initialize()

    async with db_pool.get_session() as session:
        query = text("""
            SELECT
                COALESCE(SUM(total_amount), 0.00) as total_revenue,
                COUNT(*) as reservation_count
            FROM reservations
            WHERE property_id = :property_id AND tenant_id = :tenant_id
        """)

        result = await session.execute(query, {
            "property_id": property_id,
            "tenant_id": tenant_id
        })
        row = result.one()

        return {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "total": str(row.total_revenue),
            "currency": "USD",
            "count": row.reservation_count
        }
