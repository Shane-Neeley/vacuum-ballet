from __future__ import annotations

from patterns import circle, figure_eight, lissajous, spin_crazy, square


def test_circle_and_square_are_map_frame_integer_paths() -> None:
    assert list(circle((0, 0), 100, steps=4)) == [(100, 0), (0, 100), (-100, 0), (0, -100)]
    assert square((0, 0), 50) == [(-50, -50), (50, -50), (50, 50), (-50, 50), (-50, -50)]


def test_curves_are_bounded_and_deterministic() -> None:
    paths = [
        list(figure_eight((0, 0), 500, steps=20)),
        list(lissajous((100, 200), 300, 400, a=2, b=3, steps=6)),
        list(spin_crazy((0, 0), 400, steps=5)),
    ]
    assert all(isinstance(value, int) for path in paths for point in path for value in point)
    assert paths[2] == list(spin_crazy((0, 0), 400, steps=5))
    assert all(-600 <= x <= 600 and -600 <= y <= 600 for x, y in paths[0])
