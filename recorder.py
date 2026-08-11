"""
Position Recorder Module
Manages recording, clearing, and sequence playback of multi-point click coordinates.
"""

from typing import List, Tuple


class PositionRecorder:
    """
    Modular position recorder that handles multi-location click sequences.
    """
    def __init__(self):
        self.positions: List[Tuple[int, int]] = []

    def add_position(self, x: int, y: int) -> int:
        """
        Adds a target coordinate (x, y) to the sequence list.
        """
        self.positions.append((int(x), int(y)))
        return len(self.positions) - 1

    def remove_position(self, index: int) -> bool:
        """
        Removes a coordinate entry by 0-based index.
        """
        if 0 <= index < len(self.positions):
            self.positions.pop(index)
            return True
        return False

    def clear_positions(self):
        """
        Clears all recorded coordinates from sequence.
        """
        self.positions.clear()

    def get_positions(self) -> List[Tuple[int, int]]:
        """
        Returns a copy of the list of recorded (x, y) coordinates.
        """
        return list(self.positions)

    def count(self) -> int:
        """
        Returns the count of recorded positions.
        """
        return len(self.positions)
