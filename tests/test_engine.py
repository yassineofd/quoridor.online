"""Rule tests for the server engine. Run: python -m unittest discover tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.engine import Game  # noqa: E402


def mv(r, c):
    return {"type": "move", "r": r, "c": c}


def wall(o, r, c):
    return {"type": "wall", "o": o, "r": r, "c": c}


def game_with(p0=None, p1=None, h=(), v=(), turn=0):
    g = Game()
    if p0:
        g.pawns[0] = p0
    if p1:
        g.pawns[1] = p1
    g.h, g.v, g.turn = set(h), set(v), turn
    return g


class Movement(unittest.TestCase):
    def test_start_position(self):
        g = Game()
        self.assertEqual(g.pawns, [(8, 4), (0, 4)])
        self.assertEqual(sorted(g.pawn_moves()), [(7, 4), (8, 3), (8, 5)])
        self.assertEqual(g.walls_left, [10, 10])

    def test_cannot_pass_a_wall(self):
        g = game_with(h=[(7, 4)])  # below row 7, columns 4-5
        self.assertNotIn((7, 4), g.pawn_moves())
        g = game_with(h=[(7, 3)])  # columns 3-4
        self.assertNotIn((7, 4), g.pawn_moves())
        g = game_with(h=[(7, 2)])  # columns 2-3: does not touch column 4
        self.assertIn((7, 4), g.pawn_moves())

    def test_straight_jump(self):
        g = game_with(p0=(5, 4), p1=(4, 4))
        self.assertIn((3, 4), g.pawn_moves())
        self.assertNotIn((4, 4), g.pawn_moves())

    def test_no_jump_through_a_wall_in_front_of_the_opponent(self):
        g = game_with(p0=(5, 4), p1=(4, 4), h=[(3, 4)])  # wall behind the opponent
        moves = g.pawn_moves()
        self.assertNotIn((3, 4), moves)
        self.assertEqual(sorted(m for m in moves if m[0] == 4), [(4, 3), (4, 5)])

    def test_jump_blocked_by_edge_goes_sideways(self):
        g = game_with(p0=(1, 4), p1=(0, 4), turn=0)
        moves = g.pawn_moves()
        self.assertIn((0, 3), moves)
        self.assertIn((0, 5), moves)
        self.assertNotIn((0, 4), moves)

    def test_diagonal_blocked_by_wall_beside_opponent(self):
        g = game_with(p0=(5, 4), p1=(4, 4), h=[(3, 4)], v=[(3, 3)])  # wall left of the opponent
        sides = sorted(m for m in g.pawn_moves() if m[0] == 4)
        self.assertEqual(sides, [(4, 5)])

    def test_wall_between_pawns_blocks_the_move_and_jump(self):
        g = game_with(p0=(5, 4), p1=(4, 4), h=[(4, 4)])
        moves = g.pawn_moves()
        self.assertNotIn((4, 4), moves)
        self.assertNotIn((3, 4), moves)

    def test_vertical_walls_block_sideways_movement(self):
        g = game_with(p0=(8, 4), v=[(7, 4)])  # right of column 4, rows 7-8
        self.assertNotIn((8, 5), g.pawn_moves())
        self.assertIn((8, 3), g.pawn_moves())


class Walls(unittest.TestCase):
    def test_overlap_and_crossing(self):
        g = game_with(h=[(3, 3)])
        self.assertEqual(g.wall_error("h", 3, 3), "overlap")
        self.assertEqual(g.wall_error("h", 3, 4), "overlap")
        self.assertEqual(g.wall_error("h", 3, 2), "overlap")
        self.assertIsNone(g.wall_error("h", 3, 5))
        self.assertEqual(g.wall_error("v", 3, 3), "cross")
        self.assertIsNone(g.wall_error("v", 3, 4))
        self.assertIsNone(g.wall_error("v", 2, 3))
        g = game_with(v=[(3, 3)])
        self.assertEqual(g.wall_error("v", 4, 3), "overlap")
        self.assertEqual(g.wall_error("v", 2, 3), "overlap")
        self.assertEqual(g.wall_error("h", 3, 3), "cross")

    def test_bounds(self):
        g = Game()
        for args in [("h", 8, 0), ("h", 0, 8), ("v", -1, 0), ("x", 0, 0)]:
            self.assertEqual(g.wall_error(*args), "out-of-bounds")

    def test_cannot_seal_a_pawn_in(self):
        # Pocket of two squares in the bottom-left corner: a wall above it, then a wall to its right.
        g = game_with(p0=(8, 0), h=[(7, 0)])
        self.assertEqual(g.wall_error("v", 7, 1), "blocks-path")
        self.assertIsNone(g.wall_error("v", 6, 1))  # a wall that doesn't close the pocket is fine

    def test_cannot_seal_the_opponent_either(self):
        # The check covers both players, not just the one placing the wall.
        g = game_with(p0=(4, 4), p1=(0, 0), h=[(0, 0)])
        self.assertEqual(g.wall_error("v", 0, 1), "blocks-path")

    def test_a_row_with_one_gap_is_legal(self):
        g = Game()
        for c in (0, 2, 4, 6):
            self.assertIsNone(g.wall_error("h", 3, c))
            g.h.add((3, c))
        self.assertEqual(g.wall_error("h", 3, 7), "overlap")
        self.assertEqual(g.distance(0), 8 + 4)  # 8 rows up plus 4 columns across to the gap in column 8

    def test_no_walls_left(self):
        g = Game()
        g.walls_left[0] = 0
        self.assertEqual(g.wall_error("h", 0, 0), "no-walls")


class Playing(unittest.TestCase):
    def test_turns_alternate_and_walls_are_spent(self):
        g = Game()
        self.assertIsNone(g.apply(mv(7, 4)))
        self.assertEqual(g.turn, 1)
        self.assertIsNone(g.apply(wall("h", 6, 3)))
        self.assertEqual(g.walls_left, [10, 9])
        self.assertEqual(g.turn, 0)

    def test_illegal_moves_do_not_change_anything(self):
        g = Game()
        before = g.to_dict()
        self.assertEqual(g.apply(mv(5, 4)), "illegal-move")
        self.assertEqual(g.apply({"type": "teleport"}), "bad-move")
        self.assertEqual(g.apply(mv(True, 4)), "illegal-move")
        self.assertEqual(g.apply(None), "bad-move")
        self.assertEqual(g.to_dict(), before)

    def test_reaching_the_far_edge_wins(self):
        g = game_with(p0=(1, 4), p1=(8, 0))
        self.assertIsNone(g.apply(mv(0, 4)))
        self.assertEqual(g.winner, 0)
        self.assertEqual(g.apply(mv(7, 0)), "game-over")

    def test_player_one_wins_on_the_bottom_row(self):
        g = game_with(p0=(4, 4), p1=(7, 0), turn=1)
        self.assertIsNone(g.apply(mv(8, 0)))
        self.assertEqual(g.winner, 1)

    def test_resign(self):
        g = Game()
        g.resign(0)
        self.assertEqual(g.winner, 1)


if __name__ == "__main__":
    unittest.main()
