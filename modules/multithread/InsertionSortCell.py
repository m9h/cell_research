
import threading
import time
from .MultiThreadCell import MultiThreadCell, CellStatus
from .CellGroup import GroupStatus
import random

class InsertionSortCell(MultiThreadCell):
    def __init__(self, threadID, value, lock, current_position, cells, left_boundary, right_boundary, status_probe, disable_visualization=False, swapping_count=None, export_steps=None, label=0, reverse_direction=False):
        super().__init__(threadID, value, lock, current_position, cells, left_boundary, right_boundary, status_probe, disable_visualization=disable_visualization, swapping_count=swapping_count, export_steps=export_steps, reverse_direction=reverse_direction)
        self.cell_vision = 1
        self.cell_type = 'Insertion'
        self.label = label

    def within_boundary(self, pos):
        if pos[0] > self.right_boundary[0] or pos[1] > self.right_boundary[1]:
            return False
        
        if pos[0] < self.left_boundary[0] or pos[1] < self.left_boundary[1]:
            return False

        return True

    def should_move(self):
        if self.current_position[0] <= self.left_boundary[0]:
            return False
        neighbor = self.cells[self.current_position[0] - 1]
        out_of_order = self.value > neighbor.value if self.reverse_direction else self.value < neighbor.value
        return self.can_swap_with(neighbor) and self.is_enable_to_move() and out_of_order
        #return smaller_than_left

    def should_move_to(self, target_position):
        if (
            (self.status == CellStatus.ACTIVE or self.status == CellStatus.FREEZE)
            and self.within_boundary(target_position)
            and (self.cells[int(target_position[0])].status == CellStatus.ACTIVE  or self.cells[int(target_position[0])].status == CellStatus.FREEZE)
        ):
            next_cell = int(target_position[0])
            while next_cell < len(self.cells) and self.cells[next_cell].status ==  CellStatus.FREEZE:
                next_cell += 1
            # if self.status == CellStatus.FREEZE:
            #     print("xxxxxxxxxxxxxxx1")

            # if self.cells[int(target_position[0])].status == CellStatus.FREEZE:
            #     print("xxxxxxxxxxxxxxx2")
            err_happen = self.rng.random() < 0
            if err_happen:
                return not self.value > self.cells[int(target_position[0])].value 
            # if self.cells[int(target_position[0])].status == CellStatus.FREEZE:
            #     print("xxxxxxxxxxxxxxx3")
            if self.reverse_direction:
                return self.value > self.cells[int(target_position[0])].value
            return self.value < self.cells[int(target_position[0])].value
        # else:
        #     if not self.within_boundary(target_position):
        #         print(target_position)
        #     if self.within_boundary(target_position):
        #         print(self.status)
        
    def is_enable_to_move(self):
        prev = float("inf") if self.reverse_direction else float("-inf")
        for i in range(self.left_boundary[0], self.current_position[0]):
            if self.cells[i].status == CellStatus.FREEZE:
                # Preserve upstream's explicit prefix reset at a frozen cell.
                prev = float("inf") if self.reverse_direction else float("-inf")
                continue
            value = self.cells[i].value
            if (self.reverse_direction and value > prev) or (not self.reverse_direction and value < prev):
                return False
            prev = value
        return True
    
    def move(self):
        with self.lock:
            if not self.is_enable_to_move():
                return
            if self.should_move():
                self.status_probe.record_compare_and_swap()
            if self.group.status == GroupStatus.SLEEP and self.status != CellStatus.MOVING:
                self.status = CellStatus.SLEEP
            target = (self.current_position[0] - self.cell_vision, self.current_position[1])
            if self.should_move_to(target):
                self.swap(target)

