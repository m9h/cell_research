
import threading
import time
from .MultiThreadCell import MultiThreadCell, CellStatus
from .CellGroup import GroupStatus
import random

class BubbleSortCell(MultiThreadCell):
    def __init__(self, threadID, value, lock, current_position, cells, left_boundary, right_boundary, status_probe, disable_visualization=False, swapping_count=None, export_steps=None, label=0, reverse_direction=False):
        super().__init__(threadID, value, lock, current_position, cells, left_boundary, right_boundary, status_probe, disable_visualization=disable_visualization, swapping_count=swapping_count, export_steps=export_steps, reverse_direction=reverse_direction)
        self.cell_vision = 1
        self.cell_type = 'Bubble'
        self.label = label

    def within_boundary(self, pos):
        if pos[0] > self.right_boundary[0] or pos[1] > self.right_boundary[1]:
            return False
        
        if pos[0] < self.left_boundary[0] or pos[1] < self.left_boundary[1]:
            return False

        return True

    def should_move(self):
        # Pure availability check, including passive frozen neighbors.
        for offset in (-1, 1):
            pos = (self.current_position[0] + offset, self.current_position[1])
            if self.within_boundary(pos):
                neighbor = self.cells[pos[0]]
                if self.can_swap_with(neighbor) and self.out_of_order(neighbor, offset == 1):
                    return True
        return False

    def out_of_order(self, neighbor, check_right):
        if self.reverse_direction:
            return self.value < neighbor.value if check_right else self.value > neighbor.value
        return self.value > neighbor.value if check_right else self.value < neighbor.value

    def should_move_to(self, target_position, check_right):
            
        if (
            self.status == CellStatus.ACTIVE
            and self.within_boundary(target_position)
            and (self.cells[int(target_position[0])].status == CellStatus.ACTIVE  or self.cells[int(target_position[0])].status == CellStatus.FREEZE)
        ):
            err_happen = self.rng.random() < 0
            if err_happen:
                return not self.value > self.cells[int(target_position[0])].value 
            if self.reverse_direction:
                return self.value < self.cells[int(target_position[0])].value if check_right else self.value > self.cells[int(target_position[0])].value
            return self.value > self.cells[int(target_position[0])].value if check_right else self.value < self.cells[int(target_position[0])].value
    
    def move(self):
        with self.lock:
            self.with_lock = True
            try:
                if self.group.status == GroupStatus.SLEEP and self.status != CellStatus.MOVING:
                    self.status = CellStatus.SLEEP
                if self.should_move():
                    self.status_probe.record_compare_and_swap()
                check_right = self.rng.random() < 0.5
                offset = self.cell_vision if check_right else -self.cell_vision
                target = (self.current_position[0] + offset, self.current_position[1])
                if self.should_move_to(target, check_right):
                    self.swap(target)
            finally:
                self.with_lock = False

