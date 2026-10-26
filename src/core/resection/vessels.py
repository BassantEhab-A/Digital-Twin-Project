"""Vascular tree of the liver and the effect of a resection on it.

Pipeline
  1. skeletonize the vessel mask  -> centreline voxels (a voxel graph)
  2. split it into branches (segments between junctions), with radius
  3. label every centreline voxel PORTAL (inflow) or HEPATIC (outflow) by
     which root it is closest to along the vessels (graph Voronoi):
       portal roots  = centreline near the portal-vein mask
       hepatic roots = centreline near the IVC mask
  4. after a cut: centreline voxels inside the removed part are gone; a
     remaining voxel is still SUPPLIED only if it stays connected, through
     remaining voxels of its own tree, to a root of that tree
  5. territories: every remnant voxel belongs to its nearest centreline
     voxel of each tree. Remnant tissue owned by an unsupplied voxel has
     lost its portal inflow (ischemic) or venous outflow (congested).

Pure numpy/scipy/scikit-image, no GUI. Build once per case, reuse per cut.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize

from src.core.medical_volume import MedicalVolume
from src.core.resection.margin import crop_slices

PORTAL, HEPATIC = 1, 2
TREE_NAMES = {PORTAL: "portal", HEPATIC: "hepatic"}

# 13 "forward" offsets: each pair of 26-neighbours is visited once.
_OFFSETS = [o for o in itertools.product((-1, 0, 1), repeat=3) if o > (0, 0, 0)]


@dataclass(frozen=True)
class AffectedBranch:
    branch_id: int
    tree: str               # "portal" | "hepatic"
    status: str             # "severed" (crosses the cut) | "downstream" (cut off from its root)
    diameter_mm: float
    length_mm: float


@dataclass(frozen=True)
class VascularImpact:
    branches: tuple                      # AffectedBranch, largest first
    severed_portal: int
    severed_hepatic: int
    ischemic_mask: np.ndarray            # remnant that lost portal inflow
    congested_mask: np.ndarray           # remnant that lost venous outflow
    devascularized_mask: np.ndarray      # union of the two
    severed_vessel_mask: np.ndarray      # vessel voxels of affected branches
    ischemic_ml: float
    congested_ml: float
    devascularized_ml: float
    warnings: tuple = ()


class VesselTree:
    """Centreline graph of the hepatic vessels, built once per case."""

    # ------------------------------------------------------------------ build
    @classmethod
    def build(cls, vessels: MedicalVolume, portal: MedicalVolume | None = None,
              ivc: MedicalVolume | None = None, root_tolerance_mm: float = 2.0,
              max_root_distance_mm: float = 40.0) -> "VesselTree":
        mask = vessels.voxel_data > 0
        if not mask.any():
            raise ValueError("The vessel segmentation is empty.")

        tree = cls()
        tree._vessels = vessels
        spacing_zyx = np.asarray(vessels.spacing_zyx)

        box = crop_slices(mask, (1, 1, 1))
        sub = mask[box]
        skeleton = skeletonize(sub) > 0
        local = np.argwhere(skeleton)                       # (N, 3) z, y, x in the crop
        if len(local) == 0:
            raise ValueError("Could not extract a centreline from the vessel mask.")
        n = len(local)
        offset = np.array([s.start for s in box])
        tree._zyx = local + offset
        tree.points = vessels.voxel_to_world(tree._zyx[:, ::-1])          # (N, 3) mm
        radius_volume = ndi.distance_transform_edt(sub, sampling=tuple(spacing_zyx))
        tree.radius = radius_volume[tuple(local.T)]

        # --- voxel graph (26-connectivity, edge weight = distance in mm)
        index = np.full(sub.shape, -1, dtype=np.int64)
        index[tuple(local.T)] = np.arange(n)
        rows, cols, weights = [], [], []
        for off in _OFFSETS:
            neighbour = local + off
            inside = np.all((neighbour >= 0) & (neighbour < sub.shape), axis=1)
            target = np.full(n, -1, dtype=np.int64)
            target[inside] = index[tuple(neighbour[inside].T)]
            hit = target >= 0
            rows.append(np.nonzero(hit)[0])
            cols.append(target[hit])
            weights.append(np.full(int(hit.sum()), np.linalg.norm(np.asarray(off) * spacing_zyx)))
        rows, cols, weights = map(np.concatenate, (rows, cols, weights))
        forward = coo_matrix((weights, (rows, cols)), shape=(n, n)).tocsr()
        graph = (forward + forward.T).tocsr()
        tree._graph = graph

        tree._label_branches(sub.shape, local, graph, vessels.spacing)
        tree._label_trees(portal, ivc, root_tolerance_mm, max_root_distance_mm)
        return tree

    def _label_branches(self, crop_shape, local, graph, spacing_xyz) -> None:
        """Branch = run of centreline voxels between junctions (degree >= 3)."""
        degree = np.diff(graph.indptr)
        regular = degree < 3
        segment_volume = np.zeros(crop_shape, dtype=bool)
        segment_volume[tuple(local[regular].T)] = True
        labels, count = ndi.label(segment_volume, structure=np.ones((3, 3, 3)))
        self.branch_id = labels[tuple(local.T)].astype(np.int64) - 1   # -1 = junction voxel
        self.branch_count = count
        valid = self.branch_id >= 0
        sizes = np.bincount(self.branch_id[valid], minlength=count)
        radius_sum = np.bincount(self.branch_id[valid], weights=self.radius[valid], minlength=count)
        self.branch_diameter_mm = 2 * radius_sum / np.maximum(sizes, 1)
        self.branch_length_mm = sizes * float(np.mean(spacing_xyz))
        self._branch_size = sizes

    def _label_trees(self, portal, ivc, tolerance_mm, max_distance_mm) -> None:
        """Graph Voronoi: each centreline voxel joins the nearer root (portal or IVC)."""
        n = len(self.points)
        root_label = np.zeros(n, dtype=np.int8)
        self.warnings = []
        for tree_id, volume in ((HEPATIC, ivc), (PORTAL, portal)):     # portal wins ties
            roots = self._find_roots(volume, tolerance_mm, max_distance_mm)
            if len(roots) == 0:
                self.warnings.append(f"No {TREE_NAMES[tree_id]} root found near the vessels - "
                                     f"{TREE_NAMES[tree_id]} analysis skipped.")
            root_label[roots] = tree_id
        root_nodes = np.nonzero(root_label)[0]

        tree_label = np.zeros(n, dtype=np.int8)
        if len(root_nodes):
            dist, _, source = dijkstra(self._graph, directed=False, indices=root_nodes,
                                       min_only=True, return_predecessors=True)
            reached = np.isfinite(dist)
            tree_label[reached] = root_label[source[reached]]
        self.tree_label = tree_label
        self.is_root = root_label > 0

        # Only edges inside one tree count for supply connectivity.
        coo = self._graph.tocoo()
        same = (tree_label[coo.row] == tree_label[coo.col]) & (tree_label[coo.row] > 0)
        self._tree_graph = coo_matrix((coo.data[same], (coo.row[same], coo.col[same])),
                                      shape=self._graph.shape).tocsr()

    def _find_roots(self, volume, tolerance_mm, max_distance_mm) -> np.ndarray:
        if volume is None or not volume.voxel_data.any():
            return np.array([], dtype=np.int64)
        _, pts = volume.mask_world_points()
        pts = pts[:: max(1, len(pts) // 100_000)]
        distance, _ = cKDTree(pts).query(self.points)
        if distance.min() > max_distance_mm:
            return np.array([], dtype=np.int64)
        return np.nonzero(distance <= distance.min() + tolerance_mm)[0]

    # ------------------------------------------------------------ properties
    @property
    def tree_counts(self) -> dict:
        return {TREE_NAMES[t]: int((self.tree_label == t).sum()) for t in (PORTAL, HEPATIC)}

    # ---------------------------------------------------------------- impact
    def _supplied(self, removed_at_nodes: np.ndarray) -> np.ndarray:
        """Centreline voxels that are alive AND still connected to a root of their tree."""
        alive = ~removed_at_nodes
        supplied = np.zeros(len(self.points), dtype=bool)
        for tree_id in (PORTAL, HEPATIC):
            nodes = np.nonzero(alive & (self.tree_label == tree_id))[0]
            if len(nodes) == 0:
                continue
            sub = self._tree_graph[nodes][:, nodes]
            _, component = connected_components(sub, directed=False)
            rooted = np.unique(component[self.is_root[nodes]])
            supplied[nodes[np.isin(component, rooted)]] = True
        return supplied

    def impact(self, liver: MedicalVolume, removed: np.ndarray, retained: np.ndarray,
               min_diameter_mm: float = 2.0) -> VascularImpact:
        """What the resection does to the vessels and to the tissue they serve."""
        z, y, x = self._zyx.T
        gone = removed[z, y, x]
        supplied = self._supplied(gone)

        # --- affected branches
        valid = self.branch_id >= 0
        bid = self.branch_id[valid]
        removed_fraction = np.bincount(bid, weights=gone[valid], minlength=self.branch_count) \
            / np.maximum(self._branch_size, 1)
        supplied_fraction = np.bincount(bid, weights=supplied[valid], minlength=self.branch_count) \
            / np.maximum(self._branch_size, 1)
        portal_fraction = np.bincount(bid, weights=(self.tree_label[valid] == PORTAL),
                                      minlength=self.branch_count) / np.maximum(self._branch_size, 1)
        hepatic_fraction = np.bincount(bid, weights=(self.tree_label[valid] == HEPATIC),
                                       minlength=self.branch_count) / np.maximum(self._branch_size, 1)

        affected, flagged = [], np.zeros(self.branch_count, dtype=bool)
        for b in range(self.branch_count):
            if self.branch_diameter_mm[b] < min_diameter_mm or max(portal_fraction[b], hepatic_fraction[b]) < 0.5:
                continue
            if 0 < removed_fraction[b] < 1:
                status = "severed"
            elif removed_fraction[b] == 0 and supplied_fraction[b] < 0.5:
                status = "downstream"
            else:
                continue                                  # intact, or removed together with the specimen
            flagged[b] = True
            tree_name = TREE_NAMES[PORTAL if portal_fraction[b] >= hepatic_fraction[b] else HEPATIC]
            affected.append(AffectedBranch(b, tree_name, status, float(self.branch_diameter_mm[b]),
                                           float(self.branch_length_mm[b])))
        affected.sort(key=lambda a: -a.diameter_mm)

        # --- territories of the remnant
        zr, yr, xr = np.nonzero(retained)
        remnant_points = liver.voxel_to_world(np.stack([xr, yr, zr], axis=1))
        lost = {}
        for tree_id in (PORTAL, HEPATIC):
            nodes = np.nonzero(self.tree_label == tree_id)[0]
            mask = np.zeros(liver.shape, dtype=bool)
            if len(nodes):
                _, nearest = cKDTree(self.points[nodes]).query(remnant_points, workers=-1)
                unsupplied = ~supplied[nodes][nearest]
                mask[zr[unsupplied], yr[unsupplied], xr[unsupplied]] = True
            lost[tree_id] = mask
        ischemic, congested = lost[PORTAL], lost[HEPATIC]
        both = ischemic | congested

        # --- vessel voxels that belong to affected branches
        severed_vessels = np.zeros(liver.shape, dtype=bool)
        if flagged.any():
            vz, vy, vx = np.nonzero((self._vessels.voxel_data > 0) & ~removed)
            vessel_points = self._vessels.voxel_to_world(np.stack([vx, vy, vz], axis=1))
            _, nearest = cKDTree(self.points[valid]).query(vessel_points, workers=-1)
            owner_branch = bid[nearest]
            hit = flagged[owner_branch]
            severed_vessels[vz[hit], vy[hit], vx[hit]] = True

        return VascularImpact(
            branches=tuple(affected),
            severed_portal=sum(a.tree == "portal" and a.status == "severed" for a in affected),
            severed_hepatic=sum(a.tree == "hepatic" and a.status == "severed" for a in affected),
            ischemic_mask=ischemic, congested_mask=congested, devascularized_mask=both,
            severed_vessel_mask=severed_vessels,
            ischemic_ml=liver.volume_ml(ischemic), congested_ml=liver.volume_ml(congested),
            devascularized_ml=liver.volume_ml(both), warnings=tuple(self.warnings),
        )
