"""Regression checks motivated only by the HW7 tuning failures."""
from lostlink.matching import rank_alias


def test_unknown_item_type_does_not_turn_metadata_into_a_match():
    found = {"report_id": "F", "category": "bottle", "color": "blue",
             "location": "Stata", "date": "2026-10-20", "description": "blue bottle"}
    lost = {"category": "ring", "color": "blue", "location": "Stata",
            "date": "2026-10-20", "description": "titanium ring"}
    assert rank_alias(lost, [found]) == []
    assert rank_alias({"description": "bookmark"}, [found]) == []


def test_type_can_still_come_from_the_description():
    found = {"report_id": "F", "category": "bottle", "color": "blue",
             "location": "Stata", "date": "2026-10-20", "description": "blue bottle"}
    lost = {"category": None, "color": "navy", "location": "building 32",
            "date": "2026-10-20", "description": "navy flask"}
    assert rank_alias(lost, [found])[0]["report_id"] == "F"
