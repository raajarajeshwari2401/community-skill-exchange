"""
points.py
---------
Implements the Exchange Point calculation using SymPy.

College requirement demonstrated: SymPy library usage for a real
mathematical computation (not just numbers) inside the platform.

Formula:
    Exchange Points = Duration x Difficulty Factor

Difficulty factors:
    Basic        = 1.0
    Intermediate = 1.5
    Advanced     = 2.0

We use sympy.Rational so the multiplication is performed as exact
symbolic/rational arithmetic (this is the part that is easy to show
during a viva: open a Python shell, import sympy, and multiply the
Rational duration by the Rational factor to get an exact fraction,
which is then converted to a float for storage/display).
"""

from sympy import Rational, symbols, Eq, simplify

# Difficulty factor lookup, expressed as exact fractions via SymPy's Rational
DIFFICULTY_FACTORS = {
    "Basic": Rational(1, 1),
    "Intermediate": Rational(3, 2),   # 1.5
    "Advanced": Rational(2, 1),
}

MIN_DURATION = 1
MAX_DURATION = 8


def calculate_points(duration, difficulty):
    """
    Calculate Exchange Points using SymPy.

    Args:
        duration (float|int): hours spent teaching/learning (1-8)
        difficulty (str): 'Basic' | 'Intermediate' | 'Advanced'

    Returns:
        float: calculated exchange points, rounded to 2 decimals

    Raises:
        ValueError: if duration is out of range or difficulty is unknown
    """
    if difficulty not in DIFFICULTY_FACTORS:
        raise ValueError(f"Unknown difficulty level: {difficulty}")

    if duration < MIN_DURATION or duration > MAX_DURATION:
        raise ValueError(
            f"Duration must be between {MIN_DURATION} and {MAX_DURATION} hours"
        )

    # --- SymPy symbolic calculation ---
    d = Rational(duration)                       # exact rational duration
    factor = DIFFICULTY_FACTORS[difficulty]       # exact rational factor
    points_symbolic = simplify(d * factor)        # symbolic multiplication

    return float(points_symbolic)


def explain_calculation(duration, difficulty):
    """
    Returns a human-readable string showing the SymPy computation,
    useful for displaying on the Offer Skill / Request Skill pages
    and for explaining the formula during a viva.
    """
    factor = DIFFICULTY_FACTORS.get(difficulty)
    if factor is None:
        return "Invalid difficulty"
    result = calculate_points(duration, difficulty)
    return f"{duration} hours x {difficulty} ({float(factor)}) = {result} points"


if __name__ == "__main__":
    # Quick manual test / viva demo
    print(explain_calculation(4, "Advanced"))       # 4 x 2.0 = 8 points
    print(explain_calculation(2, "Intermediate"))    # 2 x 1.5 = 3 points
    print(explain_calculation(2, "Basic"))           # 2 x 1.0 = 2 points
