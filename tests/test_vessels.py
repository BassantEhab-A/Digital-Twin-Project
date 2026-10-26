import numpy as np
import pytest

from src.core.medical_volume import MedicalVolume
from src.core.resection import PlaneCut, ResectionEngine, VesselTree

SHAPE = (64, 64, 64)            # z, y, x ; isotropic 1 mm
SP = (1.0, 1.0, 1.0)


def _vol(mask):
    return MedicalVolume(mask.astype(np.uint8), SP, (0.0, 0.0, 0.0))


def _tube(p0, p1, radius):
    """Voxels within `radius` of the segment p0-p1 (points given as x, y, z)."""
    z, y, x = np.indices(SHAPE)
    pts = np.stack([x, y, z], axis=-1).astype(float)
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    t = np.clip(((pts - p0) @ d) / (d @ d), 0, 1)
    return np.linalg.norm(pts - (p0 + t[..., None] * d), axis=-1) <= radius


@pytest.fixture(scope="module")
def anatomy():
    z, y, x = np.indices(SHAPE)
    liver = ((x - 32) ** 2 + (y - 32) ** 2 + (z - 32) ** 2) <= 32 ** 2

    # Portal tree in the plane y = 15: trunk along z, then two branches.
    portal = (_tube((30, 15, 8), (30, 15, 25), 2) | _tube((30, 15, 25), (15, 15, 50), 2)
              | _tube((30, 15, 25), (45, 15, 50), 2))
    portal_root = _tube((30, 15, 6), (30, 15, 12), 3)
    # Hepatic tree in the plane y = 45: trunk toward the IVC, then two branches.
    hepatic = (_tube((30, 45, 52), (30, 45, 35), 2) | _tube((30, 45, 35), (15, 45, 12), 2)
               | _tube((30, 45, 35), (45, 45, 12), 2))
    ivc = _tube((30, 53, 5), (30, 53, 58), 3)

    vessels = (portal | hepatic) & liver
    tree = VesselTree.build(_vol(vessels), portal=_vol(portal_root), ivc=_vol(ivc))
    return dict(liver=_vol(liver), tree=tree, portal=portal, hepatic=hepatic)


def test_trees_are_labelled_by_root(anatomy):
    tree = anatomy["tree"]
    x, y = tree._zyx[:, 2], tree._zyx[:, 1]
    portal_side = y < 30
    assert (tree.tree_label[portal_side] == 1).mean() > 0.95
    assert (tree.tree_label[~portal_side] == 2).mean() > 0.95
    assert tree.branch_count >= 3


def test_intact_liver_loses_nothing(anatomy):
    liver = anatomy["liver"]
    removed = np.zeros(liver.shape, bool)
    impact = anatomy["tree"].impact(liver, removed, liver.voxel_data > 0)
    assert impact.devascularized_ml == 0 and not impact.branches


def test_cut_through_one_portal_branch(anatomy):
    liver = anatomy["liver"]
    cut = PlaneCut([21, 0, 0], [1, 0, 0])            # remove x < 21: crosses the left portal branch
    removed = cut.removed_mask(liver)
    impact = anatomy["tree"].impact(liver, removed, (liver.voxel_data > 0) & ~removed)
    assert impact.severed_portal >= 1
    assert impact.ischemic_ml > 0
    assert impact.ischemic_ml < 0.15 * liver.volume_ml(liver.voxel_data > 0)   # only a local effect
    assert impact.severed_vessel_mask.any()


def test_removing_the_portal_root_devascularizes_the_whole_portal_territory(anatomy):
    liver = anatomy["liver"]
    removed = PlaneCut([0, 0, 20], [0, 0, 1]).removed_mask(liver)   # remove z < 20: trunk base + root gone
    impact = anatomy["tree"].impact(liver, removed, (liver.voxel_data > 0) & ~removed)
    assert any(a.status == "downstream" and a.tree == "portal" for a in impact.branches)
    assert impact.ischemic_ml > 3 * impact.congested_ml


def test_removing_the_ivc_side_congests(anatomy):
    liver = anatomy["liver"]
    removed = PlaneCut([0, 40, 0], [0, -1, 0]).removed_mask(liver)  # remove y > 40: hepatic trunk gone
    impact = anatomy["tree"].impact(liver, removed, (liver.voxel_data > 0) & ~removed)
    assert impact.congested_ml > 0 and impact.ischemic_ml == 0


def test_engine_reports_effective_flr(anatomy):
    liver = anatomy["liver"]
    cut = PlaneCut([0, 0, 20], [0, 0, 1])
    plain = ResectionEngine.simulate(liver, cut)
    with_vessels = ResectionEngine.simulate(liver, cut, vessel_tree=anatomy["tree"])
    assert plain.effective_flr_percentage is None
    assert with_vessels.vascular is not None
    assert with_vessels.effective_flr_percentage < with_vessels.flr_percentage


def test_missing_roots_are_reported():
    z, y, x = np.indices(SHAPE)
    tree = VesselTree.build(_vol(_tube((10, 10, 10), (10, 10, 50), 2)))
    assert tree.warnings and (tree.tree_label == 0).all()
