from __future__ import annotations

from tools.f0_morph_bridge import sources
from tools.manual_kf1_pixel_art import DROP_COLUMNS, DROP_ROWS, assess, construct, resolve_review


def test_kf1_keeps_original_face_pixel_sources() -> None:
    image, _ = construct()
    original = sources()["KB2"]
    cols = [x for x in range(60,116) if x not in DROP_COLUMNS]
    rows = [y for y in range(4,72) if y not in DROP_ROWS]
    # Every retained hair, face and glasses pixel must match its recorded
    # source, including original alpha. New Feng eyes cannot enter KF1.
    for y,sy in enumerate(rows,4):
        for x,sx in enumerate(cols,61):
            assert image.getpixel((x,y)) == original.getpixel((sx,sy))


def test_kf1_motion_and_render_integrity() -> None:
    image, _ = construct()
    report = assess(image)
    assert report["technicalPass"], report["checks"]
    assert report["delta"]["headSizeDelta"] == [-2,-4]
    assert report["delta"]["handCenterDelta"] == {"left":[-5,-2],"right":[5,-3]}
    assert not report["KF2Allowed"] and not report["F0ArtApproved"]
    assert image.crop((0,164,192,208)).tobytes() == sources()["KB2"].crop((0,164,192,208)).tobytes()


def test_kf2_requires_fresh_independent_visual_pass() -> None:
    report = assess(construct()[0])
    review = {"reviewer":"independent","verdict":"PASS",
              "candidateRgbaSha256":report["candidateRgbaSha256"],
              "checks":dict.fromkeys(("face","head","arms","suit","legs","alpha"),"PASS")}
    assert resolve_review(report,review)["KF2Allowed"]
    for bad in ({}, {**review,"candidateRgbaSha256":"stale"},
                {**review,"checks":{**review["checks"],"arms":"FAIL"}}):
        assert not resolve_review(report,bad)["KF2Allowed"]
