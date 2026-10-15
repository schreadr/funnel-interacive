"""
Comprehensive test suite for computational geometry, triangulation,
and the step-by-step Funnel Algorithm.
"""

import unittest
import math
import os
from geometry import (
    dist, cross2d, is_simple_polygon, is_point_in_polygon,
    is_point_in_triangle, triangulate_ear_clipping,
    find_triangle_containing_point, find_triangle_corridor,
    extract_portals, get_dual_tree, get_dual_corridor_path
)
from funnel import FunnelAlgorithm


class TestGeometryAndFunnel(unittest.TestCase):

    def test_convex_polygon_direct_path(self):
        # A simple rectangle
        poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)]
        is_simple, msg = is_simple_polygon(poly)
        self.assertTrue(is_simple, msg)

        ccw_poly, triangles, diagonals = triangulate_ear_clipping(poly)
        self.assertEqual(len(triangles), 2)

        s = (1.0, 1.0)
        t = (9.0, 4.0)
        self.assertTrue(is_point_in_polygon(s, ccw_poly))
        self.assertTrue(is_point_in_polygon(t, ccw_poly))

        s_tri = find_triangle_containing_point(s, ccw_poly, triangles)
        t_tri = find_triangle_containing_point(t, ccw_poly, triangles)
        self.assertIsNotNone(s_tri)
        self.assertIsNotNone(t_tri)

        corridor = find_triangle_corridor(triangles, s_tri, t_tri)
        portals = extract_portals(ccw_poly, triangles, corridor, s, t)

        solver = FunnelAlgorithm(portals)
        final_state = solver.states[-1]
        self.assertTrue(final_state.is_complete)
        # Direct line from s to t in convex polygon
        expected_len = dist(s, t)
        self.assertAlmostEqual(final_state.path_length, expected_len, places=5)
        self.assertEqual(final_state.path_so_far, [s, t])

    def test_l_shaped_polygon(self):
        # L-shaped corridor
        poly = [
            (0.0, 0.0), (4.0, 0.0), (4.0, 4.0),
            (10.0, 4.0), (10.0, 8.0), (0.0, 8.0)
        ]
        is_simple, msg = is_simple_polygon(poly)
        self.assertTrue(is_simple, msg)

        ccw_poly, triangles, diagonals = triangulate_ear_clipping(poly)
        self.assertEqual(len(triangles), 4)

        # s in lower leg, t in upper-right leg
        s = (2.0, 1.0)
        t = (8.0, 6.0)
        self.assertTrue(is_point_in_polygon(s, ccw_poly))
        self.assertTrue(is_point_in_polygon(t, ccw_poly))

        s_tri = find_triangle_containing_point(s, ccw_poly, triangles)
        t_tri = find_triangle_containing_point(t, ccw_poly, triangles)
        self.assertIsNotNone(s_tri)
        self.assertIsNotNone(t_tri)

        corridor = find_triangle_corridor(triangles, s_tri, t_tri)
        portals = extract_portals(ccw_poly, triangles, corridor, s, t)

        solver = FunnelAlgorithm(portals)
        final_state = solver.states[-1]
        self.assertTrue(final_state.is_complete)
        path = final_state.path_so_far
        self.assertEqual(path[0], s)
        self.assertEqual(path[-1], t)
        # Path must bend around the reflex corner (4.0, 4.0)
        self.assertIn((4.0, 4.0), path)
        expected_len = dist(s, (4.0, 4.0)) + dist((4.0, 4.0), t)
        self.assertAlmostEqual(final_state.path_length, expected_len, places=5)

    def test_u_shaped_polygon(self):
        # U-shaped corridor: obstacles in the middle
        poly = [
            (0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (7.0, 10.0),
            (7.0, 3.0), (3.0, 3.0), (3.0, 10.0), (0.0, 10.0)
        ]
        is_simple, msg = is_simple_polygon(poly)
        self.assertTrue(is_simple, msg)

        ccw_poly, triangles, diagonals = triangulate_ear_clipping(poly)
        self.assertEqual(len(triangles), 6)

        s = (1.5, 8.0)
        t = (8.5, 8.0)
        self.assertTrue(is_point_in_polygon(s, ccw_poly))
        self.assertTrue(is_point_in_polygon(t, ccw_poly))

        s_tri = find_triangle_containing_point(s, ccw_poly, triangles)
        t_tri = find_triangle_containing_point(t, ccw_poly, triangles)
        self.assertIsNotNone(s_tri)
        self.assertIsNotNone(t_tri)

        corridor = find_triangle_corridor(triangles, s_tri, t_tri)
        portals = extract_portals(ccw_poly, triangles, corridor, s, t)

        solver = FunnelAlgorithm(portals)
        final_state = solver.states[-1]
        self.assertTrue(final_state.is_complete)
        path = final_state.path_so_far
        # Path must bend around (3.0, 3.0) and (7.0, 3.0)
        self.assertEqual(path, [s, (3.0, 3.0), (7.0, 3.0), t])
        expected_len = dist(s, (3.0, 3.0)) + dist((3.0, 3.0), (7.0, 3.0)) + dist((7.0, 3.0), t)
        self.assertAlmostEqual(final_state.path_length, expected_len, places=5)

    def test_stepping_forward_and_backward(self):
        poly = [
            (0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (7.0, 10.0),
            (7.0, 3.0), (3.0, 3.0), (3.0, 10.0), (0.0, 10.0)
        ]
        ccw_poly, triangles, _ = triangulate_ear_clipping(poly)
        s, t = (1.5, 8.0), (8.5, 8.0)
        s_tri = find_triangle_containing_point(s, ccw_poly, triangles)
        t_tri = find_triangle_containing_point(t, ccw_poly, triangles)
        corridor = find_triangle_corridor(triangles, s_tri, t_tri)
        portals = extract_portals(ccw_poly, triangles, corridor, s, t)

        solver = FunnelAlgorithm(portals)
        self.assertEqual(solver.current_step_index, 0)
        self.assertFalse(solver.is_finished)

        # Step forward until done
        count = 0
        while not solver.is_finished:
            solver.step_forward()
            count += 1

        self.assertEqual(solver.current_step_index, solver.total_steps - 1)
        self.assertTrue(solver.is_finished)

        # Step backward
        solver.step_backward()
        self.assertEqual(solver.current_step_index, solver.total_steps - 2)
        self.assertFalse(solver.is_finished)


    def test_same_triangle_start_and_target(self):
        poly = [(0.0, 0.0), (10.0, 0.0), (5.0, 10.0)]
        ccw_poly, triangles, _ = triangulate_ear_clipping(poly)
        s = (3.0, 2.0)
        t = (7.0, 2.0)
        s_tri = find_triangle_containing_point(s, ccw_poly, triangles)
        t_tri = find_triangle_containing_point(t, ccw_poly, triangles)
        self.assertEqual(s_tri, t_tri)
        corridor = find_triangle_corridor(triangles, s_tri, t_tri)
        portals = extract_portals(ccw_poly, triangles, corridor, s, t)
        solver = FunnelAlgorithm(portals)
        final_state = solver.states[-1]
        self.assertTrue(final_state.is_complete)
        self.assertEqual(final_state.path_so_far, [s, t])
        self.assertAlmostEqual(final_state.path_length, dist(s, t), places=5)

    def test_s_shaped_corridor(self):
        # S-curve polygon
        poly = [
            (0.0, 0.0), (12.0, 0.0), (12.0, 4.0), (4.0, 4.0),
            (4.0, 8.0), (12.0, 8.0), (12.0, 12.0), (0.0, 12.0),
            (0.0, 8.0), (0.0, 4.0)
        ]
        # Clean colinear boundary
        poly_clean = [
            (0.0, 0.0), (12.0, 0.0), (12.0, 4.0), (4.0, 4.0),
            (4.0, 8.0), (12.0, 8.0), (12.0, 12.0), (0.0, 12.0)
        ]
        is_simple, msg = is_simple_polygon(poly_clean)
        self.assertTrue(is_simple, msg)

        ccw_poly, triangles, _ = triangulate_ear_clipping(poly_clean)
        s = (10.0, 10.0)
        t = (10.0, 2.0)

        s_tri = find_triangle_containing_point(s, ccw_poly, triangles)
        t_tri = find_triangle_containing_point(t, ccw_poly, triangles)
        corridor = find_triangle_corridor(triangles, s_tri, t_tri)
        portals = extract_portals(ccw_poly, triangles, corridor, s, t)

        solver = FunnelAlgorithm(portals)
        final_state = solver.states[-1]
        self.assertTrue(final_state.is_complete)
        # Should bend around (4.0, 8.0) and (4.0, 4.0)
        path = final_state.path_so_far
        self.assertIn((4.0, 8.0), path)
        self.assertIn((4.0, 4.0), path)
    def test_dual_tree_construction(self):
        poly = [
            (0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (7.0, 10.0),
            (7.0, 3.0), (3.0, 3.0), (3.0, 10.0), (0.0, 10.0)
        ]
        ccw_poly, triangles, _ = triangulate_ear_clipping(poly)
        centroids, tree_edges = get_dual_tree(ccw_poly, triangles)
        # Dual graph of simple polygon triangulation is a tree: V = num_triangles, E = num_triangles - 1
        self.assertEqual(len(centroids), len(triangles))
        self.assertEqual(len(tree_edges), len(triangles) - 1)

        s, t = (1.5, 8.0), (8.5, 8.0)
        s_tri = find_triangle_containing_point(s, ccw_poly, triangles)
        t_tri = find_triangle_containing_point(t, ccw_poly, triangles)
        corridor = find_triangle_corridor(triangles, s_tri, t_tri)
        dual_path = get_dual_corridor_path(corridor, centroids, s, t)
        self.assertEqual(dual_path[0], s)
        self.assertEqual(dual_path[-1], t)
        self.assertEqual(len(dual_path), len(corridor) + 2)

    def test_crossing_step_recorded_before_apex_move(self):
        poly = [
            (0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (7.0, 10.0),
            (7.0, 3.0), (3.0, 3.0), (3.0, 10.0), (0.0, 10.0)
        ]
        ccw_poly, triangles, _ = triangulate_ear_clipping(poly)
        s, t = (1.5, 8.0), (8.5, 8.0)
        s_tri = find_triangle_containing_point(s, ccw_poly, triangles)
        t_tri = find_triangle_containing_point(t, ccw_poly, triangles)
        corridor = find_triangle_corridor(triangles, s_tri, t_tri)
        portals = extract_portals(ccw_poly, triangles, corridor, s, t)
        solver = FunnelAlgorithm(portals)

        crossing_indices = [
            i for i, st in enumerate(solver.states) if st.is_crossing_step
        ]
        # U-shaped corridor has 2 reflex corners that must be crossed
        self.assertGreaterEqual(len(crossing_indices), 2)

        for c_idx in crossing_indices:
            c_state = solver.states[c_idx]
            self.assertIsNotNone(c_state.crossing_line)
            self.assertIsNotNone(c_state.crossed_segment)
            self.assertIsNotNone(c_state.crossing_point)
            # The next step should move apex to that corner
            next_state = solver.states[c_idx + 1]
            self.assertEqual(next_state.apex, c_state.crossing_point)

    def test_export_utils_and_grid_plot(self):
        import pygame
        import tempfile
        from export_utils import StepRecorder, capture_canvas, generate_grid_plot

        pygame.init()
        screen = pygame.Surface((400, 300))
        screen.fill((255, 255, 255))
        cropped = capture_canvas(screen, header_height=40, footer_height=50)
        self.assertEqual(cropped.get_size(), (400, 210))

        with tempfile.TemporaryDirectory() as tmp_dir:
            recorder = StepRecorder(base_folder=tmp_dir)
            p1 = recorder.capture_step(screen, 40, 50, "step0", "Step 0: Initial")
            p2 = recorder.capture_step(screen, 40, 50, "step1", "Step 1: Complete")
            self.assertTrue(os.path.exists(p1))
            self.assertTrue(os.path.exists(p2))

            grid_path = recorder.build_grid_plot(title="Unit Test Grid", ncols=2)
            self.assertTrue(os.path.exists(grid_path))
            self.assertGreater(os.path.getsize(grid_path), 1000)

    def test_direct_recording_app_workflow(self):
        """Tests the interactive direct recording, step popping, and column prompt modal flow."""
        import pygame
        import tempfile
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        from main import (
            FunnelInteractiveApp, STATE_DRAW_POLYGON, STATE_SELECT_START,
            STATE_SELECT_TARGET, STATE_SHOW_DUAL_TREE, STATE_STEPPING,
            STATE_FINISHED, STATE_PROMPT_COLUMNS
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            app = FunnelInteractiveApp(
                width=1280, height=720, record_mode=True, screenshot_folder=tmp_dir
            )
            self.assertEqual(app.state, STATE_DRAW_POLYGON)

            # 1. Draw a convex polygon via clicks
            app.handle_mouse_click((200, 200), 1)
            app.handle_mouse_click((800, 200), 1)
            app.handle_mouse_click((800, 500), 1)
            app.handle_mouse_click((200, 500), 1)
            app.handle_mouse_click((200, 500), 3)  # Right-click to close
            self.assertEqual(app.state, STATE_SELECT_START)

            # 2. Select S and T points
            app.handle_mouse_click((250, 250), 1)  # S
            self.assertEqual(app.state, STATE_SELECT_TARGET)
            app.handle_mouse_click((750, 450), 1)  # T
            self.assertEqual(app.state, STATE_SHOW_DUAL_TREE)

            # Step 0 (Dual Tree) recorded directly
            self.assertEqual(len(app.recorder.recorded_steps), 1)

            # 3. Advance to Funnel stepping (Step 1 recorded)
            app.handle_keydown(pygame.K_RETURN)
            self.assertEqual(app.state, STATE_STEPPING)
            self.assertEqual(len(app.recorder.recorded_steps), 2)

            # 4. Step backward: verify last step popped
            app.handle_keydown(pygame.K_BACKSPACE)
            self.assertEqual(app.state, STATE_SHOW_DUAL_TREE)
            self.assertEqual(len(app.recorder.recorded_steps), 1)

            # Advance back to stepping
            app.handle_keydown(pygame.K_RETURN)
            self.assertEqual(app.state, STATE_STEPPING)
            self.assertEqual(len(app.recorder.recorded_steps), 2)

            # 5. Step until finished
            while app.funnel_solver and not app.funnel_solver.is_finished:
                app.handle_keydown(pygame.K_RETURN)

            # Verify prompt for columns opened automatically upon completion
            self.assertEqual(app.state, STATE_PROMPT_COLUMNS)
            self.assertGreaterEqual(len(app.recorder.recorded_steps), 2)

            # 6. Select 3 columns
            app.handle_keydown(pygame.K_3)
            self.assertEqual(app.columns_input_str, "3")

            # 7. Confirm export
            app.handle_keydown(pygame.K_RETURN)
            self.assertEqual(app.state, STATE_FINISHED)

            # Verify compiled grid plot
            grid_file = os.path.join(tmp_dir, "grid_plot.png")
            self.assertTrue(os.path.exists(grid_file))
            self.assertGreater(os.path.getsize(grid_file), 1000)

            # 8. Re-open export prompt using 'E'
            app.handle_keydown(pygame.K_e)
            self.assertEqual(app.state, STATE_PROMPT_COLUMNS)

            # Test Arrow Keys (+/-)
            app.handle_keydown(pygame.K_UP)
            self.assertEqual(app.columns_input_str, "4")
            app.handle_keydown(pygame.K_DOWN)
            self.assertEqual(app.columns_input_str, "3")

            # Test Cancel via ESC
            app.handle_keydown(pygame.K_ESCAPE)
            self.assertEqual(app.state, STATE_FINISHED)

            # 9. Re-open via 'P' and test mouse click on Pill 5 and Export button
            app.handle_keydown(pygame.K_p)
            self.assertEqual(app.state, STATE_PROMPT_COLUMNS)

            cx = app.width // 2
            s = app.scale
            modal_rect_y = app.height // 2 - int(240 * s) // 2
            pill_w = int(38 * s)
            gap = int(10 * s)
            total_pills_w = 8 * pill_w + 7 * gap
            pills_x0 = cx - total_pills_w // 2
            pills_y = modal_rect_y + int(90 * s)
            p5_x = pills_x0 + 4 * (pill_w + gap) + pill_w // 2
            p5_y = pills_y + int(10 * s)
            app.handle_mouse_click((p5_x, p5_y), 1)
            self.assertEqual(app.columns_input_str, "5")

            # Click export button
            btn_y = modal_rect_y + int(165 * s) + int(10 * s)
            btn_exp_w = int(210 * s)
            btn_exp_x = cx - btn_exp_w - int(10 * s) + btn_exp_w // 2
            app.handle_mouse_click((btn_exp_x, btn_y), 1)
            self.assertEqual(app.state, STATE_FINISHED)
            self.assertEqual(app.default_cols, 5)


if __name__ == '__main__':
    unittest.main()




