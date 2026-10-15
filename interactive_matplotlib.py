"""
Alternative Matplotlib-based Interactive Funnel Algorithm Runner.
Supports drawing polygon with mouse clicks (left click add vertex, right click close),
automatic triangulation, clicking twice for S and T, viewing the dual tree,
and stepping through the Funnel Algorithm with boundary crossing visualization.
"""

from __future__ import annotations
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from typing import List, Tuple, Optional
from geometry import (
    Point, is_simple_polygon, is_point_in_polygon,
    triangulate_ear_clipping, find_triangle_containing_point,
    find_triangle_corridor, extract_portals, dist,
    get_dual_tree, get_dual_corridor_path
)
from funnel import FunnelAlgorithm


class MatplotlibFunnelApp:

    def __init__(self):
        plt.rcParams['figure.dpi'] = 200
        plt.rcParams['lines.antialiased'] = True
        plt.rcParams['patch.antialiased'] = True
        plt.rcParams['text.antialiased'] = True
        self.fig, self.ax = plt.subplots(figsize=(14, 9), dpi=200)
        self.fig.canvas.manager.set_window_title("Funnel Algorithm (Matplotlib Interactive)")

        self.vertices: List[Point] = []
        self.ccw_poly: List[Point] = []
        self.triangles: List[Tuple[int, int, int]] = []
        self.diagonals: List[Tuple[Point, Point]] = []

        self.start_point: Optional[Point] = None
        self.target_point: Optional[Point] = None
        self.start_tri: Optional[int] = None
        self.target_tri: Optional[int] = None
        self.corridor: List[int] = []
        self.portals: List[Tuple[Point, Point]] = []

        # Dual Tree
        self.centroids: List[Point] = []
        self.dual_edges: List[Tuple[Point, Point]] = []
        self.dual_path: List[Point] = []

        self.funnel_solver: Optional[FunnelAlgorithm] = None
        self.state = "DRAW"  # DRAW, SELECT_S, SELECT_T, DUAL_TREE, STEPPING, DONE
        self.status_text = "Phase 1: Left-click to add polygon vertices. Right-click to close polygon."

        self.cid_click = self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.cid_key = self.fig.canvas.mpl_connect('key_press_event', self.on_key)

        self._init_plot()

    def _init_plot(self):
        self.ax.clear()
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 100)
        self.ax.set_aspect('equal')
        self.ax.grid(True, linestyle=':', alpha=0.5)
        self.ax.set_title(self.status_text, fontsize=11, fontweight='bold', pad=12)
        self.fig.tight_layout()

    def update_display(self):
        self.ax.clear()
        self.ax.set_aspect('equal')
        self.ax.grid(True, linestyle=':', alpha=0.4)

        # Autoscale bounds
        all_pts = list(self.vertices)
        if self.start_point:
            all_pts.append(self.start_point)
        if self.target_point:
            all_pts.append(self.target_point)

        if all_pts:
            xs = [p[0] for p in all_pts]
            ys = [p[1] for p in all_pts]
            dx = max(max(xs) - min(xs), 10)
            dy = max(max(ys) - min(ys), 10)
            margin = max(dx, dy) * 0.15
            self.ax.set_xlim(min(xs) - margin, max(xs) + margin)
            self.ax.set_ylim(min(ys) - margin, max(ys) + margin)
        else:
            self.ax.set_xlim(0, 100)
            self.ax.set_ylim(0, 100)

        # 1. Draw corridor triangles
        if self.corridor and self.triangles and self.ccw_poly:
            for t_idx in self.corridor:
                tri = self.triangles[t_idx]
                pts = [self.ccw_poly[tri[0]], self.ccw_poly[tri[1]], self.ccw_poly[tri[2]]]
                patch = MplPolygon(pts, closed=True, facecolor='#fff2cc', edgecolor='none', alpha=0.6)
                self.ax.add_patch(patch)

        # 2. Draw triangulation diagonals
        if self.diagonals:
            for d in self.diagonals:
                self.ax.plot([d[0][0], d[1][0]], [d[0][1], d[1][1]], color='#999999', linestyle='--', linewidth=0.9)

        # 3. Draw polygon edges & vertices
        active_poly = self.ccw_poly if len(self.ccw_poly) >= 3 else self.vertices
        if len(active_poly) >= 2:
            xs = [p[0] for p in active_poly]
            ys = [p[1] for p in active_poly]
            if self.state != "DRAW" and len(active_poly) >= 3:
                xs.append(active_poly[0][0])
                ys.append(active_poly[0][1])
            self.ax.plot(xs, ys, color='#2b5c8f', linewidth=2, marker='o', markersize=4)

        # 4. Draw Dual Tree (when in DUAL_TREE phase)
        if self.state == "DUAL_TREE" and self.centroids:
            # Tree edges
            for c1, c2 in self.dual_edges:
                self.ax.plot([c1[0], c2[0]], [c1[1], c2[1]], color='#0284c7', linestyle=':', linewidth=1.5)
            # Centroid nodes
            c_xs = [c[0] for c in self.centroids]
            c_ys = [c[1] for c in self.centroids]
            self.ax.plot(c_xs, c_ys, 'o', color='#0284c7', markersize=6, label="Dual Tree Nodes")

            # Corridor path in dual tree
            if len(self.dual_path) >= 2:
                dp_xs = [p[0] for p in self.dual_path]
                dp_ys = [p[1] for p in self.dual_path]
                self.ax.plot(dp_xs, dp_ys, color='#d97706', linewidth=2.5, marker='s', markersize=7, label="Dual Path (S→T)")

        # 5. Draw Funnel state if available (when in STEPPING / DONE phase)
        if self.funnel_solver and self.state in ("STEPPING", "DONE"):
            st = self.funnel_solver.current_state

            # Portals
            for i, (l_pt, r_pt) in enumerate(self.portals):
                if l_pt == r_pt:
                    continue
                is_active = (i == st.portal_idx)
                col = '#d97706' if is_active else '#b0b0b0'
                lw = 2.5 if is_active else 1.0
                self.ax.plot([l_pt[0], r_pt[0]], [l_pt[1], r_pt[1]], color=col, linewidth=lw)

            # Left chain (thick)
            if len(st.left_chain) >= 2:
                l_xs = [p[0] for p in st.left_chain]
                l_ys = [p[1] for p in st.left_chain]
                self.ax.plot(l_xs, l_ys, color='#0284c7', linewidth=3.5, marker='s', markersize=5, label="Left Chain")

            # Right chain (thick)
            if len(st.right_chain) >= 2:
                r_xs = [p[0] for p in st.right_chain]
                r_ys = [p[1] for p in st.right_chain]
                self.ax.plot(r_xs, r_ys, color='#16a34a', linewidth=3.5, marker='^', markersize=5, label="Right Chain")

            # Shortest path (thin, crisp)
            if len(st.path_so_far) >= 2:
                p_xs = [p[0] for p in st.path_so_far]
                p_ys = [p[1] for p in st.path_so_far]
                self.ax.plot(p_xs, p_ys, color='#dc2626', linewidth=1.8, marker='o', markersize=5, label="Shortest Path")

            # Crossing visualization (line crossed before apex moves)
            if st.is_crossing_step and st.crossing_line and st.crossed_segment and st.crossing_point:
                cand_color = '#0284c7' if st.crossing_side == 'left' else '#16a34a'

                # Candidate sightline crossing the boundary (in candidate chain color)
                cl = st.crossing_line
                self.ax.plot([cl[0][0], cl[1][0]], [cl[0][1], cl[1][1]], color=cand_color, linestyle='--', linewidth=2, label="Candidate Line")

                # Crossing point marker (clean dot at the crossed corner)
                cp = st.crossing_point
                self.ax.plot(cp[0], cp[1], marker='o', markersize=7, color='#dc2626')

            # Apex
            self.ax.plot(st.apex[0], st.apex[1], color='#ea580c', marker='*', markersize=12, label="Apex")

        # 6. Draw S and T points
        if self.start_point:
            self.ax.plot(self.start_point[0], self.start_point[1], 'go', markersize=10, label="Start (S)")
            self.ax.text(self.start_point[0] + 0.5, self.start_point[1] + 0.5, "S", color='green', fontweight='bold')
        if self.target_point:
            self.ax.plot(self.target_point[0], self.target_point[1], 'ro', markersize=10, label="Target (T)")
            self.ax.text(self.target_point[0] + 0.5, self.target_point[1] + 0.5, "T", color='red', fontweight='bold')

        self.ax.set_title(self.status_text, fontsize=10, pad=10)
        self.fig.canvas.draw_idle()

    def on_click(self, event):
        if event.xdata is None or event.ydata is None:
            return
        x, y = float(event.xdata), float(event.ydata)

        if self.state == "DRAW":
            if event.button == 1:  # Left click: vertex
                self.vertices.append((x, y))
                self.status_text = f"Added vertex {len(self.vertices)}. Right-click to close."
                self.update_display()
            elif event.button == 3:  # Right click: close
                if len(self.vertices) < 3:
                    self.status_text = "Need at least 3 vertices! Continue clicking."
                    self.update_display()
                    return
                valid, msg = is_simple_polygon(self.vertices)
                if not valid:
                    self.status_text = f"Invalid: {msg} Click to add or restart."
                    self.update_display()
                    return

                self.ccw_poly, self.triangles, self.diagonals = triangulate_ear_clipping(self.vertices)
                self.state = "SELECT_S"
                self.status_text = "Triangulated. Click inside polygon to place Start point (S)."
                self.update_display()

        elif self.state == "SELECT_S":
            if event.button == 1:
                if not is_point_in_polygon((x, y), self.ccw_poly):
                    self.status_text = "Point is outside polygon. Click inside."
                    self.update_display()
                    return
                s_tri = find_triangle_containing_point((x, y), self.ccw_poly, self.triangles)
                self.start_point = (x, y)
                self.start_tri = s_tri
                self.state = "SELECT_T"
                self.status_text = "Start S placed. Click inside polygon to place Target point (T)."
                self.update_display()

        elif self.state == "SELECT_T":
            if event.button == 1:
                if not is_point_in_polygon((x, y), self.ccw_poly):
                    self.status_text = "Point is outside polygon. Click inside."
                    self.update_display()
                    return
                t_tri = find_triangle_containing_point((x, y), self.ccw_poly, self.triangles)
                self.target_point = (x, y)
                self.target_tri = t_tri

                self.corridor = find_triangle_corridor(self.triangles, self.start_tri, self.target_tri)
                self.portals = extract_portals(
                    self.ccw_poly, self.triangles, self.corridor, self.start_point, self.target_point
                )
                self.centroids, self.dual_edges = get_dual_tree(self.ccw_poly, self.triangles)
                self.dual_path = get_dual_corridor_path(
                    self.corridor, self.centroids, self.start_point, self.target_point
                )
                self.funnel_solver = FunnelAlgorithm(self.portals)

                # First show dual tree
                self.state = "DUAL_TREE"
                self.status_text = "Dual Tree displayed. Shows corridor of triangles from S to T. Press [ENTER] to show Funnel."
                self.update_display()

    def on_key(self, event):
        if event.key in ('enter', ' '):
            if self.state == "DUAL_TREE" and self.funnel_solver:
                self.state = "STEPPING"
                st = self.funnel_solver.current_state
                self.status_text = f"[Step 0/{st.total_steps - 1}] {st.description} (Press ENTER)"
                self.update_display()

            elif self.state == "STEPPING" and self.funnel_solver:
                if not self.funnel_solver.is_finished:
                    st = self.funnel_solver.step_forward()
                    if self.funnel_solver.is_finished:
                        self.state = "DONE"
                        self.status_text = f"[Complete] {st.description} (Press 'r' to reset)"
                    else:
                        self.status_text = f"[Step {st.step_number}/{st.total_steps - 1}] {st.description} (Press ENTER)"
                    self.update_display()

        elif event.key == 'r':
            self.vertices.clear()
            self.ccw_poly.clear()
            self.triangles.clear()
            self.diagonals.clear()
            self.start_point = None
            self.target_point = None
            self.corridor.clear()
            self.portals.clear()
            self.centroids.clear()
            self.dual_edges.clear()
            self.dual_path.clear()
            self.funnel_solver = None
            self.state = "DRAW"
            self.status_text = "Phase 1: Left-click to add polygon vertices. Right-click to close polygon."
            self._init_plot()


def main():
    app = MatplotlibFunnelApp()
    plt.show()


if __name__ == "__main__":
    main()
