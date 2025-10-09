from datetime import datetime, timedelta, timezone
import math
import src.application.schemas as schemas


def days(dt: timedelta) -> float:
    """Convert a timedelta to fractional days."""
    return dt.total_seconds() / 86_400.0


class FakeTask:
    """Minimal stand-in for the ORM Task used by KanbanLeadTimeItem.from_task."""
    def __init__(self, issue_number, state, created_at, closed_at=None, column_name=None, title=None):
        self.issue_number = issue_number
        self.state = state
        self.created_at = created_at
        self.closed_at = closed_at
        self.column_name = column_name
        self.title = title


class FakePR:
    """Minimal stand-in for the ORM PullRequest used by PRLeadTimeItem.from_pr."""
    def __init__(self, pr_number, created_at, merged_at=None, closed_at=None, title=None):
        self.pr_number = pr_number
        self.created_at = created_at
        self.merged_at = merged_at
        self.closed_at = closed_at
        self.title = title


# ================================
# KanbanLeadTimeItem.from_task()
# ================================

def test_kanban_closed_issue_sets_lead_time_only():
    """Closed issue → lead_time = closed_at - created_at; age is None."""
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t1 = datetime(2025, 1, 4, tzinfo=timezone.utc)
    task = FakeTask(issue_number=10, state="closed", created_at=t0, closed_at=t1, column_name="Done")

    item = schemas.KanbanLeadTimeItem.from_task(task)

    assert item.issue_number == 10
    assert item.state == "closed"
    assert item.created_at == t0 and item.closed_at == t1
    assert math.isclose(item.lead_time, days(t1 - t0), rel_tol=1e-9)
    assert item.age is None
    assert item.column_name == "Done"


def test_kanban_open_issue_with_age_flag_true_computes_age(monkeypatch):
    """Open issue + include_age_for_open=True → age = now - created_at; lead_time is None."""
    fixed_now = datetime(2025, 2, 1, tzinfo=timezone.utc)

    class _DT(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(schemas, "datetime", _DT)

    created = datetime(2025, 1, 20, tzinfo=timezone.utc)
    task = FakeTask(issue_number=11, state="open", created_at=created, closed_at=None, column_name="Doing")

    item = schemas.KanbanLeadTimeItem.from_task(task)

    assert item.lead_time is None
    assert math.isclose(item.age, days(fixed_now - created), rel_tol=1e-9)
    assert item.column_name == "Doing"


def test_kanban_open_issue_with_age_flag_false_has_no_age(monkeypatch):
    """Open issue + include_age_for_open=False → age is None; lead_time is None."""
    class _DT(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2025, 2, 1, tzinfo=timezone.utc)

    monkeypatch.setattr(schemas, "datetime", _DT)

    task = FakeTask(
        issue_number=12,
        state="open",
        created_at=datetime(2025, 1, 20, tzinfo=timezone.utc)
    )

    item = schemas.KanbanLeadTimeItem.from_task(task, include_age_for_open=False)
    assert item.lead_time is None
    assert item.age is None


def test_kanban_closed_issue_zero_duration_lead_time_is_zero():
    """Closed immediately after creation → lead_time should be exactly 0.0 days."""
    from datetime import datetime, timezone
    from src.application import schemas

    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    task = FakeTask(issue_number=14, state="closed", created_at=t0, closed_at=t0)

    item = schemas.KanbanLeadTimeItem.from_task(task)
    assert item.lead_time == 0.0
    assert item.age is None


# ===========================
# PRLeadTimeItem.from_pr()
# ===========================

def test_pr_closed_uses_closed_at_for_lead_time():
    """Closed PR → lead_time = closed_at - created_at; age is None."""
    t0 = datetime(2025, 3, 1, tzinfo=timezone.utc)
    t1 = datetime(2025, 3, 5, tzinfo=timezone.utc)
    pr = FakePR(pr_number=201, created_at=t0, merged_at=None, closed_at=t1)

    item = schemas.PRLeadTimeItem.from_pr(pr)

    assert item.pr_number == 201
    assert item.created_at == t0 and item.closed_at == t1 and item.merged_at is None
    assert math.isclose(item.lead_time, days(t1 - t0), rel_tol=1e-9)
    assert item.age is None


def test_pr_merged_without_closed_uses_merged_at_for_lead_time():
    """Merged (no closed_at) → lead_time = merged_at - created_at; age is None."""
    t0 = datetime(2025, 3, 1, tzinfo=timezone.utc)
    tm = datetime(2025, 3, 4, tzinfo=timezone.utc)
    pr = FakePR(pr_number=202, created_at=t0, merged_at=tm, closed_at=None)

    item = schemas.PRLeadTimeItem.from_pr(pr)

    assert item.closed_at is None
    assert math.isclose(item.lead_time, days(tm - t0), rel_tol=1e-9)
    assert item.age is None


def test_pr_open_with_age_flag_true_computes_age(monkeypatch):
    """Open PR + include_age_for_open=True → age = now - created_at; lead_time is None."""
    fixed_now = datetime(2025, 3, 10, tzinfo=timezone.utc)

    class _DT(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(schemas, "datetime", _DT)

    t0 = datetime(2025, 3, 1, tzinfo=timezone.utc)
    pr = FakePR(pr_number=203, created_at=t0, merged_at=None, closed_at=None)

    item = schemas.PRLeadTimeItem.from_pr(pr)

    assert item.lead_time is None
    assert math.isclose(item.age, days(fixed_now - t0), rel_tol=1e-9)


def test_pr_open_with_age_flag_false_has_no_age(monkeypatch):
    """Open PR + include_age_for_open=False → age is None; lead_time is None."""
    class _DT(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2025, 3, 10, tzinfo=timezone.utc)

    monkeypatch.setattr(schemas, "datetime", _DT)

    t0 = datetime(2025, 3, 1, tzinfo=timezone.utc)
    pr = FakePR(pr_number=204, created_at=t0, merged_at=None, closed_at=None)

    item = schemas.PRLeadTimeItem.from_pr(pr, include_age_for_open=False)

    assert item.lead_time is None
    assert item.age is None

def test_pr_with_both_closed_and_merged_prefers_closed_value():
    """When both merged_at and closed_at exist, closed_at must win (lead_time uses closed_at)."""
    from datetime import datetime, timezone
    import math
    from src.application import schemas

    t0 = datetime(2025, 3, 1, tzinfo=timezone.utc)
    tm = datetime(2025, 3, 3, tzinfo=timezone.utc)
    tc = datetime(2025, 3, 4, tzinfo=timezone.utc)

    pr = FakePR(pr_number=205, created_at=t0, merged_at=tm, closed_at=tc)
    item = schemas.PRLeadTimeItem.from_pr(pr)

    assert item.merged_at == tm and item.closed_at == tc
    assert math.isclose(item.lead_time, days(tc - t0), rel_tol=1e-9)
