import pytest
from fastapi import HTTPException

from app.dependencies import get_florist
from app.models.florist import Florist


def test_get_florist_returns_requested_florist(db_session):
    florist = Florist(name="Test Florist")
    db_session.add(florist)
    db_session.flush()

    result = get_florist(florist.id, db_session)

    assert result is florist


def test_get_florist_raises_404_for_unknown_id(db_session):
    with pytest.raises(HTTPException) as exc_info:
        get_florist(99999, db_session)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Florist not found."
