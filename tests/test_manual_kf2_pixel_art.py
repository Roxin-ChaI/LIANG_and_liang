from __future__ import annotations

from tools.manual_kf2_pixel_art import DROP_COLUMNS, DROP_ROWS, approved_kf1, assess, construct, resolve_review


def test_kf2_keeps_kf1_head_lineage_except_declared_brow_edits() -> None:
    image, recipe = construct()
    original = approved_kf1()
    cols = [x for x in range(61,115) if x not in DROP_COLUMNS]
    rows = [y for y in range(4,68) if y not in DROP_ROWS]
    brows = {tuple(xy) for xy in recipe["head"]["browPixels"]}
    for y,sy in enumerate(rows,4):
        for x,sx in enumerate(cols,62):
            if (x,y) not in brows:
                assert image.getpixel((x,y)) == original.getpixel((sx,sy))
    assert brows  # A declared intermediate expression change must actually occur.


def test_kf2_both_motion_budgets_and_render_integrity() -> None:
    image, _ = construct()
    report = assess(image)
    assert report["technicalPass"],report["checks"]
    assert report["pairs"]["KF1_KF2"]["headSizeDelta"] == [-2,-5]
    assert report["pairs"]["KF2_F0"]["headSizeDelta"] == [-2,-4]
    assert image.crop((0,192,192,208)).tobytes() == approved_kf1().crop((0,192,192,208)).tobytes()


def test_numeric_pass_cannot_waive_failed_suit_or_face() -> None:
    report = assess(construct()[0])
    checks = dict.fromkeys(("head","face","arms","suit","pose","alpha"),"PASS")
    review = {"reviewer":"independent","candidateRgbaSha256":report["candidateRgbaSha256"],
              "pairs":{name:{"verdict":"PASS","checks":checks.copy()} for name in ("KF1_KF2","KF2_F0")}}
    assert resolve_review(report,review)["fullChainAllowed"]
    review["pairs"]["KF2_F0"]["checks"]["face"] = "FAIL"
    failed = resolve_review(report,review)
    assert not failed["fullChainAllowed"] and failed["status"] == "MANUAL_BRIDGE_QA_FAIL"
