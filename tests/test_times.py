import datetime

from cbsent.ingest.times import boc_release_ts, fed_release_ts


def test_fed_statement_is_2pm_eastern():
    ts = fed_release_ts(datetime.date(2024, 1, 31))
    assert ts.hour == 14
    assert ts.utcoffset() == datetime.timedelta(hours=-5)


def test_fed_dst():
    ts = fed_release_ts(datetime.date(2024, 6, 12))
    assert ts.utcoffset() == datetime.timedelta(hours=-4)


def test_boc_before_change_is_10am():
    ts = boc_release_ts(datetime.date(2023, 1, 25))
    assert (ts.hour, ts.minute) == (10, 0)


def test_boc_on_change_date_is_945():
    ts = boc_release_ts(datetime.date(2024, 1, 24))
    assert (ts.hour, ts.minute) == (9, 45)


def test_boc_after_change_is_945():
    ts = boc_release_ts(datetime.date(2025, 3, 12))
    assert (ts.hour, ts.minute) == (9, 45)
