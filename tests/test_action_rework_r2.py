import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

from tools import rework_action_candidates as art


def test_sources_and_runtime_selection_are_untouched():
    report=json.loads((art.OUT/"report.json").read_text())
    assert report["candidateOnly"] and report["sourceAndSelectionUnchanged"]
    for path,sha in report["inputs"].items():
        assert hashlib.sha256((art.ROOT/path).read_bytes()).hexdigest()==sha


def test_edge_repairs_only_clear_pixels_and_preserve_shirt_buckle():
    original=Image.open(art.ROOT/"assets/builds/feng/spritesheet.webp").convert("RGBA")
    selected=Image.open(art.SOURCE/"feng.webp").convert("RGBA")
    for name,row,count in [("feng-waving-edge",3,4),("feng-review-edge",8,6),("feng-look-edge",9,16)]:
        for n in range(count):
            a=np.array(art.frame(selected if count==16 else original,row+n//8,n%8))
            b=np.array(Image.open(art.OUT/name/f"{n+1:02d}.png").convert("RGBA"))
            changed=np.any(a!=b,axis=2)
            assert not b[changed].any()
            assert np.array_equal(a[64:119,80:110],b[64:119,80:110])
            assert np.array_equal(a[112:124,83:108],b[112:124,83:108])
            assert np.count_nonzero(b[:,:,3])>.9*np.count_nonzero(a[:,:,3])


def test_failed_only_four_keyposes_endpoints_exact_and_legs_fixed():
    atlas=Image.open(art.SOURCE/"feng.webp").convert("RGBA")
    idle=np.array(art.frame(atlas,0,0))
    folder=art.OUT/"feng-failed-keyposes"
    images=[np.array(Image.open(folder/f"{i:02d}.png").convert("RGBA")) for i in range(1,5)]
    assert np.array_equal(images[0],idle) and np.array_equal(images[3],idle)
    for image in images:
        assert image.shape==(208,192,4)
        assert np.array_equal(image[116:],idle[116:])
    donor=np.array(art.frame(atlas,8,2))
    assert np.array_equal(images[1][:71],donor[:71])
    # Blink edit stays inside the face, never at the head outline.
    changed=np.any(images[1][:71]!=images[2][:71],axis=2)
    assert not changed[:35].any() and not changed[47:].any()
    assert not changed[:,:72].any() and not changed[:,111:].any()
    assert not np.array_equal(images[1],idle)
    assert not np.array_equal(images[1],images[2])
    assert not (folder/"05.png").exists()


def test_fringe_algorithm_does_not_remove_enclosed_highlight():
    image=Image.new("RGBA",(192,208))
    draw=ImageDraw.Draw(image)
    draw.rectangle((20,20,40,40),fill=(20,30,70,255))
    draw.point((30,30),fill=(0,0,0,0))
    draw.point((31,30),fill="white")
    draw.point((19,25),fill="white")
    result,_=art.clean_edge(image)
    assert result.getpixel((31,30))==(255,255,255,255)
    assert result.getpixel((19,25))==(0,0,0,0)


def test_failed_drag_attempt_quarantined_and_not_promoted():
    report=json.loads((art.OUT/"report.json").read_text())
    for entry in report["drag"]:
        assert entry["status"]=="SELF_CHECK_FAIL_DO_NOT_USE"
        assert entry["nextGate"]=="MANUAL_LEG_KEYPOSE_REVIEW_REQUIRED"
        assert not (art.OUT/f"{entry['form']}-drag-right").exists()


def test_all_candidate_gifs_have_review_frames():
    for name,count in [("feng-waving-edge",4),("feng-review-edge",6),("feng-look-edge",16),("feng-failed-keyposes",4)]:
        with Image.open(art.OUT/name/"preview.gif") as image:
            assert image.n_frames==count


def test_user_verdict_overrides_structural_checks_and_locks_art():
    review=json.loads((art.OUT/"review-status.json").read_text())
    assert review["generatorLocked"] and not review["runtimePromoted"]
    for name,item in review["items"].items():
        strip=art.OUT/name/f"{name}.png"
        assert hashlib.sha256(strip.read_bytes()).hexdigest()==item["stripSha256"]
    for name in ["feng-look-edge","feng-failed-keyposes"]:
        assert review["items"][name]["status"]=="USER_REJECTED"
    for name in ["feng-waving-edge","feng-review-edge"]:
        assert review["items"][name]["status"]=="USER_APPROVED"
