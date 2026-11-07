
import threading
import time
from .MultiThreadCell import MultiThreadCell, CellStatus
from .CellGroup import GroupStatus
import random

class SelectionSortCell(MultiThreadCell):
    def __init__(self, threadID, value, lock, current_position, cells, left_boundary, right_boundary, status_probe, disable_visualization=False, swapping_count=None, export_steps=None, label=0, reverse_direction=False):
        super().__init__(threadID, value, lock, current_position, cells, left_boundary, right_boundary, status_probe, disable_visualization=disable_visualization, swapping_count=swapping_count, export_steps=export_steps, reverse_direction=reverse_direction)
        if self.reverse_direction:
            self.ideal_position = right_boundary
        else:
            self.ideal_position = left_boundary
        self.cell_type = 'Selection'
        self.label = label


    def get_current_snapshot(self):
        return {"value": self.value, "group id": self.group.group_id, "group status": self.group.status, "cell status": self.status, "left": self.left_boundary, "right": self.right_boundary, "cell_type": self.cell_type, "cp": self.current_position[0], "ip": self.ideal_position[0],  "should_move": self.should_move(), "with_lock": self.with_lock}
    
    def within_boundary(self, pos):
        if pos[0] > self.right_boundary[0] or pos[1] > self.right_boundary[1]:
            return False
        
        if pos[0] < self.left_boundary[0] or pos[1] < self.left_boundary[1]:
            return False

        return True

    def should_move(self):
        # Advancing the ideal-position pointer is progress, even without a swap.
        return (self.status == CellStatus.ACTIVE
                and self.current_position != self.ideal_position
                and self.within_boundary(self.ideal_position))

    def should_move_to(self, target_position):
        if not self.should_move() or not self.within_boundary(target_position):
            return False
        target = self.cells[target_position[0]]
        # The pointer searches from the right for descending order, still selecting smaller values.
        precedes = self.value < target.value
        if target.status == CellStatus.FREEZE:
            self.advance_ideal_position()
            if precedes:
                self.swap(target_position)
            return False
        if target.status == CellStatus.ACTIVE:
            if not precedes:
                self.advance_ideal_position()
                return False
            return True
        return False

    def advance_ideal_position(self):
        delta = -1 if self.reverse_direction else 1
        self.ideal_position = (self.ideal_position[0] + delta, self.ideal_position[1])

        # if self.within_boundary(target_position) and self.cells[int(target_position[0])].status == CellStatus.FREEZE:
        #     return True

    def move_beside_freezed_cell(self, target_position):
        target_index = target_position[0]
        current_index = self.current_position[0]
        while current_index > target_index:
            self.swap((current_index - 1, self.current_position[1]), current_index - 1 != target_index)
            current_index -= 1
    
    def update(self):
        if self.reverse_direction:
            self.ideal_position = self.right_boundary
        else:
            self.ideal_position = self.left_boundary

    def move(self):
        with self.lock:
            self.with_lock = True
            try:
                if self.group.status == GroupStatus.SLEEP and self.status != CellStatus.MOVING:
                    self.status = CellStatus.SLEEP
                if self.should_move():
                    self.status_probe.record_compare_and_swap()
                if self.should_move_to(self.ideal_position):
                    self.swap(self.ideal_position)
            finally:
                self.with_lock = False

    
