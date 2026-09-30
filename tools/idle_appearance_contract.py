"""Read actual formal Idle pixels and enforce non-negotiable appearance gates.

Measures real alpha, palette and silhouette data. Region guides are explicitly
not anatomical measurements. No numerical result grants visual/art approval.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/rework/v0.1.0/idle-appearance-contract-2026-10-01"
CANVAS = (192, 208)
SOURCE_SHA = {
    "gu": "b6a3f086a9fdb9a4cb7c86d047991e1d3ff9a7a2ab740e4c2f705b42b9d08908",
    "feng": "d697e573268b66cb0f6a062480ec87c8c11712ca34b57f8c2fc0a97ed6e2164a",
}
PIXEL_SHA = {
    "gu": "e12f8f315e36d704a910406d1a8b9a0a9ea7779b3b61b3a92443cdf7b3be72fb",
    "feng": "17d6608ea37c508f465c4add9bd628c5ef09d9051a949d31ff9bd2ce6b0a1287",
}
HEAD_GUIDES = {"gu": [54, 4, 122, 84], "feng": [64, 4, 113, 58]}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical() -> dict[str, Image.Image]:
    refs = {}
    for form in ("gu", "feng"):
        file = ROOT / f"assets/builds/{form}/spritesheet.webp"
        if sha(file.read_bytes()) != SOURCE_SHA[form]:
            raise ValueError(f"formal {form} atlas changed; do not silently relax contract")
        with Image.open(file) as atlas:
            if atlas.size != (1536, 2288) or atlas.mode != "RGBA":
                raise ValueError("formal RGBA v2 atlas required")
            ref = atlas.crop((0, 0, *CANVAS))
        if sha(ref.tobytes()) != PIXEL_SHA[form]:
            raise ValueError("canonical Idle pixels changed")
        refs[form] = ref
    return refs


def palette(image: Image.Image) -> set[tuple[int, int, int]]:
    return {p[:3] for p in image.get_flattened_data() if p[3]}


def measure(image: Image.Image) -> dict:
    if image.mode != "RGBA":
        raise ValueError("RGBA required; conversion must not conceal wrong input mode")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    values = list(image.get_flattened_data())
    return {
        "canvas": list(image.size), "rgbaPixelSha256": sha(image.tobytes()),
        "actualAlphaBbox": list(bbox) if bbox else None,
        "actualHeight": bbox[3] - bbox[1] if bbox else 0,
        "actualBaseline": bbox[3] - 1 if bbox else None,
        "alphaValues": sorted(set(alpha.get_flattened_data())),
        "hiddenRgbPixels": sum(any(p[:3]) for p in values if p[3] == 0),
        "opaqueColorCount": len(palette(image)),
        "actualRowSpans": [
            [b[0], b[2]] if (b := alpha.crop((0, y, image.width, y + 1)).getbbox()) else None
            for y in range(image.height)
        ],
        "rowSpanMeaning": "actual opaque silhouette extents, not inferred shoulder/head segmentation",
    }


def mechanical_gate(image: Image.Image, refs: dict[str, Image.Image]) -> dict:
    if image.mode != "RGBA":
        return {"mechanicalPass": False, "checks": {"rgba": False}, "artApproved": False}
    info = measure(image)
    allowed = palette(refs["gu"]) | palette(refs["feng"])
    bbox = info["actualAlphaBbox"]
    checks = {
        "nativeSubjectCanvas": image.size == CANVAS,
        "nonempty": bbox is not None,
        "subjectHeightExactly200": info["actualHeight"] == 200,
        "subjectTopExactly4": bool(bbox and bbox[1] == 4),
        "baselineExactly203": info["actualBaseline"] == 203,
        "alphaOnly0And255": info["alphaValues"] == [0, 255],
        "noHiddenBackgroundRgb": info["hiddenRgbPixels"] == 0,
        "usesOnlyApprovedIdleSubjectColors": palette(image) <= allowed,
        "notIdlePadding": all(image.size != ref.size or image.tobytes() != ref.tobytes()
                              for ref in refs.values()),
        "notClipped": bool(bbox and bbox[0] > 0 and bbox[1] > 0
                           and bbox[2] < image.width and bbox[3] < image.height),
    }
    return {"mechanicalPass": all(checks.values()), "checks": checks,
            "artApproved": False, "styleIdentityAnatomyGate": "UNVERIFIED",
            "warning": "correct height/palette/alpha never proves correct face, anatomy or pixel-art style",
            "metrics": info}


def contract(refs: dict[str, Image.Image]) -> dict:
    return {
        "status": "HARD_REQUIREMENT_NO_WAIVER", "date": "2026-10-01",
        "userRequirement": "Idle 完全一致；比例、画风（像素风）及全部外观指标均以正式 Idle 为准。",
        "transitionFrameCount": 10, "idleFramesCounted": 0,
        "subjectCanvas": list(CANVAS), "registrationX": 96,
        "registrationMeaning": "existing logical anchor; never recenter using whole sprite bbox",
        "baselineY": 203, "characterHeight": 200, "characterTopY": 4,
        "canonical": {form: {"atlas": f"assets/builds/{form}/spritesheet.webp",
                             "atlasSha256": SOURCE_SHA[form], "row": 0, "frame": 0,
                             **measure(image)} for form, image in refs.items()},
        "historicalHeadGuides": {form: {"rectangle": guide,
                                         "isExactAnatomicalBbox": False,
                                         "note": "Gu includes lower neck/collar; Feng chin is hand-occluded. Never use constant supplied rectangles as evidence of actual candidate head size."}
                                  for form, guide in HEAD_GUIDES.items()},
        "requiredAppearance": [
            "Exact established Gu/Feng identity, hair, glasses, face rendering, costume and proportions",
            "Source Idle palette, outline thickness, pixel clusters and shading language; no generic replacement pixel style",
            "Source-registered eyes, head/neck and body; no anatomical part shifted/resized merely to fit bbox",
            "Readable connected shoulder/elbow/wrist/hand and hip/knee/ankle/shoe anatomy",
            "Measured and visually verified head/shoulder/torso/leg/stance trajectory between the actual two Idle forms",
            "10 genuine transition poses; external Gu/Feng Idle holds are not frames and may not pad the count",
        ],
        "intermediatePolicy": "Gu and Feng have different approved designs. Intermediate measurements must follow a documented trajectory between these two forms; they do not authorize a third character design. Numeric interpolation alone is not art approval.",
        "drawingPolicy": {
            "authoringScale": "native 192x208 subject; 224x240 oversized output uses normal anchor offset (16,18)",
            "referenceEnlargement": "integer nearest-neighbor only, native pixels remain authoritative",
            "globalOrPerFrameFittingToConcealMismatch": False,
            "genericChibiRestyling": False, "blurOrAntialiasing": False,
            "paletteQuantizationToInventNewPixelStyle": False,
            "effects": "secondary separate QA layer; may not contaminate subject measurements or conceal defects",
        },
        "gates": {
            "mechanical": "all exact canvas/height/baseline/alpha/palette checks must pass",
            "semantic": "actual candidate region annotations and visual review of face, hair, glasses, shoulders, suit, hands, legs and shoes required",
            "temporal": "all adjacent pairs and both external Idle handoffs must pass at native display scale",
            "artApproval": "explicit actual visual approval, never inherited from tests, prompt wording or supplied bbox values",
            "anyFailOrUnknown": "NOT_APPROVED; do not integrate or label complete",
        },
        "priorDrafts": "2026-10-01 generated candidate and old E1/E2/E3 are rejected art, not appearance references",
        "reverseDirection": "user-approved frozen 8-frame Feng->Gu; unchanged",
        "createdAnimationFrames": 0, "appIntegrated": False,
    }


def write() -> None:
    if OUT.exists():
        raise ValueError("refuse to overwrite fixed reference pack")
    refs = canonical()
    spec = contract(refs)
    OUT.mkdir()
    for form, image in refs.items():
        image.save(OUT / f"{form}-idle-native.png")
        image.resize((768, 832), Image.Resampling.NEAREST).save(OUT / f"{form}-idle-nearest4x.png")
    board = Image.new("RGBA", (384, 240), (35, 35, 39, 255))
    draw = ImageDraw.Draw(board)
    for col, form in enumerate(("gu", "feng")):
        draw.text((col * 192 + 4, 4), f"{form.upper()} FORMAL IDLE / 200px", fill="white")
        board.alpha_composite(refs[form], (col * 192, 24))
    board.resize((1536, 960), Image.Resampling.NEAREST).save(OUT / "formal-idle-reference-sheet.png")
    (OUT / "contract.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
    colors = {form: ["#%02x%02x%02x" % rgb for rgb in sorted(palette(im))] for form, im in refs.items()}
    (OUT / "source-palettes.json").write_text(json.dumps(colors, indent=2) + "\n")
    prior = ROOT / "assets/rework/v0.1.0/gu-to-feng-idle-redraw-2026-10-01/frames"
    rejected = {file.name: mechanical_gate(Image.open(file), refs) for file in sorted(prior.glob("*.png"))}
    if len(rejected) != 10 or any(item["mechanicalPass"] for item in rejected.values()):
        raise AssertionError("prior generation must not pass this native Idle contract")
    (OUT / "prior-candidate-rejection.json").write_text(json.dumps(rejected, indent=2) + "\n")
    print("HARD_IDLE_CONTRACT_LOCKED; prior candidate 10/10 REJECTED; new animation frames 0")


if __name__ == "__main__":
    write()
