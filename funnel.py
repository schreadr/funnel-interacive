"""
Step-by-step Funnel Algorithm implementation for finding Euclidean shortest paths
in simple polygons given a sequence of portals (sleeve of triangles).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from geometry import Point, cross2d, dist, EPSILON


@dataclass
class FunnelState:
    step_number: int
    total_steps: int
    apex: Point
    left_chain: List[Point] = field(default_factory=list)
    right_chain: List[Point] = field(default_factory=list)
    portal_idx: int = 0
    portal: Optional[Tuple[Point, Point]] = None
    path_so_far: List[Point] = field(default_factory=list)
    description: str = ""
    is_complete: bool = False
    path_length: float = 0.0

    # Fields for showing boundary crossing before apex moves
    is_crossing_step: bool = False
    crossing_line: Optional[Tuple[Point, Point]] = None      # Candidate line from apex to new portal vertex
    crossed_segment: Optional[Tuple[Point, Point]] = None    # Funnel boundary segment being crossed
    crossing_point: Optional[Point] = None                   # Corner vertex that must become new apex
    crossing_side: str = ""                                  # "left" or "right"


class FunnelAlgorithm:
    """
    Executes the Funnel Algorithm step-by-step.
    Precomputes all intermediate states for smooth interactive navigation
    (forward and backward stepping).
    """

    def __init__(self, portals: List[Tuple[Point, Point]]):
        self.portals = portals
        self.states: List[FunnelState] = []
        self._current_index = 0
        self._compute_all_steps()

    @property
    def current_state(self) -> FunnelState:
        if not self.states:
            raise ValueError("No states available in FunnelAlgorithm.")
        return self.states[self._current_index]

    @property
    def current_step_index(self) -> int:
        return self._current_index

    @property
    def total_steps(self) -> int:
        return len(self.states)

    @property
    def is_finished(self) -> bool:
        return self._current_index >= len(self.states) - 1

    def step_forward(self) -> FunnelState:
        """Advances one step if not already finished."""
        if self._current_index < len(self.states) - 1:
            self._current_index += 1
        return self.current_state

    def step_backward(self) -> FunnelState:
        """Steps backward one step if not at the beginning."""
        if self._current_index > 0:
            self._current_index -= 1
        return self.current_state

    def reset_to_start(self):
        self._current_index = 0

    def _calculate_path_length(self, path: List[Point]) -> float:
        total = 0.0
        for i in range(len(path) - 1):
            total += dist(path[i], path[i + 1])
        return total

    def _compute_all_steps(self):
        """Precomputes each step's geometric state and informative explanation."""
        if len(self.portals) < 2:
            s = self.portals[0][0] if self.portals else (0.0, 0.0)
            self.states.append(
                FunnelState(
                    step_number=0,
                    total_steps=1,
                    apex=s,
                    left_chain=[s],
                    right_chain=[s],
                    portal_idx=0,
                    portal=None,
                    path_so_far=[s],
                    description="Trivial path: Start and Target are identical.",
                    is_complete=True,
                    path_length=0.0
                )
            )
            return

        s = self.portals[0][0]
        t = self.portals[-1][0]

        # Case 1: Start and Target are in the same triangle (only 2 portals: (s,s) and (t,t))
        if len(self.portals) == 2:
            path = [s, t]
            length = self._calculate_path_length(path)
            self.states.append(
                FunnelState(
                    step_number=0,
                    total_steps=2,
                    apex=s,
                    left_chain=[s],
                    right_chain=[s],
                    portal_idx=0,
                    portal=(s, s),
                    path_so_far=[s],
                    description="Initialized at Start point S. Both S and T are in the same triangle.",
                    is_complete=False,
                    path_length=0.0
                )
            )
            self.states.append(
                FunnelState(
                    step_number=1,
                    total_steps=2,
                    apex=t,
                    left_chain=[t],
                    right_chain=[t],
                    portal_idx=1,
                    portal=(t, t),
                    path_so_far=path,
                    description="Direct line of sight: Connected S to T! Shortest path complete.",
                    is_complete=True,
                    path_length=length
                )
            )
            return

        # General Case: More than 1 triangle
        apex = s
        path = [apex]
        left_chain = [apex, self.portals[1][0]]
        right_chain = [apex, self.portals[1][1]]

        raw_states: List[FunnelState] = []

        # Step 0: Initialization
        raw_states.append(
            FunnelState(
                step_number=0,
                total_steps=0,
                apex=apex,
                left_chain=[apex],
                right_chain=[apex],
                portal_idx=0,
                portal=self.portals[0],
                path_so_far=list(path),
                description=f"Initialized funnel at Start point S ({apex[0]:.1f}, {apex[1]:.1f}).",
                is_complete=False,
                path_length=0.0
            )
        )

        # Step 1: Open funnel to first portal
        raw_states.append(
            FunnelState(
                step_number=1,
                total_steps=0,
                apex=apex,
                left_chain=list(left_chain),
                right_chain=list(right_chain),
                portal_idx=1,
                portal=self.portals[1],
                path_so_far=list(path),
                description=(
                    f"Opened funnel from S to Portal 1: "
                    f"Left=({self.portals[1][0][0]:.1f}, {self.portals[1][0][1]:.1f}), "
                    f"Right=({self.portals[1][1][0]:.1f}, {self.portals[1][1][1]:.1f})."
                ),
                is_complete=False,
                path_length=0.0
            )
        )

        # Process portals 2 to N-2 (intermediate portals)
        num_portals = len(self.portals)
        for i in range(2, num_portals - 1):
            new_l, new_r = self.portals[i]
            old_l, old_r = self.portals[i - 1]

            if new_l != old_l:
                # Left portal updated
                crossed = False
                while len(right_chain) > 1 and cross2d(right_chain[0], right_chain[1], new_l) <= -EPSILON:
                    corner = right_chain[1]
                    # 1. Crossing step: Show sightline crossing the right boundary BEFORE apex moves
                    raw_states.append(
                        FunnelState(
                            step_number=len(raw_states),
                            total_steps=0,
                            apex=apex,
                            left_chain=list(left_chain),
                            right_chain=list(right_chain),
                            portal_idx=i,
                            portal=self.portals[i],
                            path_so_far=list(path),
                            description=(
                                f"Line to left portal vertex ({new_l[0]:.1f}, {new_l[1]:.1f}) "
                                f"crosses right boundary at ({corner[0]:.1f}, {corner[1]:.1f}). "
                                f"Apex moves to this vertex next."
                            ),
                            is_complete=False,
                            path_length=self._calculate_path_length(path),
                            is_crossing_step=True,
                            crossing_line=(apex, new_l),
                            crossed_segment=(apex, corner),
                            crossing_point=corner,
                            crossing_side="left"
                        )
                    )

                    # 2. Apex move step: Move apex to corner
                    right_chain.pop(0)
                    apex = corner
                    path.append(apex)
                    crossed = True
                    raw_states.append(
                        FunnelState(
                            step_number=len(raw_states),
                            total_steps=0,
                            apex=apex,
                            left_chain=list(left_chain),
                            right_chain=list(right_chain),
                            portal_idx=i,
                            portal=self.portals[i],
                            path_so_far=list(path),
                            description=(
                                f"Apex moved to corner ({apex[0]:.1f}, {apex[1]:.1f})! "
                                f"Shortest path extended. Funnel re-anchored. Press ENTER to continue."
                            ),
                            is_complete=False,
                            path_length=self._calculate_path_length(path),
                        )
                    )

                if crossed:
                    left_chain = [apex, new_l]
                    raw_states.append(
                        FunnelState(
                            step_number=len(raw_states),
                            total_steps=0,
                            apex=apex,
                            left_chain=list(left_chain),
                            right_chain=list(right_chain),
                            portal_idx=i,
                            portal=self.portals[i],
                            path_so_far=list(path),
                            description=(
                                f"Funnel re-opened at new Apex ({apex[0]:.1f}, {apex[1]:.1f}) "
                                f"with Left portal vertex ({new_l[0]:.1f}, {new_l[1]:.1f})."
                            ),
                            is_complete=False,
                            path_length=self._calculate_path_length(path),
                        )
                    )
                else:
                    # Narrow left chain
                    popped_count = 0
                    while len(left_chain) > 1 and cross2d(left_chain[-2], left_chain[-1], new_l) <= -EPSILON:
                        left_chain.pop()
                        popped_count += 1
                    left_chain.append(new_l)
                    desc = (
                        f"Left portal updated to ({new_l[0]:.1f}, {new_l[1]:.1f}) (tightened {popped_count} vertices)."
                        if popped_count > 0 else
                        f"Left portal widened to ({new_l[0]:.1f}, {new_l[1]:.1f})."
                    )
                    raw_states.append(
                        FunnelState(
                            step_number=len(raw_states),
                            total_steps=0,
                            apex=apex,
                            left_chain=list(left_chain),
                            right_chain=list(right_chain),
                            portal_idx=i,
                            portal=self.portals[i],
                            path_so_far=list(path),
                            description=f"Step (Portal {i}): {desc}",
                            is_complete=False,
                            path_length=self._calculate_path_length(path),
                        )
                    )

            if new_r != old_r:
                # Right portal updated
                crossed = False
                while len(left_chain) > 1 and cross2d(left_chain[0], left_chain[1], new_r) >= EPSILON:
                    corner = left_chain[1]
                    # 1. Crossing step: Show sightline crossing the left boundary BEFORE apex moves
                    raw_states.append(
                        FunnelState(
                            step_number=len(raw_states),
                            total_steps=0,
                            apex=apex,
                            left_chain=list(left_chain),
                            right_chain=list(right_chain),
                            portal_idx=i,
                            portal=self.portals[i],
                            path_so_far=list(path),
                            description=(
                                f"Line to right portal vertex ({new_r[0]:.1f}, {new_r[1]:.1f}) "
                                f"crosses left boundary at ({corner[0]:.1f}, {corner[1]:.1f}). "
                                f"Apex moves to this vertex next."
                            ),
                            is_complete=False,
                            path_length=self._calculate_path_length(path),
                            is_crossing_step=True,
                            crossing_line=(apex, new_r),
                            crossed_segment=(apex, corner),
                            crossing_point=corner,
                            crossing_side="right"
                        )
                    )

                    # 2. Apex move step: Move apex to corner
                    left_chain.pop(0)
                    apex = corner
                    path.append(apex)
                    crossed = True
                    raw_states.append(
                        FunnelState(
                            step_number=len(raw_states),
                            total_steps=0,
                            apex=apex,
                            left_chain=list(left_chain),
                            right_chain=list(right_chain),
                            portal_idx=i,
                            portal=self.portals[i],
                            path_so_far=list(path),
                            description=(
                                f"Apex moved to corner ({apex[0]:.1f}, {apex[1]:.1f}). "
                                f"Funnel re-anchored."
                            ),
                            is_complete=False,
                            path_length=self._calculate_path_length(path),
                        )
                    )

                if crossed:
                    right_chain = [apex, new_r]
                    raw_states.append(
                        FunnelState(
                            step_number=len(raw_states),
                            total_steps=0,
                            apex=apex,
                            left_chain=list(left_chain),
                            right_chain=list(right_chain),
                            portal_idx=i,
                            portal=self.portals[i],
                            path_so_far=list(path),
                            description=(
                                f"Funnel re-opened at Apex ({apex[0]:.1f}, {apex[1]:.1f}) "
                                f"with Right portal vertex ({new_r[0]:.1f}, {new_r[1]:.1f})."
                            ),
                            is_complete=False,
                            path_length=self._calculate_path_length(path),
                        )
                    )
                else:
                    # Narrow right chain
                    popped_count = 0
                    while len(right_chain) > 1 and cross2d(right_chain[-2], right_chain[-1], new_r) >= EPSILON:
                        right_chain.pop()
                        popped_count += 1
                    right_chain.append(new_r)
                    desc = (
                        f"Right portal updated to ({new_r[0]:.1f}, {new_r[1]:.1f}) (tightened {popped_count} vertices)."
                        if popped_count > 0 else
                        f"Right portal widened to ({new_r[0]:.1f}, {new_r[1]:.1f})."
                    )
                    raw_states.append(
                        FunnelState(
                            step_number=len(raw_states),
                            total_steps=0,
                            apex=apex,
                            left_chain=list(left_chain),
                            right_chain=list(right_chain),
                            portal_idx=i,
                            portal=self.portals[i],
                            path_so_far=list(path),
                            description=f"Step (Portal {i}): {desc}",
                            is_complete=False,
                            path_length=self._calculate_path_length(path),
                        )
                    )

        # Final target step: portal is (t, t)
        while len(left_chain) > 1 and cross2d(left_chain[0], left_chain[1], t) >= EPSILON:
            corner = left_chain[1]
            raw_states.append(
                FunnelState(
                    step_number=len(raw_states),
                    total_steps=0,
                    apex=apex,
                    left_chain=list(left_chain),
                    right_chain=list(right_chain),
                    portal_idx=num_portals - 1,
                    portal=self.portals[-1],
                    path_so_far=list(path),
                    description=(
                        f"Line to target crosses left boundary at ({corner[0]:.1f}, {corner[1]:.1f}). "
                        f"Apex moves to this vertex next."
                    ),
                    is_complete=False,
                    path_length=self._calculate_path_length(path),
                    is_crossing_step=True,
                    crossing_line=(apex, t),
                    crossed_segment=(apex, corner),
                    crossing_point=corner,
                    crossing_side="left"
                )
            )
            left_chain.pop(0)
            apex = corner
            path.append(apex)
            raw_states.append(
                FunnelState(
                    step_number=len(raw_states),
                    total_steps=0,
                    apex=apex,
                    left_chain=list(left_chain),
                    right_chain=list(right_chain),
                    portal_idx=num_portals - 1,
                    portal=self.portals[-1],
                    path_so_far=list(path),
                    description=f"Apex moved to corner ({apex[0]:.1f}, {apex[1]:.1f}) towards Target T.",
                    is_complete=False,
                    path_length=self._calculate_path_length(path),
                )
            )

        while len(right_chain) > 1 and cross2d(right_chain[0], right_chain[1], t) <= -EPSILON:
            corner = right_chain[1]
            raw_states.append(
                FunnelState(
                    step_number=len(raw_states),
                    total_steps=0,
                    apex=apex,
                    left_chain=list(left_chain),
                    right_chain=list(right_chain),
                    portal_idx=num_portals - 1,
                    portal=self.portals[-1],
                    path_so_far=list(path),
                    description=(
                        f"Line to target crosses right boundary at ({corner[0]:.1f}, {corner[1]:.1f}). "
                        f"Apex moves to this vertex next."
                    ),
                    is_complete=False,
                    path_length=self._calculate_path_length(path),
                    is_crossing_step=True,
                    crossing_line=(apex, t),
                    crossed_segment=(apex, corner),
                    crossing_point=corner,
                    crossing_side="right"
                )
            )
            right_chain.pop(0)
            apex = corner
            path.append(apex)
            raw_states.append(
                FunnelState(
                    step_number=len(raw_states),
                    total_steps=0,
                    apex=apex,
                    left_chain=list(left_chain),
                    right_chain=list(right_chain),
                    portal_idx=num_portals - 1,
                    portal=self.portals[-1],
                    path_so_far=list(path),
                    description=f"Apex moved to corner ({apex[0]:.1f}, {apex[1]:.1f}) towards Target T.",
                    is_complete=False,
                    path_length=self._calculate_path_length(path),
                )
            )

        if path[-1] != t:
            path.append(t)

        final_length = self._calculate_path_length(path)
        raw_states.append(
            FunnelState(
                step_number=len(raw_states),
                total_steps=0,
                apex=t,
                left_chain=[t],
                right_chain=[t],
                portal_idx=num_portals - 1,
                portal=self.portals[-1],
                path_so_far=list(path),
                description="Final Step: Direct connection from final Apex to Target T! Shortest path complete.",
                is_complete=True,
                path_length=final_length
            )
        )

        total_steps = len(raw_states)
        for s_idx, st in enumerate(raw_states):
            st.step_number = s_idx
            st.total_steps = total_steps

        self.states = raw_states
