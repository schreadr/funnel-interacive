"""
Interactive Funnel Algorithm Application.
Allows users to draw a polygon, view automatic triangulation,
place start (S) and target (T) points, and step through the Funnel Algorithm
using the ENTER key.
"""

from __future__ import annotations
import sys
import pygame
from typing import List, Tuple, Optional
from geometry import (
    Point, is_simple_polygon, is_point_in_polygon,
    triangulate_ear_clipping, find_triangle_containing_point,
    find_triangle_corridor, extract_portals, dist,
    segments_intersect
)
from funnel import FunnelAlgorithm, FunnelState

# --- Color Palette (Modern Dark Theme) ---
COLOR_BG = (24, 24, 37)              # Dark slate background
COLOR_PANEL_BG = (30, 30, 46)        # HUD / Panel bar
COLOR_PANEL_BORDER = (49, 50, 68)    # Border
COLOR_TEXT_PRIMARY = (205, 214, 244) # Crisp off-white text
COLOR_TEXT_SECONDARY = (166, 173, 200) # Dim text
COLOR_TEXT_ACCENT = (137, 180, 250)  # Blue highlight text
COLOR_TEXT_WARN = (243, 139, 168)    # Warning pink/red

COLOR_POLY_EDGE = (137, 180, 250)    # Blue polygon outline
COLOR_POLY_FILL = (30, 40, 65, 120)  # Semi-transparent polygon interior
COLOR_VERTEX = (180, 190, 254)       # Vertex dots
COLOR_RUBBER_BAND = (116, 199, 236)  # Dynamic mouse segment

COLOR_TRI_DIAG = (88, 91, 112)       # Triangulation diagonals
COLOR_CORRIDOR_FILL = (249, 226, 175, 55) # Translucent amber triangle strip
COLOR_PORTAL = (147, 153, 178)       # Inactive portals
COLOR_ACTIVE_PORTAL = (249, 226, 175) # Bright yellow active portal

COLOR_START = (166, 227, 161)        # Green for S
COLOR_TARGET = (243, 139, 168)       # Red for T
COLOR_APEX = (250, 179, 135)         # Warm peach/orange for apex
COLOR_LEFT_CHAIN = (137, 220, 235)   # Cyan for left funnel chain
COLOR_RIGHT_CHAIN = (166, 227, 161)  # Light green for right funnel chain
COLOR_PATH = (245, 194, 231)         # Soft pink/magenta for shortest path
COLOR_PATH_GLOW = (250, 179, 135)    # Orange glow for shortest path

# Application States
STATE_DRAW_POLYGON = "DRAW_POLYGON"
STATE_SELECT_START = "SELECT_START"
STATE_SELECT_TARGET = "SELECT_TARGET"
STATE_STEPPING = "STEPPING"
STATE_FINISHED = "FINISHED"


class FunnelInteractiveApp:

    def __init__(self, width: int = 1200, height: int = 800):
        pygame.init()
        pygame.display.set_caption("Shortest Paths in Simple Polygons — Interactive Funnel Algorithm")
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

        # Fonts
        self.font_title = pygame.font.SysFont("DejaVu Sans", 20, bold=True)
        self.font_bold = pygame.font.SysFont("DejaVu Sans", 16, bold=True)
        self.font_normal = pygame.font.SysFont("DejaVu Sans", 14)
        self.font_small = pygame.font.SysFont("DejaVu Sans", 12)

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

        self.funnel_solver: Optional[FunnelAlgorithm] = None
        self.status_message = "Click to add polygon vertices. Right-click to close polygon."
        self.warning_message: Optional[str] = None
        self.warning_timer = 0

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
        self.funnel_solver = None
        self.status_message = "Click to add polygon vertices. Right-click to close polygon."
        self.warning_message = None

    def load_preset(self, preset_id: int):
        """Loads a built-in demo polygon for immediate testing."""
        self.reset()
        w, h = self.width, self.height
        cx, cy = w // 2, h // 2

        if preset_id == 1:
            # L-shaped corridor
            self.vertices = [
                (cx - 300, cy - 200),
                (cx - 50, cy - 200),
                (cx - 50, cy + 50),
                (cx + 300, cy + 50),
                (cx + 300, cy + 220),
                (cx - 300, cy + 220),
            ]
        elif preset_id == 2:
            # U-shaped polygon
            self.vertices = [
                (cx - 350, cy - 220),
                (cx - 150, cy - 220),
                (cx - 150, cy + 100),
                (cx + 150, cy + 100),
                (cx + 150, cy - 220),
                (cx + 350, cy - 220),
                (cx + 350, cy + 250),
                (cx - 350, cy + 250),
            ]
        elif preset_id == 3:
            # Spiral / S-shaped polygon
            self.vertices = [
                (cx - 350, cy - 220),
                (cx + 350, cy - 220),
                (cx + 350, cy - 60),
                (cx - 150, cy - 60),
                (cx - 150, cy + 80),
                (cx + 350, cy + 80),
                (cx + 350, cy + 240),
                (cx - 350, cy + 240),
                (cx - 350, cy + 100),
                (cx + 150, cy + 100),
                (cx + 150, cy - 80),
                (cx - 350, cy - 80),
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
        self.status_message = "Polygon triangulated! Click inside polygon to place Start point (S)."
        self.warning_message = None

    def set_warning(self, msg: str):
        self.warning_message = msg
        self.warning_timer = pygame.time.get_ticks() + 4000

    def handle_mouse_click(self, pos: Point, button: int):
        x, y = float(pos[0]), float(pos[1])

        # Ignore clicks in header or footer panel
        if y < 65 or y > self.height - 75:
            return

        if self.state == STATE_DRAW_POLYGON:
            if button == 1:  # Left-click: Add vertex
                # Optional check: ensure new segment doesn't self-intersect
                if len(self.vertices) >= 2:
                    new_seg = (self.vertices[-1], (x, y))
                    for i in range(len(self.vertices) - 2):
                        prev_seg = (self.vertices[i], self.vertices[i + 1])
                        if segments_intersect(new_seg[0], new_seg[1], prev_seg[0], prev_seg[1]):
                            self.set_warning("New edge crosses an existing edge! Click elsewhere.")
                            return

                self.vertices.append((x, y))
                self.status_message = f"Added vertex {len(self.vertices)}. Right-click when done to close."
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
                self.status_message = "Start point S selected! Now click inside polygon to place Target (T)."

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

                # Find corridor and portals
                self.corridor = find_triangle_corridor(self.triangles, self.start_tri, self.target_tri)
                self.portals = extract_portals(
                    self.ccw_poly, self.triangles, self.corridor, self.start_point, self.target_point
                )
                self.funnel_solver = FunnelAlgorithm(self.portals)

                self.state = STATE_STEPPING
                self.status_message = (
                    f"Corridor identified ({len(self.corridor)} triangles, {len(self.portals)} portals). "
                    f"Press ENTER to execute step 1!"
                )

    def handle_keydown(self, key: int):
        if key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()

        elif key == pygame.K_r:
            self.reset()

        elif key in (pygame.K_1, pygame.K_2, pygame.K_3):
            preset_map = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3}
            self.load_preset(preset_map[key])

        elif key in (pygame.K_u, pygame.K_BACKSPACE):
            if self.state == STATE_DRAW_POLYGON and self.vertices:
                self.vertices.pop()
                self.status_message = f"Removed last vertex. {len(self.vertices)} vertices remaining."
            elif self.state in (STATE_STEPPING, STATE_FINISHED) and self.funnel_solver:
                self.funnel_solver.step_backward()
                self.state = STATE_STEPPING
                curr = self.funnel_solver.current_state
                self.status_message = f"[Step {curr.step_number}/{curr.total_steps - 1}] {curr.description}"

        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.state == STATE_STEPPING and self.funnel_solver:
                if not self.funnel_solver.is_finished:
                    new_st = self.funnel_solver.step_forward()
                    if self.funnel_solver.is_finished:
                        self.state = STATE_FINISHED
                        self.status_message = (
                            f"[COMPLETE] {new_st.description} | Press 'R' to reset and draw a new polygon."
                        )
                    else:
                        self.status_message = (
                            f"[Step {new_st.step_number}/{new_st.total_steps - 1}] {new_st.description} "
                            f"(Press ENTER to continue)"
                        )
                else:
                    self.state = STATE_FINISHED
            elif self.state == STATE_FINISHED:
                self.status_message = (
                    f"[COMPLETE] Path length: {self.funnel_solver.current_state.path_length:.2f}. "
                    f"Press 'R' to draw a new polygon."
                )

    # --- RENDER METHODS ---

    def draw_polygon_and_triangulation(self):
        # Draw translucent polygon fill
        if len(self.ccw_poly) >= 3 and self.state != STATE_DRAW_POLYGON:
            poly_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            int_pts = [(int(p[0]), int(p[1])) for p in self.ccw_poly]
            pygame.draw.polygon(poly_surf, COLOR_POLY_FILL, int_pts)

            # Highlight corridor triangles if available
            if self.corridor and self.triangles:
                for tri_idx in self.corridor:
                    tri = self.triangles[tri_idx]
                    t_pts = [
                        (int(self.ccw_poly[tri[0]][0]), int(self.ccw_poly[tri[0]][1])),
                        (int(self.ccw_poly[tri[1]][0]), int(self.ccw_poly[tri[1]][1])),
                        (int(self.ccw_poly[tri[2]][0]), int(self.ccw_poly[tri[2]][1])),
                    ]
                    pygame.draw.polygon(poly_surf, COLOR_CORRIDOR_FILL, t_pts)

            self.screen.blit(poly_surf, (0, 0))

        # Draw triangulation diagonals
        if self.diagonals and self.state != STATE_DRAW_POLYGON:
            for d in self.diagonals:
                p1 = (int(d[0][0]), int(d[0][1]))
                p2 = (int(d[1][0]), int(d[1][1]))
                pygame.draw.line(self.screen, COLOR_TRI_DIAG, p1, p2, 1)

        # Draw polygon boundary edges
        active_poly = self.ccw_poly if len(self.ccw_poly) >= 3 else self.vertices
        n = len(active_poly)
        if n >= 2:
            for i in range(n - 1):
                p1 = (int(active_poly[i][0]), int(active_poly[i][1]))
                p2 = (int(active_poly[i + 1][0]), int(active_poly[i + 1][1]))
                pygame.draw.line(self.screen, COLOR_POLY_EDGE, p1, p2, 2)

            if self.state != STATE_DRAW_POLYGON and n >= 3:
                # Closing edge
                p1 = (int(active_poly[-1][0]), int(active_poly[-1][1]))
                p2 = (int(active_poly[0][0]), int(active_poly[0][1]))
                pygame.draw.line(self.screen, COLOR_POLY_EDGE, p1, p2, 2)

        # Draw rubber-band line while drawing
        if self.state == STATE_DRAW_POLYGON and n >= 1:
            mouse_pos = pygame.mouse.get_pos()
            last_pt = (int(active_poly[-1][0]), int(active_poly[-1][1]))
            pygame.draw.line(self.screen, COLOR_RUBBER_BAND, last_pt, mouse_pos, 1)

        # Draw vertices
        for i, pt in enumerate(active_poly):
            ip = (int(pt[0]), int(pt[1]))
            pygame.draw.circle(self.screen, COLOR_BG, ip, 6)
            pygame.draw.circle(self.screen, COLOR_VERTEX, ip, 4)

    def draw_funnel_state(self):
        if not self.funnel_solver or self.state not in (STATE_STEPPING, STATE_FINISHED):
            return

        curr: FunnelState = self.funnel_solver.current_state

        # Draw all portals in corridor
        for i, (l_pt, r_pt) in enumerate(self.portals):
            if l_pt == r_pt:
                continue  # Skip s and t degenerate portals
            p1 = (int(l_pt[0]), int(l_pt[1]))
            p2 = (int(r_pt[0]), int(r_pt[1]))
            is_active = (i == curr.portal_idx)
            color = COLOR_ACTIVE_PORTAL if is_active else COLOR_PORTAL
            width = 3 if is_active else 1
            pygame.draw.line(self.screen, color, p1, p2, width)

        # Draw Funnel Left Chain
        if len(curr.left_chain) >= 2:
            pts = [(int(p[0]), int(p[1])) for p in curr.left_chain]
            pygame.draw.lines(self.screen, COLOR_LEFT_CHAIN, False, pts, 3)
            for p in curr.left_chain[1:]:
                pygame.draw.circle(self.screen, COLOR_LEFT_CHAIN, (int(p[0]), int(p[1])), 5)

        # Draw Funnel Right Chain
        if len(curr.right_chain) >= 2:
            pts = [(int(p[0]), int(p[1])) for p in curr.right_chain]
            pygame.draw.lines(self.screen, COLOR_RIGHT_CHAIN, False, pts, 3)
            for p in curr.right_chain[1:]:
                pygame.draw.circle(self.screen, COLOR_RIGHT_CHAIN, (int(p[0]), int(p[1])), 5)

        # Draw Shortest Path so far
        if len(curr.path_so_far) >= 2:
            pts = [(int(p[0]), int(p[1])) for p in curr.path_so_far]
            # Outer glow
            pygame.draw.lines(self.screen, COLOR_PATH_GLOW, False, pts, 6)
            # Core path line
            pygame.draw.lines(self.screen, COLOR_PATH, False, pts, 3)
            for p in curr.path_so_far:
                pygame.draw.circle(self.screen, COLOR_PATH_GLOW, (int(p[0]), int(p[1])), 6)
                pygame.draw.circle(self.screen, COLOR_PATH, (int(p[0]), int(p[1])), 3)

        # Draw Funnel Apex
        apex_int = (int(curr.apex[0]), int(curr.apex[1]))
        pygame.draw.circle(self.screen, COLOR_APEX, apex_int, 9)
        pygame.draw.circle(self.screen, (255, 255, 255), apex_int, 4)
        apex_lbl = self.font_bold.render("Apex", True, COLOR_APEX)
        self.screen.blit(apex_lbl, (apex_int[0] + 12, apex_int[1] - 8))

    def draw_start_and_target(self):
        if self.start_point:
            sp = (int(self.start_point[0]), int(self.start_point[1]))
            pygame.draw.circle(self.screen, COLOR_BG, sp, 10)
            pygame.draw.circle(self.screen, COLOR_START, sp, 8)
            lbl = self.font_bold.render("S", True, (0, 0, 0))
            self.screen.blit(lbl, (sp[0] - lbl.get_width() // 2, sp[1] - lbl.get_height() // 2))

        if self.target_point:
            tp = (int(self.target_point[0]), int(self.target_point[1]))
            pygame.draw.circle(self.screen, COLOR_BG, tp, 10)
            pygame.draw.circle(self.screen, COLOR_TARGET, tp, 8)
            lbl = self.font_bold.render("T", True, (0, 0, 0))
            self.screen.blit(lbl, (tp[0] - lbl.get_width() // 2, tp[1] - lbl.get_height() // 2))

    def draw_hud(self):
        # Top Header Bar
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, (0, 0, self.width, 65))
        pygame.draw.line(self.screen, COLOR_PANEL_BORDER, (0, 65), (self.width, 65), 1)

        title = self.font_title.render("Interactive Funnel Algorithm", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(title, (20, 10))

        # Phase indicator badge
        phase_text = {
            STATE_DRAW_POLYGON: "1. DRAW POLYGON",
            STATE_SELECT_START: "2. PLACE START (S)",
            STATE_SELECT_TARGET: "2. PLACE TARGET (T)",
            STATE_STEPPING: "3. FUNNEL STEPPING",
            STATE_FINISHED: "4. FINISHED",
        }.get(self.state, "")
        phase_surf = self.font_bold.render(phase_text, True, COLOR_TEXT_ACCENT)
        self.screen.blit(phase_surf, (20, 38))

        # Legend on top right
        legend_items = [
            ("Left Chain", COLOR_LEFT_CHAIN),
            ("Right Chain", COLOR_RIGHT_CHAIN),
            ("Apex", COLOR_APEX),
            ("Shortest Path", COLOR_PATH_GLOW),
        ]
        lx = self.width - 450
        for name, col in legend_items:
            pygame.draw.circle(self.screen, col, (lx, 32), 6)
            txt = self.font_small.render(name, True, COLOR_TEXT_SECONDARY)
            self.screen.blit(txt, (lx + 10, 25))
            lx += 105

        # Bottom Panel Bar
        panel_y = self.height - 75
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, (0, panel_y, self.width, 75))
        pygame.draw.line(self.screen, COLOR_PANEL_BORDER, (0, panel_y), (self.width, panel_y), 1)

        # Status text or Warning
        now = pygame.time.get_ticks()
        if self.warning_message and now < self.warning_timer:
            msg_surf = self.font_bold.render(f"⚠ {self.warning_message}", True, COLOR_TEXT_WARN)
        else:
            msg_surf = self.font_normal.render(self.status_message, True, COLOR_TEXT_PRIMARY)
        self.screen.blit(msg_surf, (20, panel_y + 12))

        # Instructions / Controls Hint
        controls = "[ENTER]: Step Forward | [←/Backspace]: Step Back | [R]: Reset | [1/2/3]: Presets | [ESC]: Quit"
        ctrl_surf = self.font_small.render(controls, True, COLOR_TEXT_SECONDARY)
        self.screen.blit(ctrl_surf, (20, panel_y + 44))

    def run(self):
        """Main game/application loop."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.VIDEORESIZE:
                    self.width = max(800, event.w)
                    self.height = max(600, event.h)
                    self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_click(event.pos, event.button)

                elif event.type == pygame.KEYDOWN:
                    self.handle_keydown(event.key)

            # Rendering
            self.screen.fill(COLOR_BG)
            self.draw_polygon_and_triangulation()
            self.draw_funnel_state()
            self.draw_start_and_target()
            self.draw_hud()

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()


if __name__ == "__main__":
    app = FunnelInteractiveApp()
    app.run()

