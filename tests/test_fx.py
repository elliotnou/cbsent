import datetime
import lzma
import struct

from cbsent import fx


def _encode(records):
    """Build a .bi5 payload the way Dukascopy stores one hour of ticks."""
    raw = b"".join(
        struct.pack(">IIIff", ms, ask, bid, 1.0, 1.0) for ms, ask, bid in records
    )
    compressor = lzma.LZMACompressor(format=lzma.FORMAT_ALONE)
    return compressor.compress(raw) + compressor.flush()


def test_decode_returns_timestamps_and_mid_prices():
    hour = datetime.datetime(2025, 1, 29, 19, 0)
    payload = _encode([(0, 144000, 143800), (1500, 144200, 144000)])
    out = fx._decode_bi5(payload, hour)

    assert len(out) == 2
    assert out[0][0] == hour
    assert out[1][0] == hour + datetime.timedelta(milliseconds=1500)
    # Mid of 1.44000 ask and 1.43800 bid.
    assert abs(out[0][1] - 1.439) < 1e-9
    assert abs(out[1][1] - 1.4410) < 1e-9


def test_decode_empty_payload():
    assert fx._decode_bi5(b"", datetime.datetime(2025, 1, 1)) == []


def test_point_value_puts_usdcad_in_a_plausible_range():
    hour = datetime.datetime(2025, 1, 29, 19, 0)
    out = fx._decode_bi5(_encode([(0, 144000, 143800)]), hour)
    assert 1.0 < out[0][1] < 2.0
