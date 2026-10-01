"""Human motion approval must not silently approve production pixels."""
import json

from tools.preview_gu_side_shuffle import BASE, SOURCE, digest


def test_motion_approval_is_bound_to_reviewed_source_and_scope():
    approval = json.loads((BASE / 'motion-approval.json').read_text())
    review = json.loads((BASE / 'review.json').read_text())
    assert approval['sourceSha256'] == digest(SOURCE) == review['sha256']
    assert approval['userStatement'] == '动作通过'
    assert approval['motionApproved'] and review['fourKeyposeMotionApproved']
    assert approval['frameOrder'] == [1, 2, 3, 4]
    assert (BASE / approval['reviewedPreview']).is_file()
    assert not approval['productionArtApproved']
    assert not approval['exactIdleAppearanceApproved']
    assert not approval['runtimeReady'] and not review['runtimeReady']
    assert not review['hardAlphaPass'] and not review['nativeSizePass']
