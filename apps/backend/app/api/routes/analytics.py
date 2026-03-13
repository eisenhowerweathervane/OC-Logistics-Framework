"""
Analytics and reporting routes.

Dashboard summary, revenue reports, fleet utilization, fuel cost summary.
"""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbDep
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_dashboard(db: DbDep, user: CurrentUser):
    """Get high-level dashboard metrics."""
    return await analytics_service.dashboard_summary(db, user.organization_id)


@router.get("/revenue")
async def get_revenue_report(
    db: DbDep,
    user: CurrentUser,
    period: str = "monthly",
    months_back: int = 6,
):
    """Revenue breakdown by period (weekly or monthly)."""
    if period not in ("weekly", "monthly"):
        period = "monthly"
    if months_back < 1:
        months_back = 1
    elif months_back > 24:
        months_back = 24
    return await analytics_service.revenue_by_period(db, user.organization_id, period, months_back)


@router.get("/fleet-utilization")
async def get_fleet_utilization(db: DbDep, user: CurrentUser):
    """Fleet utilization report: per-driver load count, revenue, miles, current status."""
    return await analytics_service.fleet_utilization(db, user.organization_id)


@router.get("/fuel-costs")
async def get_fuel_costs(
    db: DbDep,
    user: CurrentUser,
    months_back: int = 3,
):
    """Fuel cost summary: total gallons, total cost, avg price per gallon."""
    if months_back < 1:
        months_back = 1
    elif months_back > 24:
        months_back = 24
    return await analytics_service.fuel_cost_summary(db, user.organization_id, months_back)
