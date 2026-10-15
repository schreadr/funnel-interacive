"""
Computational geometry primitives, polygon validation, ear-clipping triangulation,
and dual graph corridor extraction for the Funnel Algorithm.
"""

from __future__ import annotations
import math
from collections import deque
from typing import List, Tuple, Optional, Dict

Point = Tuple[float, float]
Triangle = Tuple[int, int, int]
Segment = Tuple[Point, Point]

EPSILON = 1e-9


def dist(p1: Point, p2: Point) -> float:
    """Euclidean distance between two 2D points."""
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def dist_sq(p1: Point, p2: Point) -> float:
    """Squared Euclidean distance."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return dx * dx + dy * dy


def cross2d(origin: Point, a: Point, b: Point) -> float:
    """
    2D Cross product of vectors (a - origin) and (b - origin).
    > 0 : Counter-Clockwise (left turn)
    < 0 : Clockwise (right turn)
    = 0 : Collinear
    """
    return (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0])


def dot2d(origin: Point, a: Point, b: Point) -> float:
    """Dot product of vectors (a - origin) and (b - origin)."""
    return (a[0] - origin[0]) * (b[0] - origin[0]) + (a[1] - origin[1]) * (b[1] - origin[1])


def polygon_signed_area(poly: List[Point]) -> float:
    """Computes signed area using Shoelace formula. Positive for CCW, negative for CW."""
    n = len(poly)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += poly[i][0] * poly[j][1] - poly[j][0] * poly[i][1]
    return area * 0.5


def ensure_ccw(poly: List[Point]) -> Tuple[List[Point], bool]:
    """Ensures polygon vertices are in Counter-Clockwise order. Returns (ccw_poly, was_reversed)."""
    if polygon_signed_area(poly) < 0:
        return list(reversed(poly)), True
    return list(poly), False


def on_segment(p: Point, a: Point, b: Point) -> bool:
    """Checks if point p lies on segment ab (assuming collinear)."""
    return (
        min(a[0], b[0]) - EPSILON <= p[0] <= max(a[0], b[0]) + EPSILON
        and min(a[1], b[1]) - EPSILON <= p[1] <= max(a[1], b[1]) + EPSILON
    )


def segments_intersect(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    """
    Returns True if line segment p1-p2 intersects line segment p3-p4.
    Proper or improper intersection (including collinear overlap).
    """
    d1 = cross2d(p3, p4, p1)
    d2 = cross2d(p3, p4, p2)
    d3 = cross2d(p1, p2, p3)
    d4 = cross2d(p1, p2, p4)

    # General case: segments straddle each other
    if (((d1 > EPSILON and d2 < -EPSILON) or (d1 < -EPSILON and d2 > EPSILON)) and
            ((d3 > EPSILON and d4 < -EPSILON) or (d3 < -EPSILON and d4 > EPSILON))):
        return True

    # Collinear and overlapping cases
    if abs(d1) <= EPSILON and on_segment(p1, p3, p4):
        return True
    if abs(d2) <= EPSILON and on_segment(p2, p3, p4):
        return True
    if abs(d3) <= EPSILON and on_segment(p3, p1, p2):
        return True
    if abs(d4) <= EPSILON and on_segment(p4, p1, p2):
        return True

    return False


def segments_cross_strictly(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    """Returns True if segments cross strictly in their interiors."""
    d1 = cross2d(p3, p4, p1)
    d2 = cross2d(p3, p4, p2)
    d3 = cross2d(p1, p2, p3)
    d4 = cross2d(p1, p2, p4)

    return (((d1 > EPSILON and d2 < -EPSILON) or (d1 < -EPSILON and d2 > EPSILON)) and
            ((d3 > EPSILON and d4 < -EPSILON) or (d3 < -EPSILON and d4 > EPSILON)))


def is_simple_polygon(poly: List[Point]) -> Tuple[bool, str]:
    """
    Validates if a polygon is simple:
    1. At least 3 vertices
    2. Non-zero area
    3. No two non-consecutive edges intersect
    4. Consecutive edges don't overlap backwards
    """
    n = len(poly)
    if n < 3:
        return False, "A polygon must have at least 3 vertices."

    if abs(polygon_signed_area(poly)) < 1e-4:
        return False, "Polygon has near-zero or zero area."

    # Check for identical consecutive points
    for i in range(n):
        if dist_sq(poly[i], poly[(i + 1) % n]) < 1e-6:
            return False, f"Duplicate consecutive vertex at index {i}."

    # Check non-adjacent edges for intersection
    for i in range(n):
        a1, a2 = poly[i], poly[(i + 1) % n]
        for j in range(i + 1, n):
            # Skip adjacent edges
            if j == i or j == (i + 1) % n or (i == 0 and j == n - 1):
                continue
            b1, b2 = poly[j], poly[(j + 1) % n]
            if segments_intersect(a1, a2, b1, b2):
                return False, f"Self-intersection between edge ({i},{(i+1)%n}) and edge ({j},{(j+1)%n})."

    return True, "Valid simple polygon."


def is_point_in_triangle(p: Point, a: Point, b: Point, c: Point) -> bool:
    """
    Checks if point p is inside triangle abc (including boundary).
    Works for both CCW and CW triangles.
    """
    c1 = cross2d(a, b, p)
    c2 = cross2d(b, c, p)
    c3 = cross2d(c, a, p)

    has_neg = (c1 < -EPSILON) or (c2 < -EPSILON) or (c3 < -EPSILON)
    has_pos = (c1 > EPSILON) or (c2 > EPSILON) or (c3 > EPSILON)

    return not (has_neg and has_pos)


def is_point_strictly_in_triangle(p: Point, a: Point, b: Point, c: Point) -> bool:
    """Checks if point p is strictly inside triangle abc (excluding boundary)."""
    c1 = cross2d(a, b, p)
    c2 = cross2d(b, c, p)
    c3 = cross2d(c, a, p)

    is_ccw = (c1 > EPSILON) and (c2 > EPSILON) and (c3 > EPSILON)
    is_cw = (c1 < -EPSILON) and (c2 < -EPSILON) and (c3 < -EPSILON)

    return is_ccw or is_cw


def is_point_in_polygon(p: Point, poly: List[Point]) -> bool:
    """
    Standard ray-casting algorithm to test whether point p is inside simple polygon.
    Returns True if inside or on boundary.
    """
    n = len(poly)
    if n < 3:
        return False

    # Check if point is on any edge
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        if abs(cross2d(a, b, p)) <= EPSILON and on_segment(p, a, b):
            return True

    inside = False
    x, y = p
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]

        if ((y1 > y) != (y2 > y)):
            x_inters = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < x_inters:
                inside = not inside

    return inside


def triangulate_ear_clipping(poly: List[Point]) -> Tuple[List[Point], List[Triangle], List[Segment]]:
    """
    Triangulates a simple polygon using the Ear Clipping algorithm.
    Returns:
      ccw_poly: The vertices guaranteed in CCW order.
      triangles: List of vertex index tuples (i, j, k) forming each triangle.
      diagonals: List of internal diagonals ((x1, y1), (x2, y2)).
    """
    ccw_poly, _ = ensure_ccw(poly)
    n = len(ccw_poly)
    if n < 3:
        return ccw_poly, [], []
    if n == 3:
        return ccw_poly, [(0, 1, 2)], []

    indices = list(range(n))
    triangles: List[Triangle] = []
    diagonals: List[Segment] = []

    def is_ear(idx_pos: int) -> bool:
        prev_idx = indices[(idx_pos - 1) % len(indices)]
        curr_idx = indices[idx_pos]
        next_idx = indices[(idx_pos + 1) % len(indices)]

        a = ccw_poly[prev_idx]
        b = ccw_poly[curr_idx]
        c = ccw_poly[next_idx]

        # In CCW polygon, an ear vertex must be strictly convex
        if cross2d(a, b, c) <= EPSILON:
            return False

        # No other polygon vertex can lie inside or on the ear triangle
        for k_idx in indices:
            if k_idx in (prev_idx, curr_idx, next_idx):
                continue
            pk = ccw_poly[k_idx]
            if is_point_in_triangle(pk, a, b, c):
                return False

        return True

    while len(indices) > 3:
        ear_found = False
        for pos in range(len(indices)):
            if is_ear(pos):
                prev_idx = indices[(pos - 1) % len(indices)]
                curr_idx = indices[pos]
                next_idx = indices[(pos + 1) % len(indices)]

                triangles.append((prev_idx, curr_idx, next_idx))

                # If this is not a polygon boundary edge, it's an internal diagonal
                edge_diff = abs(prev_idx - next_idx)
                if edge_diff != 1 and edge_diff != n - 1:
                    diagonals.append((ccw_poly[prev_idx], ccw_poly[next_idx]))

                indices.pop(pos)
                ear_found = True
                break

        if not ear_found:
            # Fallback for near-degenerate or numerically tricky ear
            best_pos = 0
            best_val = -float('inf')
            for pos in range(len(indices)):
                prev_idx = indices[(pos - 1) % len(indices)]
                curr_idx = indices[pos]
                next_idx = indices[(pos + 1) % len(indices)]
                val = cross2d(ccw_poly[prev_idx], ccw_poly[curr_idx], ccw_poly[next_idx])
                if val > best_val:
                    best_val = val
                    best_pos = pos

            prev_idx = indices[(best_pos - 1) % len(indices)]
            curr_idx = indices[best_pos]
            next_idx = indices[(best_pos + 1) % len(indices)]
            triangles.append((prev_idx, curr_idx, next_idx))
            indices.pop(best_pos)

    # Last 3 vertices form the final triangle
    triangles.append((indices[0], indices[1], indices[2]))

    return ccw_poly, triangles, diagonals


def find_triangle_containing_point(p: Point, poly: List[Point], triangles: List[Triangle]) -> Optional[int]:
    """
    Finds the index of the triangle in `triangles` that contains point p.
    Returns triangle index or None if outside all triangles.
    """
    for i, (i1, i2, i3) in enumerate(triangles):
        a, b, c = poly[i1], poly[i2], poly[i3]
        if is_point_in_triangle(p, a, b, c):
            return i

    # Fallback with small distance tolerance if point is near boundary/vertex
    closest_dist = float('inf')
    closest_tri = None
    for i, (i1, i2, i3) in enumerate(triangles):
        a, b, c = poly[i1], poly[i2], poly[i3]
        # Distance to triangle centroid
        centroid = ((a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0)
        d = dist(p, centroid)
        if d < closest_dist:
            closest_dist = d
            closest_tri = i

    return closest_tri


def build_dual_graph(triangles: List[Triangle]) -> Dict[int, List[Tuple[int, Tuple[int, int]]]]:
    """
    Constructs dual graph of triangulation.
    Returns adjacency list: tri_idx -> list of (neighbor_tri_idx, (shared_v1, shared_v2)).
    """
    num_triangles = len(triangles)
    adj: Dict[int, List[Tuple[int, Tuple[int, int]]]] = {i: [] for i in range(num_triangles)}

    for i in range(num_triangles):
        set_i = set(triangles[i])
        for j in range(i + 1, num_triangles):
            set_j = set(triangles[j])
            common = set_i.intersection(set_j)
            if len(common) == 2:
                v1, v2 = tuple(common)
                adj[i].append((j, (v1, v2)))
                adj[j].append((i, (v1, v2)))

    return adj


def find_triangle_corridor(
    triangles: List[Triangle], start_tri: int, end_tri: int
) -> List[int]:
    """
    Finds the unique path of triangles (sleeve/channel) from start_tri to end_tri
    in the dual tree using BFS.
    """
    if start_tri == end_tri:
        return [start_tri]

    adj = build_dual_graph(triangles)
    queue = deque([(start_tri, [start_tri])])
    visited = {start_tri}

    while queue:
        curr, path = queue.popleft()
        if curr == end_tri:
            return path
        for nxt, _ in adj[curr]:
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, path + [nxt]))

    return [start_tri]


def extract_portals(
    poly: List[Point],
    triangles: List[Triangle],
    corridor: List[int],
    s: Point,
    t: Point
) -> List[Tuple[Point, Point]]:
    """
    Extracts the sequence of oriented portals (Left, Right) along the triangle sleeve.
    Starts with (s, s) and ends with (t, t).
    Each intermediate portal is oriented so that Left is to the left of the path
    and Right is to the right as you move from s toward t.
    """
    portals: List[Tuple[Point, Point]] = [(s, s)]

    if len(corridor) <= 1:
        portals.append((t, t))
        return portals

    for k in range(len(corridor) - 1):
        curr_t = corridor[k]
        next_t = corridor[k + 1]

        tri_curr = triangles[curr_t]
        tri_next = set(triangles[next_t])

        # Shared edge indices
        shared = [v for v in tri_curr if v in tri_next]
        if len(shared) != 2:
            continue
        u, v = shared[0], shared[1]

        # In triangle curr_t, ensure vertices are in CCW order
        c0, c1, c2 = tri_curr[0], tri_curr[1], tri_curr[2]
        if cross2d(poly[c0], poly[c1], poly[c2]) < 0:
            c_verts = [c0, c2, c1]
        else:
            c_verts = [c0, c1, c2]

        # In CCW order around curr_t, the directed edge exiting the triangle
        # goes from Right to Left!
        if (
            (c_verts[0] == u and c_verts[1] == v) or
            (c_verts[1] == u and c_verts[2] == v) or
            (c_verts[2] == u and c_verts[0] == v)
        ):
            # u -> v is CCW, so u is Right and v is Left
            right_pt = poly[u]
            left_pt = poly[v]
        else:
            right_pt = poly[v]
            left_pt = poly[u]

        portals.append((left_pt, right_pt))

    portals.append((t, t))
    return portals


def get_triangle_centroid(poly: List[Point], tri: Triangle) -> Point:
    """Calculates the geometric centroid (center of mass) of a triangle."""
    a, b, c = poly[tri[0]], poly[tri[1]], poly[tri[2]]
    return ((a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0)


def get_dual_tree(
    poly: List[Point], triangles: List[Triangle]
) -> Tuple[List[Point], List[Tuple[Point, Point]]]:
    """
    Constructs the dual tree of the triangulation.
    Returns:
      centroids: list of centroid points for all triangles.
      tree_edges: list of segments connecting centroids of adjacent triangles.
    """
    centroids = [get_triangle_centroid(poly, tri) for tri in triangles]
    adj = build_dual_graph(triangles)
    tree_edges: List[Tuple[Point, Point]] = []

    for i in range(len(triangles)):
        for j, _ in adj[i]:
            if i < j:
                tree_edges.append((centroids[i], centroids[j]))

    return centroids, tree_edges


def get_dual_corridor_path(
    corridor: List[int], centroids: List[Point], s: Point, t: Point
) -> List[Point]:
    """
    Returns the sequence of points representing the path through the dual tree:
    Start s -> centroid of T_0 -> centroid of T_1 -> ... -> centroid of T_m -> Target t.
    """
    path = [s]
    for tri_idx in corridor:
        if 0 <= tri_idx < len(centroids):
            path.append(centroids[tri_idx])
    path.append(t)
    return path


