"""Derive a leftward sway from approved right pixels, without mirroring identity."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.prepare_gu_drag_suspended import OUT as RIGHT_ROOT, sha
from tools.build_gu_drag_suspended import R2 as RIGHT, row_offsets, DURATIONS

OUT = ROOT / "assets/rework/v0.1.0/gu-drag-left-suspended-2026-10-22"


def verify_right_source(folder=RIGHT):
    record = json.loads((folder / "review-status.json").read_text())
    if (record.get("status") != "GU_DRAG_RIGHT_ART_APPROVED"
            or record.get("userApproval") != "APPROVED"
            or not record.get("generatorLocked")):
        raise ValueError("Right source is not approved and frozen")
    required = {f"right-{i:02d}.png" for i in range(1,9)} | {"gu-running-right.png"}
    if not required <= record.get("sha256", {}).keys():
        raise ValueError("Right source freeze is incomplete")
    for name, digest in record["sha256"].items():
        if Path(name).name != name:
            raise ValueError("Invalid source filename")
        if sha(folder / name) != digest:
            raise ValueError(f"Frozen right source changed: {name}")
    return record


def assert_unapproved(folder=OUT):
    status = folder / "review-status.json"
    if status.exists() and json.loads(status.read_text()).get("generatorLocked"):
        raise RuntimeError("Approved Gu left drag is frozen; create a new revision")


def derive_left(right, index):
    if not 0 <= index < 8:
        raise ValueError("Frame index must be 0..7")
    if right.mode != "RGBA" or right.size != (192,208):
        raise ValueError("Expected 192x208 RGBA source")
    source = np.array(right)
    if set(np.unique(source[:,:,3])) - {0,255} or source[source[:,:,3]==0,:3].any():
        raise ValueError("Source must have binary alpha and zero hidden RGB")
    target = np.zeros_like(source)
    for y, delta in enumerate(-2 * row_offsets(index)):
        xs = np.flatnonzero(source[y,:,3])
        if len(xs) and (xs[0]+delta < 0 or xs[-1]+delta >=192):
            raise ValueError("Left displacement would clip source pixels")
        # Bijective translation: not a horizontal flip, warp/resample or x-split.
        target[y,xs+delta] = source[y,xs]
    return Image.fromarray(target)
