"""
Interactive Funnel Algorithm Application (High-Resolution White Theme).
Allows users to draw a polygon, view automatic triangulation,
place start (S) and target (T) points, view the dual tree of the triangulation,
and step through the Funnel Algorithm with thick funnel boundaries and a thin path line.

Features high-DPI crisp vector rendering, smooth anti-aliased geometry,
resolution scaling, fullscreen toggle (F / F11), and calm status messages.
"""

from __future__ import annotations
import sys
import os
import math
import argparse
import pygame
import pygame.gfxdraw
from typing import List, Tuple, Optional
from geometry import (
    Point, is_simple_polygon, is_point_in_polygon,
    triangulate_ear_clipping, find_triangle_containing_point,
    find_triangle_corridor, extract_portals, dist,
    segments_intersect, get_dual_tree, get_dual_corridor_path
)
from funnel import FunnelAlgorithm, FunnelState
from export_utils import StepRecorder, save_canvas_screenshot, generate_grid_plot

# Enable SDL high-DPI scaling hints with crisp nearest filtering (no linear blur)
os.environ["SDL_HINT_VIDEO_HIGHDPI_DISABLED"] = "0"
os.environ["SDL_HINT_RENDER_SCALE_QUALITY"] = "0"

# --- Color Palette (Crisp High-Contrast White Theme) ---
COLOR_BG = (255, 255, 255)              # Pure white canvas
COLOR_PANEL_BG = (248, 249, 251)        # Clean off-white panel bar
COLOR_PANEL_BORDER = (222, 226, 230)    # Soft gray separator line
COLOR_TEXT_PRIMARY = (20, 24, 33)       # Deep charcoal text (maximum contrast)
COLOR_TEXT_SECONDARY = (100, 108, 118)  # Muted secondary text
COLOR_TEXT_ACCENT = (13, 110, 253)      # Royal blue highlight
COLOR_TEXT_WARN = (220, 53, 69)         # Error red

COLOR_POLY_EDGE = (30, 64, 175)         # Deep rich blue polygon outline
COLOR_POLY_FILL = (239, 246, 255, 140)  # Very soft light blue interior
COLOR_VERTEX = (37, 99, 235)            # Blue vertex dots
COLOR_RUBBER_BAND = (96, 165, 250)      # Sky blue dynamic mouse line

COLOR_TRI_DIAG = (195, 205, 218)        # Clean subtle gray diagonals
COLOR_CORRIDOR_FILL = (254, 243, 199, 140) # Soft translucent amber triangle strip
COLOR_PORTAL = (156, 163, 175)          # Neutral gray inactive portals
COLOR_ACTIVE_PORTAL = (217, 119, 6)     # Warm amber active portal

# Dual Tree Colors
COLOR_DUAL_NODE = (14, 165, 233)        # Cyan/sky blue centroid nodes
COLOR_DUAL_EDGE = (156, 163, 175)       # Dashed gray dual tree edges
COLOR_DUAL_PATH = (217, 119, 6)         # Amber corridor path in dual tree

# Funnel Colors (Thick Funnel Lines, Thin Path Line)
COLOR_START = (22, 163, 74)             # Crisp green for S
COLOR_TARGET = (220, 38, 38)            # Crisp red for T
COLOR_APEX = (234, 88, 12)              # Warm vibrant orange for apex
COLOR_LEFT_CHAIN = (2, 132, 199)        # Bold sky blue for left chain (thick)
COLOR_RIGHT_CHAIN = (22, 163, 74)       # Bold emerald green for right chain (thick)
COLOR_PATH = (220, 38, 38)              # Crisp thin crimson red for shortest path (thin)

# Crossing Visualization Colors (Clean & Tasteful)
COLOR_CROSSING_LINE = (225, 29, 72)     # Dashed line showing sightline crossing boundary
COLOR_CROSSED_SEG = (190, 24, 93)       # Highlighted boundary segment that is crossed
COLOR_CROSSING_POINT = (225, 29, 72)    # Clean dot marker at the crossed corner

# Application States
STATE_DRAW_POLYGON = "DRAW_POLYGON"
STATE_SELECT_START = "SELECT_START"
STATE_SELECT_TARGET = "SELECT_TARGET"
STATE_SHOW_DUAL_TREE = "SHOW_DUAL_TREE"
STATE_STEPPING = "STEPPING"
STATE_FINISHED = "FINISHED"

RESOLUTION_PRESETS = [
    (1280, 720),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
    (3840, 2160),
]


def draw_aa_circle(surface: pygame.Surface, color: Tuple[int, ...], center: Point, radius: float):
    """Draws a smooth anti-aliased filled circle."""
    x, y, r = int(round(center[0])), int(round(center[1])), int(round(radius))
    if r <= 0:
        return
    c = (color[0], color[1], color[2], 255 if len(color) < 4 else color[3])
    pygame.gfxdraw.filled_circle(surface, x, y, r, c)
    pygame.gfxdraw.aacircle(surface, x, y, r, c)


def draw_aa_line(surface: pygame.Surface, color: Tuple[int, ...], p1: Point, p2: Point, width: float = 1.0):
    """Draws a smooth anti-aliased line segment with sub-pixel thickness and rounded caps."""
    x1, y1 = float(p1[0]), float(p1[1])
    x2, y2 = float(p2[0]), float(p2[1])
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-4:
        return

    c = (color[0], color[1], color[2], 255 if len(color) < 4 else color[3])
    if width <= 1.2:
        pygame.draw.aaline(surface, c, (int(round(x1)), int(round(y1))), (int(round(x2)), int(round(y2))))
        return

    # Normal vector for perpendicular offset
    half_w = width * 0.5
    nx = -dy / length * half_w
    ny = dx / length * half_w

    pts = [
        (int(round(x1 + nx)), int(round(y1 + ny))),
        (int(round(x2 + nx)), int(round(y2 + ny))),
        (int(round(x2 - nx)), int(round(y2 - ny))),
        (int(round(x1 - nx)), int(round(y1 - ny))),
    ]

    pygame.gfxdraw.filled_polygon(surface, pts, c)
    pygame.gfxdraw.aapolygon(surface, pts, c)

    r = int(round(half_w))
    if r >= 1:
        pygame.gfxdraw.filled_circle(surface, int(round(x1)), int(round(y1)), r, c)
        pygame.gfxdraw.aacircle(surface, int(round(x1)), int(round(y1)), r, c)
        pygame.gfxdraw.filled_circle(surface, int(round(x2)), int(round(y2)), r, c)
        pygame.gfxdraw.aacircle(surface, int(round(x2)), int(round(y2)), r, c)


def draw_aa_polyline(surface: pygame.Surface, color: Tuple[int, ...], points: List[Point], width: float = 1.0):
    """Draws a smooth anti-aliased polyline."""
    if len(points) < 2:
        return
    for i in range(len(points) - 1):
        draw_aa_line(surface, color, points[i], points[i + 1], width)


def draw_dashed_aa_line(
    surface: pygame.Surface,
    color: Tuple[int, int, int],
    start_pos: Point,
    end_pos: Point,
    width: float = 1.0,
    dash_length: float = 8.0,
    space_length: float = 5.0
):
    """Draws a crisp anti-aliased dashed line between two points."""
    x1, y1 = start_pos
    x2, y2 = end_pos
    dx = x2 - x1
    dy = y2 - y1
    distance = math.hypot(dx, dy)
    if distance < 1e-4:
        return

    step_x = (dx / distance) * (dash_length + space_length)
    step_y = (dy / distance) * (dash_length + space_length)
    dash_dx = (dx / distance) * dash_length
    dash_dy = (dy / distance) * dash_length

    curr_x, curr_y = x1, y1
    dist_covered = 0.0

    while dist_covered < distance:
        seg_end_x = curr_x + dash_dx
        seg_end_y = curr_y + dash_dy
        if dist_covered + dash_length > distance:
            seg_end_x, seg_end_y = x2, y2

        draw_aa_line(surface, color, (curr_x, curr_y), (seg_end_x, seg_end_y), width)
        dist_covered += dash_length + space_length
        curr_x += step_x
        curr_y += step_y


class FunnelInteractiveApp:

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        fullscreen: bool = False,
        record_mode: bool = False,
        screenshot_folder: Optional[str] = None
    ):
        pygame.init()
        pygame.display.set_caption("Shortest Paths in Simple Polygons — Interactive Funnel Algorithm")

        self.fullscreen = fullscreen
        self.width = width
        self.height = height

        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.width, self.height = self.screen.get_size()
        else:
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)

        self.clock = pygame.time.Clock()
        self._update_scale_and_fonts()

        # Step Recording & Screenshot Mode
        self.record_mode = record_mode
        self.recorder = StepRecorder(base_folder=screenshot_folder, auto_record=record_mode)

        # State Variables
        self.state = STATE_DRAW_POLYGON
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

        # Dual Tree Variables
        self.centroids: List[Point] = []
        self.dual_edges: List[Tuple[Point, Point]] = []
        self.dual_path: List[Point] = []

        self.funnel_solver: Optional[FunnelAlgorithm] = None
        self.status_message = "Click to add polygon vertices. Right-click to close polygon."
        self.warning_message: Optional[str] = None
        self.warning_timer = 0

    def _update_scale_and_fonts(self):
        """Calculates scale factor based on current resolution and updates fonts."""
        # Scale factor normalized to 1200x800 base
        self.scale = max(1.0, min(self.width / 1200.0, self.height / 800.0))
        self.header_height = int(65 * self.scale)
        self.footer_height = int(75 * self.scale)

        font_names = ["ubuntu", "dejavusans", "liberationsans", "arial"]
        self.font_title = pygame.font.SysFont(font_names, int(20 * self.scale), bold=True)
        self.font_bold = pygame.font.SysFont(font_names, int(15 * self.scale), bold=True)
        self.font_normal = pygame.font.SysFont(font_names, int(15 * self.scale))
        self.font_small = pygame.font.SysFont(font_names, int(13 * self.scale))

    def _rescale_coordinates(self, rx: float, ry: float):
        """Proportionally rescales active geometric elements when window resolution changes."""
        if rx <= 0 or ry <= 0 or (abs(rx - 1.0) < 1e-4 and abs(ry - 1.0) < 1e-4):
            return

        self.vertices = [(p[0] * rx, p[1] * ry) for p in self.vertices]
        self.ccw_poly = [(p[0] * rx, p[1] * ry) for p in self.ccw_poly]
        self.diagonals = [((p1[0] * rx, p1[1] * ry), (p2[0] * rx, p2[1] * ry)) for p1, p2 in self.diagonals]

        if self.start_point:
            self.start_point = (self.start_point[0] * rx, self.start_point[1] * ry)
        if self.target_point:
            self.target_point = (self.target_point[0] * rx, self.target_point[1] * ry)

        if self.portals:
            self.portals = [((l[0] * rx, l[1] * ry), (r[0] * rx, r[1] * ry)) for l, r in self.portals]
        if self.centroids:
            self.centroids = [(c[0] * rx, c[1] * ry) for c in self.centroids]
        if self.dual_edges:
            self.dual_edges = [((p1[0] * rx, p1[1] * ry), (p2[0] * rx, p2[1] * ry)) for p1, p2 in self.dual_edges]
        if self.dual_path:
            self.dual_path = [(p[0] * rx, p[1] * ry) for p in self.dual_path]

        if self.funnel_solver and self.portals:
            saved_step = self.funnel_solver.current_step_index
            self.funnel_solver = FunnelAlgorithm(self.portals)
            for _ in range(saved_step):
                if not self.funnel_solver.is_finished:
                    self.funnel_solver.step_forward()

    def toggle_fullscreen(self):
        """Toggles between fullscreen native display mode and windowed mode."""
        old_w, old_h = self.width, self.height
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        new_w, new_h = self.screen.get_size()
        if old_w > 0 and old_h > 0 and (new_w != old_w or new_h != old_h):
            self._rescale_coordinates(new_w / old_w, new_h / old_h)
        self.width, self.height = new_w, new_h
        self._update_scale_and_fonts()

    def set_resolution(self, w: int, h: int):
        """Changes window resolution and rescales geometry proportionally."""
        if not self.fullscreen:
            old_w, old_h = self.width, self.height
            if old_w > 0 and old_h > 0 and (w != old_w or h != old_h):
                self._rescale_coordinates(w / old_w, h / old_h)
            self.width = w
            self.height = h
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
            self._update_scale_and_fonts()

    def reset(self):
        """Resets the application to initial polygon drawing state."""
        self.state = STATE_DRAW_POLYGON
        self.vertices.clear()
        self.ccw_poly.clear()
        self.triangles.clear()
        self.diagonals.clear()
        self.start_point = None
        self.target_point = None
        self.start_tri = None
        self.target_tri = None
        self.corridor.clear()
        self.portals.clear()
        self.centroids.clear()
        self.dual_edges.clear()
        self.dual_path.clear()
        self.funnel_solver = None
        self.status_message = "Click to add polygon vertices. Right-click to close polygon."
        self.warning_message = None

    def load_preset(self, preset_id: int):
        """Loads a built-in demo polygon scaled to current canvas dimensions."""
        self.reset()
        w, h = self.width, self.height
        cx, cy = w // 2, h // 2
        s = self.scale

        if preset_id == 1:
            # L-shaped corridor
            self.vertices = [
                (cx - int(320 * s), cy - int(220 * s)),
                (cx - int(60 * s), cy - int(220 * s)),
                (cx - int(60 * s), cy + int(60 * s)),
                (cx + int(320 * s), cy + int(60 * s)),
                (cx + int(320 * s), cy + int(240 * s)),
                (cx - int(320 * s), cy + int(240 * s)),
            ]
        elif preset_id == 2:
            # U-shaped polygon
            self.vertices = [
                (cx - int(380 * s), cy - int(240 * s)),
                (cx - int(160 * s), cy - int(240 * s)),
                (cx - int(160 * s), cy + int(110 * s)),
                (cx + int(160 * s), cy + int(110 * s)),
                (cx + int(160 * s), cy - int(240 * s)),
                (cx + int(380 * s), cy - int(240 * s)),
                (cx + int(380 * s), cy + int(260 * s)),
                (cx - int(380 * s), cy + int(260 * s)),
            ]
        elif preset_id == 3:
            # S-shaped labyrinth corridor with two internal baffles
            self.vertices = [
                (cx - int(360 * s), cy - int(200 * s)),
                (cx + int(360 * s), cy - int(200 * s)),
                (cx + int(360 * s), cy + int(60 * s)),
                (cx - int(150 * s), cy + int(60 * s)),
                (cx - int(150 * s), cy + int(100 * s)),
                (cx + int(360 * s), cy + int(100 * s)),
                (cx + int(360 * s), cy + int(220 * s)),
                (cx - int(360 * s), cy + int(220 * s)),
                (cx - int(360 * s), cy - int(60 * s)),
                (cx + int(150 * s), cy - int(60 * s)),
                (cx + int(150 * s), cy - int(100 * s)),
                (cx - int(360 * s), cy - int(100 * s)),
            ]

        self._close_polygon_and_triangulate()

    def _close_polygon_and_triangulate(self):
        """Validates polygon, runs ear clipping triangulation, and transitions to point selection."""
        if len(self.vertices) < 3:
            self.set_warning("A polygon must have at least 3 vertices!")
            return

        is_valid, msg = is_simple_polygon(self.vertices)
        if not is_valid:
            self.set_warning(f"Invalid polygon: {msg}")
            return

        self.ccw_poly, self.triangles, self.diagonals = triangulate_ear_clipping(self.vertices)
        self.state = STATE_SELECT_START
        self.status_message = "Polygon triangulated. Click inside polygon to place Start point (S)."
        self.warning_message = None

    def set_warning(self, msg: str):
        self.warning_message = msg
        self.warning_timer = pygame.time.get_ticks() + 4000

    def handle_mouse_click(self, pos: Point, button: int):
        x, y = float(pos[0]), float(pos[1])

        # Ignore clicks in header or footer panel
        if y < self.header_height or y > self.height - self.footer_height:
            return

        if self.state == STATE_DRAW_POLYGON:
            if button == 1:  # Left-click: Add vertex
                if len(self.vertices) >= 2:
                    new_seg = (self.vertices[-1], (x, y))
                    for i in range(len(self.vertices) - 2):
                        prev_seg = (self.vertices[i], self.vertices[i + 1])
                        if segments_intersect(new_seg[0], new_seg[1], prev_seg[0], prev_seg[1]):
                            self.set_warning("New edge crosses an existing edge! Click elsewhere.")
                            return

                self.vertices.append((x, y))
                self.status_message = f"Added vertex {len(self.vertices)}. Right-click to close polygon."
            elif button == 3:  # Right-click: Close polygon
                self._close_polygon_and_triangulate()

        elif self.state == STATE_SELECT_START:
            if button == 1:
                if not is_point_in_polygon((x, y), self.ccw_poly):
                    self.set_warning("Start point (S) must be inside the polygon!")
                    return
                s_tri = find_triangle_containing_point((x, y), self.ccw_poly, self.triangles)
                if s_tri is None:
                    self.set_warning("Could not locate triangle for Start point. Click inside!")
                    return
                self.start_point = (x, y)
                self.start_tri = s_tri
                self.state = STATE_SELECT_TARGET
                self.status_message = "Start point S selected. Click inside polygon to place Target (T)."

        elif self.state == STATE_SELECT_TARGET:
            if button == 1:
                if not is_point_in_polygon((x, y), self.ccw_poly):
                    self.set_warning("Target point (T) must be inside the polygon!")
                    return
                t_tri = find_triangle_containing_point((x, y), self.ccw_poly, self.triangles)
                if t_tri is None:
                    self.set_warning("Could not locate triangle for Target point. Click inside!")
                    return
                self.target_point = (x, y)
                self.target_tri = t_tri

                # 1. Find corridor and portals
                self.corridor = find_triangle_corridor(self.triangles, self.start_tri, self.target_tri)
                self.portals = extract_portals(
                    self.ccw_poly, self.triangles, self.corridor, self.start_point, self.target_point
                )

                # 2. Extract Dual Tree and Corridor Path in Dual Tree
                self.centroids, self.dual_edges = get_dual_tree(self.ccw_poly, self.triangles)
                self.dual_path = get_dual_corridor_path(
                    self.corridor, self.centroids, self.start_point, self.target_point
                )

                # 3. Initialize Funnel Algorithm solver
                self.funnel_solver = FunnelAlgorithm(self.portals)

                # 4. First show the dual tree
                self.state = STATE_SHOW_DUAL_TREE
                self.status_message = (
                    f"Dual Tree displayed ({len(self.centroids)} nodes, {len(self.corridor)} triangles in corridor). "
                    f"Press ENTER to view the Funnel Algorithm."
                )

                if self.record_mode:
                    self.recorder.reset_session()
                    self.screen.fill(COLOR_BG)
                    self.draw_polygon_and_triangulation()
                    self.draw_dual_tree()
                    self.draw_start_and_target()
                    self.recorder.capture_step(
                        self.screen, self.header_height, self.footer_height,
                        "00_dual_tree", "Step 0: Dual Tree & Corridor Path"
                    )

    def export_all_steps_grid(self, custom_folder: Optional[str] = None) -> Optional[str]:
        """
        Automatically steps through the entire funnel algorithm for current polygon and S/T,
        captures cropped screenshots for each step (drawing only), compiles a grid plot with a unified legend,
        and restores the application state.
        """
        if not self.funnel_solver or not self.portals or self.start_point is None or self.target_point is None:
            self.set_warning("Must declare polygon, Start (S), and Target (T) first!")
            return None

        prev_state = self.state
        prev_step_idx = self.funnel_solver.current_step_index

        rec = StepRecorder(base_folder=custom_folder)
        rec.reset_session(custom_folder)

        # 1. Capture Step 0: Dual Tree & Corridor
        self.state = STATE_SHOW_DUAL_TREE
        self.screen.fill(COLOR_BG)
        self.draw_polygon_and_triangulation()
        self.draw_dual_tree()
        self.draw_start_and_target()
        rec.capture_step(
            self.screen, self.header_height, self.footer_height,
            "00_dual_tree", "Step 0: Dual Tree & Corridor Path"
        )

        # 2. Iterate through all Funnel states
        self.state = STATE_STEPPING
        solver = FunnelAlgorithm(self.portals)
        total_steps = solver.total_steps

        for step_i in range(total_steps):
            self.funnel_solver = solver
            curr = solver.current_state

            self.screen.fill(COLOR_BG)
            self.draw_polygon_and_triangulation()
            self.draw_dual_tree()
            self.draw_funnel_state()
            self.draw_start_and_target()

            step_num = step_i + 1
            if step_i == total_steps - 1:
                caption = f"Step {step_num}: Path Complete ({curr.path_length:.1f})"
                tag = f"{step_num:02d}_complete"
            elif curr.is_crossing_step:
                caption = f"Step {step_num}: Sightline Crosses Boundary"
                tag = f"{step_num:02d}_crossing"
            elif step_i == 0:
                caption = f"Step 1: Funnel Initialized at S"
                tag = f"01_init"
            else:
                caption = f"Step {step_num}: Portal {curr.portal_idx} Updated"
                tag = f"{step_num:02d}_step"

            rec.capture_step(
                self.screen, self.header_height, self.footer_height,
                tag, caption
            )

            if not solver.is_finished:
                solver.step_forward()

        # 3. Build Grid Plot with unified legend
        poly_n = len(self.ccw_poly)
        grid_file = rec.build_grid_plot(
            title=f"Funnel Algorithm Step-by-Step ({poly_n} Vertices, Path Length: {solver.current_state.path_length:.2f})"
        )

        # 4. Restore original state
        self.state = prev_state
        self.funnel_solver = FunnelAlgorithm(self.portals)
        for _ in range(prev_step_idx):
            if not self.funnel_solver.is_finished:
                self.funnel_solver.step_forward()

        self.status_message = f"Screenshots ({len(rec.recorded_steps)}) & grid saved: {grid_file}"
        return grid_file

    def handle_keydown(self, key: int):
        if key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()

        elif key in (pygame.K_f, pygame.K_F11):
            self.toggle_fullscreen()

        elif key in (pygame.K_PLUS, pygame.K_EQUALS):
            # Increase resolution to next preset
            for w, h in RESOLUTION_PRESETS:
                if w > self.width:
                    self.set_resolution(w, h)
                    break

        elif key in (pygame.K_MINUS, pygame.K_UNDERSCORE):
            # Decrease resolution to previous preset
            for w, h in reversed(RESOLUTION_PRESETS):
                if w < self.width:
                    self.set_resolution(w, h)
                    break

        elif key == pygame.K_r:
            self.reset()

        elif key in (pygame.K_p, pygame.K_g):
            self.export_all_steps_grid()

        elif key == pygame.K_s:
            self.record_mode = not self.record_mode
            status_txt = "ON" if self.record_mode else "OFF"
            self.status_message = f"Step screenshot recording is now {status_txt}. (Press 'P' to export all steps immediately)."

        elif key in (pygame.K_1, pygame.K_2, pygame.K_3):
            preset_map = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3}
            self.load_preset(preset_map[key])

        elif key in (pygame.K_u, pygame.K_BACKSPACE):
            if self.state == STATE_DRAW_POLYGON and self.vertices:
                self.vertices.pop()
                self.status_message = f"Removed last vertex. {len(self.vertices)} vertices remaining."
            elif self.state == STATE_SHOW_DUAL_TREE:
                self.target_point = None
                self.target_tri = None
                self.corridor.clear()
                self.portals.clear()
                self.centroids.clear()
                self.dual_edges.clear()
                self.dual_path.clear()
                self.funnel_solver = None
                self.state = STATE_SELECT_TARGET
                self.status_message = "Start point S selected. Click inside polygon to place Target (T)."
            elif self.state in (STATE_STEPPING, STATE_FINISHED) and self.funnel_solver:
                if self.funnel_solver.current_step_index == 0:
                    self.state = STATE_SHOW_DUAL_TREE
                    self.status_message = "Dual Tree displayed. Press ENTER to show the Funnel Algorithm."
                else:
                    self.funnel_solver.step_backward()
                    self.state = STATE_STEPPING
                    curr = self.funnel_solver.current_state
                    self.status_message = f"[Step {curr.step_number}/{curr.total_steps - 1}] {curr.description}"

        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.state == STATE_SHOW_DUAL_TREE and self.funnel_solver:
                self.state = STATE_STEPPING
                curr = self.funnel_solver.current_state
                self.status_message = (
                    f"[Step 0/{curr.total_steps - 1}] {curr.description} "
                    f"(Press ENTER to continue)"
                )
                if self.record_mode:
                    self.screen.fill(COLOR_BG)
                    self.draw_polygon_and_triangulation()
                    self.draw_dual_tree()
                    self.draw_funnel_state()
                    self.draw_start_and_target()
                    self.recorder.capture_step(
                        self.screen, self.header_height, self.footer_height,
                        "01_funnel_init", "Step 1: Funnel Initialized at S"
                    )

            elif self.state == STATE_STEPPING and self.funnel_solver:
                if not self.funnel_solver.is_finished:
                    new_st = self.funnel_solver.step_forward()
                    if self.funnel_solver.is_finished:
                        self.state = STATE_FINISHED
                        self.status_message = (
                            f"[Complete] {new_st.description} | Press 'R' to reset and draw a new polygon."
                        )
                    else:
                        self.status_message = (
                            f"[Step {new_st.step_number}/{new_st.total_steps - 1}] {new_st.description} "
                            f"(Press ENTER to continue)"
                        )

                    if self.record_mode:
                        self.screen.fill(COLOR_BG)
                        self.draw_polygon_and_triangulation()
                        self.draw_dual_tree()
                        self.draw_funnel_state()
                        self.draw_start_and_target()
                        step_num = new_st.step_number + 1
                        if self.funnel_solver.is_finished:
                            self.recorder.capture_step(
                                self.screen, self.header_height, self.footer_height,
                                f"{step_num:02d}_complete", f"Step {step_num}: Path Complete (Length: {new_st.path_length:.1f})"
                            )
                            grid_p = self.recorder.build_grid_plot()
                            self.status_message = f"[Complete] Grid plot saved to: {grid_p}"
                        elif new_st.is_crossing_step:
                            self.recorder.capture_step(
                                self.screen, self.header_height, self.footer_height,
                                f"{step_num:02d}_crossing", f"Step {step_num}: Sightline Crosses Boundary"
                            )
                        else:
                            self.recorder.capture_step(
                                self.screen, self.header_height, self.footer_height,
                                f"{step_num:02d}_step", f"Step {step_num}: Portal {new_st.portal_idx} Updated"
                            )
                else:
                    self.state = STATE_FINISHED

            elif self.state == STATE_FINISHED and self.funnel_solver:
                self.status_message = (
                    f"[Complete] Path length: {self.funnel_solver.current_state.path_length:.2f}. "
                    f"Press 'R' to draw a new polygon."
                )

    # --- RENDER METHODS ---

    def draw_polygon_and_triangulation(self):
        # Draw translucent polygon fill with smooth anti-aliased edges
        if len(self.ccw_poly) >= 3 and self.state != STATE_DRAW_POLYGON:
            poly_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            int_pts = [(int(round(p[0])), int(round(p[1]))) for p in self.ccw_poly]
            pygame.gfxdraw.filled_polygon(poly_surf, int_pts, COLOR_POLY_FILL)
            pygame.gfxdraw.aapolygon(poly_surf, int_pts, COLOR_POLY_FILL)

            # Highlight corridor triangles if available
            if self.corridor and self.triangles:
                for tri_idx in self.corridor:
                    tri = self.triangles[tri_idx]
                    t_pts = [
                        (int(round(self.ccw_poly[tri[0]][0])), int(round(self.ccw_poly[tri[0]][1]))),
                        (int(round(self.ccw_poly[tri[1]][0])), int(round(self.ccw_poly[tri[1]][1]))),
                        (int(round(self.ccw_poly[tri[2]][0])), int(round(self.ccw_poly[tri[2]][1]))),
                    ]
                    pygame.gfxdraw.filled_polygon(poly_surf, t_pts, COLOR_CORRIDOR_FILL)
                    pygame.gfxdraw.aapolygon(poly_surf, t_pts, COLOR_CORRIDOR_FILL)

            self.screen.blit(poly_surf, (0, 0))

        # Draw triangulation diagonals
        if self.diagonals and self.state != STATE_DRAW_POLYGON:
            for d in self.diagonals:
                draw_dashed_aa_line(
                    self.screen, COLOR_TRI_DIAG, d[0], d[1],
                    width=1.0, dash_length=6.0 * self.scale, space_length=4.0 * self.scale
                )

        # Draw polygon boundary edges
        active_poly = self.ccw_poly if len(self.ccw_poly) >= 3 else self.vertices
        n = len(active_poly)
        if n >= 2:
            for i in range(n - 1):
                draw_aa_line(self.screen, COLOR_POLY_EDGE, active_poly[i], active_poly[i + 1], width=2.0 * self.scale)

            if self.state != STATE_DRAW_POLYGON and n >= 3:
                draw_aa_line(self.screen, COLOR_POLY_EDGE, active_poly[-1], active_poly[0], width=2.0 * self.scale)

        # Draw rubber-band line while drawing
        if self.state == STATE_DRAW_POLYGON and n >= 1:
            mouse_pos = pygame.mouse.get_pos()
            draw_dashed_aa_line(
                self.screen, COLOR_RUBBER_BAND, active_poly[-1], mouse_pos,
                width=1.5, dash_length=5.0 * self.scale, space_length=3.0 * self.scale
            )

        # Draw vertices
        v_radius = 5.0 * self.scale
        for pt in active_poly:
            draw_aa_circle(self.screen, COLOR_BG, pt, v_radius + 1.0)
            draw_aa_circle(self.screen, COLOR_VERTEX, pt, v_radius)

    def draw_dual_tree(self):
        """Draws the dual tree of the triangulation and the corridor path."""
        if not self.centroids or self.state not in (STATE_SHOW_DUAL_TREE, STATE_STEPPING):
            return

        is_focus_dual = (self.state == STATE_SHOW_DUAL_TREE)

        # 1. Draw all tree edges between adjacent triangle centroids
        tree_edge_color = COLOR_DUAL_EDGE if is_focus_dual else (220, 224, 230)
        for c1, c2 in self.dual_edges:
            if is_focus_dual:
                draw_dashed_aa_line(
                    self.screen, tree_edge_color, c1, c2,
                    width=1.5, dash_length=6.0 * self.scale, space_length=4.0 * self.scale
                )
            else:
                draw_aa_line(self.screen, tree_edge_color, c1, c2, width=1.0)

        # 2. Draw all centroid nodes
        if is_focus_dual:
            c_radius = 5.0 * self.scale
            for i, c in enumerate(self.centroids):
                in_corridor = (i in self.corridor)
                node_col = COLOR_DUAL_PATH if in_corridor else COLOR_DUAL_NODE
                draw_aa_circle(self.screen, COLOR_BG, c, c_radius + 1.5)
                draw_aa_circle(self.screen, node_col, c, c_radius)

        # 3. Highlight the unique Corridor Path in the Dual Tree (clean crisp line, no fuzzy glow)
        if is_focus_dual and len(self.dual_path) >= 2:
            draw_aa_polyline(self.screen, COLOR_DUAL_PATH, self.dual_path, width=2.5 * self.scale)
            for p in self.dual_path:
                draw_aa_circle(self.screen, COLOR_DUAL_PATH, p, 4.0 * self.scale)

    def draw_funnel_state(self):
        """Draws the active funnel, apex, chains, crossing lines, and shortest path."""
        if not self.funnel_solver or self.state not in (STATE_STEPPING, STATE_FINISHED):
            return

        curr: FunnelState = self.funnel_solver.current_state

        # Draw all portals in corridor
        for i, (l_pt, r_pt) in enumerate(self.portals):
            if l_pt == r_pt:
                continue
            is_active = (i == curr.portal_idx)
            color = COLOR_ACTIVE_PORTAL if is_active else COLOR_PORTAL
            width = (2.5 if is_active else 1.2) * self.scale
            draw_aa_line(self.screen, color, l_pt, r_pt, width=width)

        # Draw Funnel Left Chain (thick lines: width 4.5 * scale)
        chain_w = 4.5 * self.scale
        if len(curr.left_chain) >= 2:
            draw_aa_polyline(self.screen, COLOR_LEFT_CHAIN, curr.left_chain, width=chain_w)
            for p in curr.left_chain[1:]:
                draw_aa_circle(self.screen, COLOR_LEFT_CHAIN, p, 5.0 * self.scale)

        # Draw Funnel Right Chain (thick lines: width 4.5 * scale)
        if len(curr.right_chain) >= 2:
            draw_aa_polyline(self.screen, COLOR_RIGHT_CHAIN, curr.right_chain, width=chain_w)
            for p in curr.right_chain[1:]:
                draw_aa_circle(self.screen, COLOR_RIGHT_CHAIN, p, 5.0 * self.scale)

        # --- Crossing Visualization (Clean, non-exaggerated) ---
        if curr.is_crossing_step and curr.crossing_line and curr.crossed_segment and curr.crossing_point:
            # Highlight the boundary segment that is being crossed
            draw_aa_line(
                self.screen, COLOR_CROSSED_SEG,
                curr.crossed_segment[0], curr.crossed_segment[1],
                width=3.5 * self.scale
            )

            # Draw the candidate line from Apex to portal vertex crossing the boundary
            draw_dashed_aa_line(
                self.screen, COLOR_CROSSING_LINE,
                curr.crossing_line[0], curr.crossing_line[1],
                width=2.0 * self.scale,
                dash_length=6.0 * self.scale,
                space_length=4.0 * self.scale
            )
            draw_aa_circle(self.screen, COLOR_CROSSING_LINE, curr.crossing_line[1], 4.5 * self.scale)

            # Clean neat marker at the corner where the line crosses
            draw_aa_circle(self.screen, COLOR_BG, curr.crossing_point, 6.0 * self.scale)
            draw_aa_circle(self.screen, COLOR_CROSSING_POINT, curr.crossing_point, 4.5 * self.scale)

        # Draw Shortest Path so far (thin, crisp line: width 2.0 * scale, no blurry glow)
        if len(curr.path_so_far) >= 2:
            path_w = 2.0 * self.scale
            draw_aa_polyline(self.screen, COLOR_PATH, curr.path_so_far, width=path_w)
            for p in curr.path_so_far:
                draw_aa_circle(self.screen, COLOR_PATH, p, 3.5 * self.scale)

        # Draw Funnel Apex
        apex_r = 7.0 * self.scale
        draw_aa_circle(self.screen, COLOR_BG, curr.apex, apex_r + 2.0)
        draw_aa_circle(self.screen, COLOR_APEX, curr.apex, apex_r)
        apex_lbl = self.font_bold.render("Apex", True, COLOR_APEX)
        self.screen.blit(apex_lbl, (int(curr.apex[0] + 10 * self.scale), int(curr.apex[1] - 8 * self.scale)))

    def draw_start_and_target(self):
        marker_r = 9.0 * self.scale
        if self.start_point:
            sp = (int(self.start_point[0]), int(self.start_point[1]))
            draw_aa_circle(self.screen, COLOR_BG, self.start_point, marker_r + 2.0)
            draw_aa_circle(self.screen, COLOR_START, self.start_point, marker_r)
            lbl = self.font_bold.render("S", True, (255, 255, 255))
            self.screen.blit(lbl, (sp[0] - lbl.get_width() // 2, sp[1] - lbl.get_height() // 2))

        if self.target_point:
            tp = (int(self.target_point[0]), int(self.target_point[1]))
            draw_aa_circle(self.screen, COLOR_BG, self.target_point, marker_r + 2.0)
            draw_aa_circle(self.screen, COLOR_TARGET, self.target_point, marker_r)
            lbl = self.font_bold.render("T", True, (255, 255, 255))
            self.screen.blit(lbl, (tp[0] - lbl.get_width() // 2, tp[1] - lbl.get_height() // 2))

    def draw_hud(self):
        # Top Header Bar
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, (0, 0, self.width, self.header_height))
        pygame.draw.line(self.screen, COLOR_PANEL_BORDER, (0, self.header_height), (self.width, self.header_height), 1)

        title = self.font_title.render("Interactive Funnel Algorithm", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(title, (int(20 * self.scale), int(10 * self.scale)))

        # Phase indicator badge
        phase_text = {
            STATE_DRAW_POLYGON: "1. DRAW POLYGON",
            STATE_SELECT_START: "2. PLACE START (S)",
            STATE_SELECT_TARGET: "2. PLACE TARGET (T)",
            STATE_SHOW_DUAL_TREE: "3. DUAL TREE",
            STATE_STEPPING: "4. FUNNEL STEPPING",
            STATE_FINISHED: "5. COMPLETE",
        }.get(self.state, "")
        badge_color = COLOR_DUAL_PATH if self.state == STATE_SHOW_DUAL_TREE else COLOR_TEXT_ACCENT
        phase_surf = self.font_bold.render(phase_text, True, badge_color)
        self.screen.blit(phase_surf, (int(20 * self.scale), int(38 * self.scale)))

        # Live Recording Mode indicator
        if self.record_mode:
            rec_badge = self.font_bold.render("● REC", True, (220, 38, 38))
            self.screen.blit(rec_badge, (int(210 * self.scale), int(38 * self.scale)))

        # Legend on top right
        if self.state == STATE_SHOW_DUAL_TREE:
            legend_items = [
                ("Dual Node", COLOR_DUAL_NODE),
                ("Dual Tree Edge", COLOR_DUAL_EDGE),
                ("Corridor Path (S→T)", COLOR_DUAL_PATH),
            ]
            lx = self.width - int(520 * self.scale)
            for name, col in legend_items:
                draw_aa_circle(self.screen, col, (lx, int(32 * self.scale)), 5.0 * self.scale)
                txt = self.font_small.render(name, True, COLOR_TEXT_SECONDARY)
                self.screen.blit(txt, (lx + int(12 * self.scale), int(24 * self.scale)))
                lx += int(160 * self.scale)
        else:
            legend_items = [
                ("Left Chain", COLOR_LEFT_CHAIN),
                ("Right Chain", COLOR_RIGHT_CHAIN),
                ("Apex", COLOR_APEX),
                ("Crossing Line", COLOR_CROSSING_LINE),
                ("Shortest Path", COLOR_PATH),
            ]
            lx = self.width - int(560 * self.scale)
            for name, col in legend_items:
                draw_aa_circle(self.screen, col, (lx, int(32 * self.scale)), 5.0 * self.scale)
                txt = self.font_small.render(name, True, COLOR_TEXT_SECONDARY)
                self.screen.blit(txt, (lx + int(10 * self.scale), int(24 * self.scale)))
                lx += int(112 * self.scale)

        # Bottom Panel Bar
        panel_y = self.height - self.footer_height
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, (0, panel_y, self.width, self.footer_height))
        pygame.draw.line(self.screen, COLOR_PANEL_BORDER, (0, panel_y), (self.width, panel_y), 1)

        # Status text (normal text below, not exaggerated)
        now = pygame.time.get_ticks()
        if self.warning_message and now < self.warning_timer:
            msg_surf = self.font_normal.render(f"Note: {self.warning_message}", True, COLOR_TEXT_WARN)
        else:
            msg_surf = self.font_normal.render(self.status_message, True, COLOR_TEXT_PRIMARY)
        self.screen.blit(msg_surf, (int(20 * self.scale), panel_y + int(12 * self.scale)))

        # Instructions / Controls Hint (including resolution, export, and recording shortcuts)
        res_info = f"{self.width}x{self.height}"
        rec_status = "ON" if self.record_mode else "OFF"
        controls = (
            f"[ENTER]: Next | [←]: Back | [P]: Export Grid | "
            f"[S]: Rec ({rec_status}) | [1/2/3]: Presets | [F]: Fullscreen | [+/-]: Res ({res_info})"
        )
        ctrl_surf = self.font_small.render(controls, True, COLOR_TEXT_SECONDARY)
        self.screen.blit(ctrl_surf, (int(20 * self.scale), panel_y + int(44 * self.scale)))

    def run(self):
        """Main game/application loop."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                    new_w = max(800, event.w)
                    new_h = max(600, event.h)
                    self.set_resolution(new_w, new_h)

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_click(event.pos, event.button)

                elif event.type == pygame.KEYDOWN:
                    self.handle_keydown(event.key)

            # Rendering (Crisp white theme)
            self.screen.fill(COLOR_BG)
            self.draw_polygon_and_triangulation()
            self.draw_dual_tree()
            self.draw_funnel_state()
            self.draw_start_and_target()
            self.draw_hud()

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()


def parse_args():
    parser = argparse.ArgumentParser(description="Interactive Funnel Algorithm (High Resolution)")
    parser.add_argument(
        "--res", type=str, default="1920x1080",
        help="Resolution preset: 1080p (1920x1080), 1440p (2560x1440), 4k (3840x2160), 900p (1600x900), 720p (1280x720), max/native, or WxH"
    )
    parser.add_argument("--width", type=int, default=None, help="Window width in pixels")
    parser.add_argument("--height", type=int, default=None, help="Window height in pixels")
    parser.add_argument("--fullscreen", action="store_true", help="Start in native fullscreen mode")
    parser.add_argument(
        "--record", nargs="?", const="", default=None,
        help="Enable step screenshot recording mode (optional: output folder path)"
    )
    parser.add_argument(
        "--screenshots", nargs="?", const="", default=None,
        help="Alias for --record (optional: output folder path)"
    )
    parser.add_argument(
        "--export-grid", type=int, choices=[1, 2, 3], default=None,
        help="Load preset (1, 2, or 3), export all step screenshots and grid_plot.png, then exit"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Resolution aliases
    aliases = {
        "1080p": (1920, 1080),
        "1080": (1920, 1080),
        "fhd": (1920, 1080),
        "1440p": (2560, 1440),
        "1440": (2560, 1440),
        "2k": (2560, 1440),
        "qhd": (2560, 1440),
        "4k": (3840, 2160),
        "2160p": (3840, 2160),
        "uhd": (3840, 2160),
        "900p": (1600, 900),
        "720p": (1280, 720),
        "hd": (1280, 720),
    }

    width, height = 1920, 1080

    if args.res:
        res_lower = args.res.strip().lower()
        if res_lower in aliases:
            width, height = aliases[res_lower]
        elif res_lower in ("max", "native", "desktop"):
            pygame.init()
            try:
                desktop_sizes = pygame.display.get_desktop_sizes()
                if desktop_sizes:
                    width, height = desktop_sizes[0]
            except Exception:
                pass
        elif "x" in res_lower:
            parts = res_lower.split("x")
            try:
                width, height = int(parts[0]), int(parts[1])
            except ValueError:
                pass

    if args.width:
        width = args.width
    if args.height:
        height = args.height

    rec_arg = args.record if args.record is not None else args.screenshots
    record_mode = rec_arg is not None
    rec_folder = rec_arg if (rec_arg and len(rec_arg) > 0) else None

    app = FunnelInteractiveApp(
        width=width, height=height, fullscreen=args.fullscreen,
        record_mode=record_mode, screenshot_folder=rec_folder
    )

    if args.export_grid is not None:
        app.load_preset(args.export_grid)
        cx, cy = app.width // 2, app.height // 2
        s = app.scale
        if args.export_grid == 1:
            app.handle_mouse_click((cx - int(220 * s), cy - int(140 * s)), 1)
            app.handle_mouse_click((cx + int(220 * s), cy + int(140 * s)), 1)
        elif args.export_grid == 2:
            app.handle_mouse_click((cx - int(280 * s), cy - int(160 * s)), 1)
            app.handle_mouse_click((cx + int(280 * s), cy - int(160 * s)), 1)
        elif args.export_grid == 3:
            app.handle_mouse_click((cx - int(280 * s), cy - int(150 * s)), 1)
            app.handle_mouse_click((cx - int(280 * s), cy + int(160 * s)), 1)

        grid_path = app.export_all_steps_grid(custom_folder=rec_folder)
        print(f"Exported all steps and generated grid plot at:\n  {grid_path}")
        sys.exit(0)

    app.run()
