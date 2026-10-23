import json

import pytest
from PIL import Image

from tools.assemble_approved_actions import BASE, OUT, ROWS, approved_input, build, validate_atlas
from tools.build_animation_review import sha256


@pytest.mark.parametrize("form", ["gu", "feng"])
def test_only_approved_rows_changed_and_look_is_untouched(form):
    old = Image.open(BASE / f"{form}.webp").convert("RGBA")
    new = Image.open(OUT / f"{form}.webp").convert("RGBA")
    validate_atlas(new)
    changed = {spec[1] for spec in ROWS if spec[0] == form}
    for row in range(11):
        box = (0, row*208, 1536, (row+1)*208)
        if row not in changed:
            assert old.crop(box).tobytes() == new.crop(box).tobytes()
    assert 9 not in changed and 10 not in changed


@pytest.mark.parametrize("spec", ROWS)
def test_integrated_pixels_and_preview_timing_equal_approved_source(spec):
    source, record = approved_input(spec)
    im = Image.open(OUT / f'{record["form"]}.webp').convert("RGBA")
    y = record["row"]*208
    assert im.crop((0,y,source.width,y+208)).tobytes() == source.tobytes()
    gif = Image.open(OUT / f'{record["form"]}-{record["state"]}.gif')
    assert gif.n_frames == record["frames"]
    for i, duration in enumerate(record["durationsMs"]):
        gif.seek(i)
        assert gif.info["duration"] == duration


def test_manifest_and_output_freeze():
    report = json.loads((OUT / "manifest.json").read_text())
    assert report["spriteVersion"] == 2 and len(report["replacements"]) == 7
    for form, digest in report["outputSha256"].items():
        assert sha256(OUT/f"{form}.webp") == digest
    with pytest.raises(FileExistsError):
        build()


def test_unused_cell_validation_rejects_hidden_rgb():
    im = Image.open(OUT/"gu.webp").convert("RGBA")
    im.putpixel((7*192, 0), (1,0,0,0))
    with pytest.raises(ValueError, match="Hidden RGB"):
        validate_atlas(im)
