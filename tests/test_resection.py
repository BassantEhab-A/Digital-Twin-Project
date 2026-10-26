import numpy as np
import pytest

from src.core.medical_volume import MedicalVolume
from src.core.resection import (PlaneCut, ResectionEngine, SegmentCut, expand_mask_mm,
                                min_distance_mm, suggest_plane_cut, suggest_segment_cut)

SPACING = (1.0, 1.0, 2.0)   # x, y, z in mm  (anisotropic on purpose)


def _grid(shape=(40, 70, 70)):
    return np.indices(shape)  # z, y, x


def _vol(arr, spacing=SPACING):
    return MedicalVolume(arr.astype(np.uint8), spacing, (0.0, 0.0, 0.0))


def _ball(shape, center_xyz_mm, radius_mm, spacing=SPACING):
    z, y, x = _grid(shape)
    cx, cy, cz = center_xyz_mm
    d2 = ((x * spacing[0] - cx) ** 2 + (y * spacing[1] - cy) ** 2 + (z * spacing[2] - cz) ** 2)
    return d2 <= radius_mm ** 2


@pytest.fixture
def liver():
    return _vol(_ball((40, 70, 70), (35, 35, 40), 30))


def test_world_roundtrip_with_rotated_direction():
    direction = (0, -1, 0, 1, 0, 0, 0, 0, 1)
    vol = MedicalVolume(np.zeros((5, 6, 7), np.uint8), (0.7, 0.8, 2.5), (10, -20, 30), direction)
    ijk = np.array([[1, 2, 3], [6, 5, 4]], float)
    assert np.allclose(vol.world_to_voxel(vol.voxel_to_world(ijk)), ijk)


def test_volume_ml(liver):
    assert liver.volume_ml() == pytest.approx(np.count_nonzero(liver.voxel_data) * 2.0 / 1000)


def test_axis_aligned_axial_halves_the_liver(liver):
    result = ResectionEngine.simulate(liver, PlaneCut.axis_aligned(liver, "axial", 50))
    assert result.remnant_percentage == pytest.approx(50, abs=3)
    assert not (result.retained_mask & result.removed_mask).any()
    assert (result.retained_mask | result.removed_mask).sum() == np.count_nonzero(liver.voxel_data)


def test_normal_points_to_kept_side(liver):
    keep_high = PlaneCut.axis_aligned(liver, "axial", 30, keep_positive=True).removed_mask(liver)
    z = np.nonzero(keep_high)[0]
    zmax_removed = z.max()
    kept_z = np.nonzero(liver.voxel_data > 0)[0]
    assert zmax_removed < kept_z.max()           # the top (superior) part is kept


def test_coronal_and_sagittal_use_different_axes(liver):
    cor = PlaneCut.axis_aligned(liver, "coronal", 50)
    sag = PlaneCut.axis_aligned(liver, "sagittal", 50)
    assert np.allclose(cor.normal, [0, 1, 0]) and np.allclose(sag.normal, [1, 0, 0])


def test_collinear_points_rejected():
    with pytest.raises(ValueError):
        PlaneCut.from_points([0, 0, 0], [1, 1, 1], [2, 2, 2])


def test_expand_mask_matches_analytic_radius():
    shape = (60, 80, 80)
    tumor = _ball(shape, (40, 40, 60), 6)
    grown = expand_mask_mm(tumor, SPACING, 10)
    expected = _ball(shape, (40, 40, 60), 16)
    assert (grown ^ expected).sum() / expected.sum() < 0.05


def test_min_distance():
    a = np.zeros((10, 10, 10), bool); a[5, 5, 2] = True
    b = np.zeros((10, 10, 10), bool); b[5, 5, 8] = True
    assert min_distance_mm(a, b, (1, 1, 1)) == pytest.approx(6.0)
    assert min_distance_mm(a, np.zeros_like(b), (1, 1, 1)) is None


def test_cut_through_tumor_is_flagged(liver):
    tumor = _vol(_ball(liver.shape, (35, 35, 40), 5))
    result = ResectionEngine.simulate(liver, PlaneCut.axis_aligned(liver, "axial", 50),
                                      tumor=tumor, margin_mm=10)
    assert not result.tumor_covered and not result.margin_satisfied and result.warnings


def test_suggested_plane_covers_tumor_and_margin_and_beats_axis_aligned(liver):
    tumor = _vol(_ball(liver.shape, (55, 35, 40), 5))       # tumor near +X edge
    margin = 8
    required = expand_mask_mm(tumor.voxel_data, SPACING, margin) & (liver.voxel_data > 0)

    cut = suggest_plane_cut(liver, required)
    result = ResectionEngine.simulate(liver, cut, tumor=tumor, margin_mm=margin)
    assert result.tumor_covered and result.margin_satisfied
    assert result.margin_achieved_mm is not None and result.margin_achieved_mm >= margin - 1.0

    # Best axis-aligned alternative that also covers the zone.
    best_axis = 0.0
    for orientation in ("axial", "coronal", "sagittal"):
        for keep_positive in (True, False):
            for pct in range(0, 101, 2):
                r = ResectionEngine.simulate(liver, PlaneCut.axis_aligned(liver, orientation, pct, keep_positive),
                                             tumor=tumor, margin_mm=margin)
                if r.margin_satisfied:
                    best_axis = max(best_axis, r.remnant_percentage)
    assert result.remnant_percentage >= best_axis - 1.0


def test_flr_excludes_tumor(liver):
    tumor = _vol(_ball(liver.shape, (35, 35, 40), 8))
    # Remove nothing but a sliver far from the tumor.
    result = ResectionEngine.simulate(liver, PlaneCut.axis_aligned(liver, "axial", 0), tumor=tumor)
    assert result.flr_percentage == pytest.approx(100, abs=0.5)
    assert result.tumor_volume_ml > 0


def test_segment_cut_and_suggestion(liver):
    z, y, x = _grid(liver.shape)
    inside = liver.voxel_data > 0
    left = x * 1.0 >= 35
    segments = {
        "liver_segment_4": _vol(inside & ~left),
        "liver_segment_2": _vol(inside & left),
    }
    tumor_mask = _ball(liver.shape, (50, 35, 40), 4)
    required = expand_mask_mm(tumor_mask, SPACING, 3) & inside
    cut = suggest_segment_cut(segments, required)
    assert cut.keys == ["liver_segment_2"]
    result = ResectionEngine.simulate(liver, cut, tumor=_vol(tumor_mask), margin_mm=3)
    assert result.tumor_covered and result.margin_satisfied

    with pytest.raises(ValueError):
        SegmentCut(segments, ["liver_segment_9"])
    with pytest.raises(ValueError):
        SegmentCut(segments, [])
