"""
Export and Grid Plot Utilities for the Interactive Funnel Algorithm.
Captures clean screenshots of the drawing canvas (excluding UI header/footer panels)
and arranges step-by-step screenshots into a comprehensive grid plot with a unified legend.
"""

from __future__ import annotations
import os
import math
import datetime
from typing import List, Tuple, Optional
import pygame

# Set temporary cache for matplotlib to prevent permission warnings
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib_cache")

import matplotlib
matplotlib.use("Agg")  # Use non-GUI Agg backend for thread-safe in-memory rendering
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import matplotlib.image as mpimg


def capture_canvas(screen: pygame.Surface, header_height: int, footer_height: int) -> pygame.Surface:
    """
    Crops and returns ONLY the active drawing canvas of the application,
    excluding the top header and bottom footer HUD panels.
    """
    width, height = screen.get_size()
    canvas_h = max(10, height - header_height - footer_height)
    canvas_rect = pygame.Rect(0, header_height, width, canvas_h)
    return screen.subsurface(canvas_rect).copy()


def save_canvas_screenshot(
    screen: pygame.Surface,
    header_height: int,
    footer_height: int,
    filepath: str
) -> str:
    """Saves a cropped screenshot of the drawing canvas to a file."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    canvas = capture_canvas(screen, header_height, footer_height)
    pygame.image.save(canvas, filepath)
    return filepath


def generate_grid_plot(
    step_records: List[Tuple[str, str]],
    output_path: str,
    main_title: str = "Funnel Algorithm — Step-by-Step Shortest Path Execution",
    ncols: Optional[int] = None
) -> str:
    """
    Combines step screenshot images into an publication-quality grid plot with a unified legend.

    Args:
        step_records: List of (image_file_path, step_title_or_caption)
        output_path: Destination filepath for the compiled grid PNG
        main_title: Main title rendered at the top of the grid figure
        ncols: Optional specific number of columns for the grid layout

    Returns:
        The absolute path to the generated grid plot image.
    """
    n_steps = len(step_records)
    if n_steps == 0:
        return ""

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Determine grid dimensions (custom or dynamic)
    if ncols is not None and ncols >= 1:
        ncols = max(1, min(ncols, 12))
        nrows = math.ceil(n_steps / ncols)
    else:
        if n_steps == 1:
            ncols, nrows = 1, 1
        elif n_steps == 2:
            ncols, nrows = 2, 1
        elif n_steps in (3, 4):
            ncols, nrows = 2, 2
        elif n_steps in (5, 6):
            ncols, nrows = 3, 2
        elif n_steps in (7, 8):
            ncols, nrows = 4, 2
        elif n_steps in (9, 10, 11, 12):
            ncols, nrows = 4, 3
        elif n_steps in (13, 14, 15, 16):
            ncols, nrows = 4, 4
        else:
            ncols = 4
            nrows = math.ceil(n_steps / ncols)

    cell_w = 4.8
    cell_h = 3.2
    fig_w = cell_w * ncols
    fig_h = cell_h * nrows + 1.4

    fig, axes = plt.subplots(nrows, ncols, figsize=(fig_w, fig_h), dpi=180)
    fig.patch.set_facecolor('#ffffff')
    fig.suptitle(main_title, fontsize=15, fontweight='bold', color='#141821', y=0.985)

    if nrows == 1 and ncols == 1:
        axes_list = [axes]
    elif nrows == 1 or ncols == 1:
        axes_list = list(axes)
    else:
        axes_list = list(axes.flat)

    for i in range(len(axes_list)):
        ax = axes_list[i]
        if i < n_steps:
            img_path, caption = step_records[i]
            if os.path.exists(img_path):
                img = mpimg.imread(img_path)
                ax.imshow(img)
            else:
                ax.text(0.5, 0.5, f"Image not found:\n{os.path.basename(img_path)}",
                        ha='center', va='center', color='red')

            ax.set_title(caption, fontsize=9.5, fontweight='bold', color='#1e293b', pad=6)

            # Elegant thin border
            for spine in ax.spines.values():
                spine.set_edgecolor('#dee2e6')
                spine.set_linewidth(1.0)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            # Hide unused grid cells
            ax.axis('off')

    # Unified Color Legend
    legend_elements = [
        Line2D([0], [0], color='#1e40af', lw=2.5, label='Polygon Boundary'),
        Line2D([0], [0], color='#c3cdda', lw=1.5, linestyle='--', label='Diagonals'),
        Patch(facecolor='#fef3c7', edgecolor='#e5e7eb', label='Corridor Triangles'),
        Line2D([0], [0], marker='o', color='none', markerfacecolor='#0ea5e9', markeredgecolor='#0ea5e9', markersize=6, label='Dual Nodes'),
        Line2D([0], [0], color='#d97706', lw=2.5, label='Corridor Path (S→T)'),
        Line2D([0], [0], color='#0284c7', lw=3.5, label='Left Chain'),
        Line2D([0], [0], color='#16a34a', lw=3.5, label='Right Chain'),
        Line2D([0], [0], marker='o', color='none', markerfacecolor='#ea580c', markeredgecolor='#ea580c', markersize=7, label='Apex'),
        Line2D([0], [0], color='#e11d48', lw=2, linestyle='--', label='Crossing Sightline'),
        Line2D([0], [0], color='#be185d', lw=3, label='Crossed Segment'),
        Line2D([0], [0], color='#dc2626', lw=2.2, label='Shortest Path'),
        Line2D([0], [0], marker='o', color='none', markerfacecolor='#16a34a', markeredgecolor='#16a34a', markersize=7.5, label='Start (S)'),
        Line2D([0], [0], marker='o', color='none', markerfacecolor='#dc2626', markeredgecolor='#dc2626', markersize=7.5, label='Target (T)'),
    ]

    fig.legend(
        handles=legend_elements,
        loc='lower center',
        ncol=min(len(legend_elements), 7),
        fontsize=8.5,
        frameon=True,
        facecolor='#f8f9fb',
        edgecolor='#dee2e6',
        bbox_to_anchor=(0.5, 0.012)
    )

    # Adjust layout to preserve header and footer spacing
    plt.tight_layout(rect=[0.01, 0.065, 0.99, 0.965])
    plt.savefig(output_path, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)

    return os.path.abspath(output_path)


class StepRecorder:
    """Manages screenshot recording for algorithm steps and grid plot generation."""

    def __init__(self, base_folder: Optional[str] = None, auto_record: bool = False):
        self.auto_record = auto_record
        self.base_folder = base_folder
        if base_folder:
            self.folder = base_folder
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.folder = os.path.join("screenshots", f"run_{timestamp}")

        self.recorded_steps: List[Tuple[str, str]] = []
        self._step_counter = 0

    def reset_session(self, new_folder: Optional[str] = None):
        """Starts a fresh recording session."""
        if new_folder:
            self.folder = new_folder
        elif self.base_folder:
            self.folder = self.base_folder
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.folder = os.path.join("screenshots", f"run_{timestamp}")
        self.recorded_steps.clear()
        self._step_counter = 0

    def capture_step(
        self,
        screen: pygame.Surface,
        header_height: int,
        footer_height: int,
        step_tag: str,
        caption: str
    ) -> str:
        """Captures and saves a single step screenshot."""
        os.makedirs(self.folder, exist_ok=True)
        filename = f"step_{self._step_counter:02d}_{step_tag}.png"
        filepath = os.path.join(self.folder, filename)
        save_canvas_screenshot(screen, header_height, footer_height, filepath)
        self.recorded_steps.append((filepath, caption))
        self._step_counter += 1
        return filepath

    def pop_last_step(self) -> Optional[Tuple[str, str]]:
        """Removes the last captured step record (e.g. on step backward)."""
        if self.recorded_steps:
            last_entry = self.recorded_steps.pop()
            path, _ = last_entry
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
            self._step_counter = max(0, self._step_counter - 1)
            return last_entry
        return None

    def build_grid_plot(
        self,
        title: str = "Funnel Algorithm — Step-by-Step Shortest Path Execution",
        ncols: Optional[int] = None
    ) -> str:
        """Compiles all recorded steps into grid_plot.png."""
        if not self.recorded_steps:
            return ""
        grid_file = os.path.join(self.folder, "grid_plot.png")
        return generate_grid_plot(self.recorded_steps, grid_file, main_title=title, ncols=ncols)

