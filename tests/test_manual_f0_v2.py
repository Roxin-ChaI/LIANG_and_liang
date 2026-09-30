from tools.f0_v2_spec import FACE_SOURCE, FACE_TARGET, HAND_LOCKS, FEET_LOCK, sources
from tools.manual_f0_v2 import construct, assess


def test_f0_v2_retains_expression_hands_and_feet_bytes():
    original = sources()["KF2"]
    candidate, _ = construct()
    assert original.crop(FACE_SOURCE).tobytes() == candidate.crop(FACE_TARGET).tobytes()
    for box in [*HAND_LOCKS, FEET_LOCK]:
        assert original.crop(box).tobytes() == candidate.crop(box).tobytes()


def test_f0_v2_native_geometry_and_no_pixel_artifacts():
    candidate, recipe = construct()
    report = assess(candidate)
    assert report["technicalPass"], report["checks"]
    assert report["delta"]["headSizeDelta"] == [-2,-4]
    assert report["delta"]["headCenterDelta"] == [0,-2]
    assert report["delta"]["bodyWidthDelta"] == 1
    assert recipe["retiredF0PixelsUsed"] == recipe["BPixelDonorsUsed"] == 0
    assert not report["morphApproved"] and not report["entryAuditAllowed"]


def test_expression_edit_or_foot_movement_is_rejected():
    candidate, _ = construct()
    candidate.putpixel((80,38),(0,0,0,255))
    report = assess(candidate)
    assert not report["technicalPass"]
    assert not report["checks"]["expressionByteIdentical"]
    candidate, _ = construct()
    candidate.putpixel((96,203),(1,1,1,255))
    assert not assess(candidate)["checks"]["handsFeetByteIdentical"]


def test_trouser_stance_does_not_widen_more_than_three_pixels_per_side():
    original = sources()["KF2"]
    candidate, _ = construct()
    for y in range(155,192):
        for x0,x1 in ((70,96),(99,123)):
            a = original.getchannel("A").crop((x0,y,x1,y+1)).getbbox()
            b = candidate.getchannel("A").crop((x0,y,x1,y+1)).getbbox()
            assert a and b
            assert abs(a[0]-b[0]) <= 3 and abs(a[2]-b[2]) <= 3
