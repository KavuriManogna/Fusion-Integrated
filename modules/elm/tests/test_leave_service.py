from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import BadRequestError
from modules.elm.services.leave_service import calculate_leave_days

pytestmark = pytest.mark.django_db


def test_single_day_leave_counts_as_one_day():
    assert calculate_leave_days(
        date(2026, 10, 26), date(2026, 10, 26)
    ) == Decimal("1")


def test_multi_day_leave_counts_both_endpoints():
    assert calculate_leave_days(
        date(2026, 10, 26), date(2026, 10, 28)
    ) == Decimal("3")


def test_half_day_leave_counts_as_half_day():
    assert calculate_leave_days(
        date(2026, 10, 26), date(2026, 10, 26), is_half_day=True
    ) == Decimal("0.5")


def test_half_day_cannot_span_multiple_dates():
    with pytest.raises(BadRequestError):
        calculate_leave_days(
            date(2026, 10, 26), date(2026, 10, 27), is_half_day=True
        )


def test_end_date_before_start_date_is_rejected():
    with pytest.raises(BadRequestError):
        calculate_leave_days(date(2026, 10, 27), date(2026, 10, 26))


def test_started_leave_cannot_use_pre_start_cancellation(monkeypatch):
    from modules.elm.models import LeaveBalance, LeaveRequest, LeaveType
    from modules.elm.services.leave_service import cancel_approved_leave
    from core.api.exceptions import ConflictError

    today = date(2026, 10, 26)
    monkeypatch.setattr(
        "modules.elm.services.leave_service.timezone.localdate",
        lambda: today,
    )

    leave_type = LeaveType.objects.create(
        code="EL", name="Earned Leave", annual_quota=Decimal("30")
    )
    LeaveBalance.objects.create(
        employee_id=1001,
        leave_type=leave_type,
        year=2026,
        total_allocated=Decimal("30"),
        used_days=Decimal("2"),
    )
    leave_request = LeaveRequest.objects.create(
        employee_id=1001,
        leave_type=leave_type,
        start_date=today,
        end_date=date(2026, 10, 27),
        total_days=Decimal("2"),
        reason="Test leave",
        status="APPROVED",
    )

    with pytest.raises(ConflictError):
        cancel_approved_leave(
            employee_id=1001,
            request_id=leave_request.id,
        )
