"""
Battlesnake game replay tests.

Loads real game recordings from tests/test_files/*.json and replays them,
measuring how long the algorithm takes to decide each move.

    python3 -m pytest tests/ -v          # pass/fail only
    python3 -m pytest tests/ -v -s       # show per-move timing report
"""

import contextlib
import glob
import io
import json
import os
import random
import time
import typing
from collections import defaultdict

import pytest

from main import move as our_move

# ---------------------------------------------------------------------------
# Game replay loader
# ---------------------------------------------------------------------------

OUR_SNAKE_NAME = "talbott-hall"  # fallback; auto-detected per file
GAME_FILES_DIR = os.path.join(os.path.dirname(__file__), "test_files")

# Set to a turn number to drop into pdb at that turn, e.g. DEBUG_TURN = 42
# Run with: pytest tests/ -v -s -k "<filename>" --pdb
DEBUG_TURN: typing.Optional[int] = None


def load_game_frames(path: str) -> typing.List[dict]:
    """Load frames from an NDJSON game recording where our snake is alive.

    The snake is identified by the ``you`` field on the first turn-0 frame,
    then tracked by id for the remainder of the game.

    Each returned frame has ``you`` set to our snake, ready to pass to ``move()``.
    """
    raw_frames = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            state = json.loads(line)
            if "turn" not in state:
                continue  # bare game metadata line
            raw_frames.append(state)

    if not raw_frames:
        return []

    # Identify our snake from the you.id on the earliest frame that has it.
    our_id: typing.Optional[str] = None
    for state in raw_frames:
        if state.get("you", {}).get("id"):
            our_id = state["you"]["id"]
            break
    if our_id is None:
        return []

    frames = []
    for state in raw_frames:
        our_snake = next(
            (s for s in state["board"]["snakes"] if s["id"] == our_id),
            None,
        )
        if our_snake is None:
            continue  # our snake has been eliminated
        frames.append({**state, "you": our_snake})
    return frames


def _all_game_files() -> typing.List[str]:
    return sorted(glob.glob(os.path.join(GAME_FILES_DIR, "*.json")))


def _game_file_id(path: str) -> str:
    return os.path.basename(path)


# ---------------------------------------------------------------------------
# Types (kept for the simulation engine below)
# ---------------------------------------------------------------------------

Point = typing.Tuple[int, int]


class GameResult(typing.NamedTuple):
    turns_survived: int
    food_eaten: int
    survived: bool
    cause_of_death: typing.Optional[str]
    final_length: int


# ---------------------------------------------------------------------------
# Snake & state builders
# ---------------------------------------------------------------------------

def _snake(sid: str, body: typing.List[Point], health: int = 100) -> dict:
    bd = [{"x": x, "y": y} for x, y in body]
    return {"id": sid, "name": sid, "health": health,
            "body": bd, "head": bd[0], "length": len(bd)}


def _state(width: int, height: int, snakes: typing.List[dict],
           food: typing.List[Point], turn: int = 0) -> dict:
    return {
        "turn": turn,
        "board": {
            "width": width,
            "height": height,
            "food": [{"x": x, "y": y} for x, y in food],
            "snakes": list(snakes),
        },
        "you": snakes[0],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

def random_mover(game_state: dict) -> str:
    """Pick a random valid move (avoids walls and own body)."""
    head = game_state["you"]["head"]
    hx, hy = head["x"], head["y"]
    w = game_state["board"]["width"]
    h = game_state["board"]["height"]
    body_set = {(s["x"], s["y"]) for s in game_state["you"]["body"][1:]}
    options = [
        d for d, (dx, dy) in (
            ("up", (0, 1)), ("down", (0, -1)),
            ("left", (-1, 0)), ("right", (1, 0)),
        )
        if 0 <= hx + dx < w and 0 <= hy + dy < h
        and (hx + dx, hy + dy) not in body_set
    ]
    return random.choice(options) if options else "up"


# ---------------------------------------------------------------------------
# Game engine
# ---------------------------------------------------------------------------

_DELTA: typing.Dict[str, Point] = {
    "up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0),
}


def _step(
    width: int,
    height: int,
    snakes: typing.List[dict],
    food: typing.List[Point],
    move_funcs: typing.Dict[str, typing.Callable],
    turn: int,
    rng: random.Random,
) -> typing.Tuple[
    typing.List[dict],
    typing.List[Point],
    typing.Dict[str, str],
    typing.Set[str],
]:
    """Advance the game one turn following standard Battlesnake rules."""
    base = _state(width, height, snakes, food, turn)

    # --- Collect moves ---
    chosen: typing.Dict[str, str] = {}
    for s in snakes:
        sid = s["id"]
        try:
            result = move_funcs[sid]({**base, "you": s})
            # our_move returns {"move": "direction"}; opponent helpers return a bare string
            chosen[sid] = result["move"] if isinstance(result, dict) else result
        except Exception:
            chosen[sid] = "up"

    # --- New head positions ---
    new_heads: typing.Dict[str, Point] = {}
    for s in snakes:
        sid = s["id"]
        hx, hy = s["head"]["x"], s["head"]["y"]
        dx, dy = _DELTA[chosen[sid]]
        new_heads[sid] = (hx + dx, hy + dy)

    deaths: typing.Dict[str, str] = {}

    # --- Wall collisions ---
    for s in snakes:
        sid = s["id"]
        nh = new_heads[sid]
        if not (0 <= nh[0] < width and 0 <= nh[1] < height):
            deaths[sid] = "wall"

    # --- Body collisions ---
    # Check new head against segments that will still occupy that cell after
    # this turn (all segments except the tail, unless the snake just ate).
    for s in snakes:
        sid = s["id"]
        if sid in deaths:
            continue
        nh = new_heads[sid]
        for other in snakes:
            oid = other["id"]
            body_pts = [(seg["x"], seg["y"]) for seg in other["body"]]
            just_ate = len(body_pts) >= 2 and body_pts[-1] == body_pts[-2]
            occupied = set(body_pts if just_ate else body_pts[:-1])
            if nh in occupied:
                deaths[sid] = "self_collision" if oid == sid else f"body:{oid}"
                break

    # --- Head-to-head collisions ---
    head_map: typing.Dict[Point, typing.List[str]] = defaultdict(list)
    for s in snakes:
        sid = s["id"]
        if sid not in deaths:
            head_map[new_heads[sid]].append(sid)

    for pos, colliders in head_map.items():
        if len(colliders) < 2:
            continue
        lens = {
            sid: len(next(s for s in snakes if s["id"] == sid)["body"])
            for sid in colliders
        }
        max_len = max(lens.values())
        tied_for_max = sum(1 for l in lens.values() if l == max_len)
        for sid in colliders:
            if lens[sid] < max_len:
                deaths[sid] = "h2h_loss"
            elif tied_for_max > 1:
                deaths[sid] = "h2h_tie"
            # sole longest snake — survives

    # --- Update survivors ---
    food_set = set(food)
    ate_food: typing.Set[str] = set()
    surviving: typing.List[dict] = []

    for s in snakes:
        sid = s["id"]
        if sid in deaths:
            continue
        nh = new_heads[sid]
        body_pts = [(seg["x"], seg["y"]) for seg in s["body"]]

        if nh in food_set:
            new_health = 100
            new_body = [nh] + body_pts       # grow: tail stays
            ate_food.add(sid)
        else:
            new_health = s["health"] - 1
            new_body = [nh] + body_pts[:-1]  # normal: tail vacates

        if new_health <= 0:
            deaths[sid] = "starvation"
            continue

        surviving.append(_snake(sid, new_body, new_health))

    # --- Spawn food ---
    new_food = [f for f in food if f not in ate_food]
    if surviving:
        occ: typing.Set[Point] = {
            (seg["x"], seg["y"]) for s in surviving for seg in s["body"]
        }
        occ.update(new_food)
        free = [(x, y) for x in range(width) for y in range(height) if (x, y) not in occ]
        if free and (not new_food or rng.random() < 0.15):
            new_food.append(rng.choice(free))

    return surviving, new_food, deaths, ate_food


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def simulate(
    width: int,
    height: int,
    snakes: typing.List[typing.Tuple[str, typing.List[Point], int]],
    food: typing.List[Point],
    move_funcs: typing.Dict[str, typing.Callable],
    max_turns: int = 300,
    seed: int = 42,
) -> typing.Dict[str, GameResult]:
    """
    Run a full Battlesnake game and return per-snake GameResult.

    Parameters
    ----------
    snakes      List of (id, body_points, health).
    food        Initial food positions.
    move_funcs  Map of snake_id -> callable(game_state) -> direction string.
    max_turns   Snakes still alive at this limit are marked survived=True.
    seed        RNG seed -- same seed always produces the same game.
    """
    rng = random.Random(seed)
    random.seed(seed)   # seed global RNG for tie-breaking in our_move + random_mover

    live = [_snake(sid, body, hp) for sid, body, hp in snakes]
    current_food = list(food)

    initial_length: typing.Dict[str, int] = {sid: len(body) for sid, body, _ in snakes}
    last_turn: typing.Dict[str, int] = {}
    last_len: typing.Dict[str, int] = dict(initial_length)
    food_count: typing.Dict[str, int] = defaultdict(int)
    all_deaths: typing.Dict[str, str] = {}

    for turn in range(1, max_turns + 1):
        if not live:
            break

        for s in live:
            last_turn[s["id"]] = turn
        pre_len = {s["id"]: s["length"] for s in live}

        live, current_food, deaths, ate = _step(
            width, height, live, current_food, move_funcs, turn, rng
        )

        for sid in ate:
            food_count[sid] += 1
        for s in live:
            last_len[s["id"]] = s["length"]
        for sid, cause in deaths.items():
            all_deaths[sid] = cause
            if sid not in last_len:
                last_len[sid] = pre_len.get(sid, initial_length[sid])

    for s in live:
        last_len[s["id"]] = s["length"]

    return {
        sid: GameResult(
            turns_survived=last_turn.get(sid, 0),
            food_eaten=food_count[sid],
            survived=sid not in all_deaths,
            cause_of_death=all_deaths.get(sid),
            final_length=last_len.get(sid, initial_length[sid]),
        )
        for sid, _, _ in snakes
    }


# ---------------------------------------------------------------------------
# Scenario runners
# ---------------------------------------------------------------------------

def _solo(
    width: int = 11, height: int = 11, seed: int = 42, max_turns: int = 300,
) -> GameResult:
    """Our snake alone on an empty board."""
    cx, cy = width // 2, height // 2
    body: typing.List[Point] = [(cx, cy), (cx, cy - 1), (cx, cy - 2)]
    food: typing.List[Point] = [(2, 2), (width - 3, height - 3)]
    return simulate(
        width, height,
        [("ours", body, 100)],
        food,
        {"ours": our_move},
        max_turns=max_turns,
        seed=seed,
    )["ours"]


def _1v1(seed: int = 42, max_turns: int = 200) -> typing.Dict[str, GameResult]:
    """Our snake vs a random mover, starting on opposite sides of an 11x11 board."""
    return simulate(
        11, 11,
        [
            ("ours",   [(2, 5), (2, 4), (2, 3)], 100),
            ("random", [(8, 5), (8, 6), (8, 7)], 100),
        ],
        [(5, 5), (1, 1), (9, 9)],
        {"ours": our_move, "random": random_mover},
        max_turns=max_turns,
        seed=seed,
    )


def _4snake(seed: int = 42, max_turns: int = 200) -> typing.Dict[str, GameResult]:
    """Our snake vs three random movers, one in each quadrant of an 11x11 board."""
    return simulate(
        11, 11,
        [
            ("ours", [(2, 2),  (2, 1),  (2, 0)],  100),
            ("r1",   [(8, 2),  (8, 1),  (8, 0)],  100),
            ("r2",   [(2, 8),  (2, 9),  (2, 10)], 100),
            ("r3",   [(8, 8),  (8, 9),  (8, 10)], 100),
        ],
        [(5, 5), (0, 5), (10, 5), (5, 0), (5, 10)],
        {"ours": our_move, "r1": random_mover, "r2": random_mover, "r3": random_mover},
        max_turns=max_turns,
        seed=seed,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture(params=_all_game_files(), ids=_game_file_id)
def game_file(request):
    return request.param


class TestGameReplay:
    """
    Replay recorded games from tests/test_files/ and measure how long the
    algorithm takes to decide each move.

    Run with: pytest tests/ -v -s
    Compare average/max timings before and after changes to main.py.
    """

    def test_move_timing(self, game_file, capsys):
        frames = load_game_frames(game_file)
        assert frames, f"No frames found for {OUR_SNAKE_NAME!r} in {game_file}"

        timings: typing.List[float] = []
        for frame in frames:
            if DEBUG_TURN is not None and frame["turn"] == DEBUG_TURN:
                breakpoint()  # inspect `frame` then `s` to step into our_move()
            buf = io.StringIO()
            t0 = time.perf_counter()
            with contextlib.redirect_stdout(buf):
                result = our_move(frame)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            timings.append(elapsed_ms)
            assert "move" in result, (
                f"move() did not return a 'move' key at turn {frame['turn']}"
            )

        avg_ms = sum(timings) / len(timings)
        max_ms = max(timings)

        with capsys.disabled():
            game_name = os.path.basename(game_file)
            print(f"\n=== {game_name} ({len(timings)} moves) ===")
            for frame, ms in zip(frames, timings):
                if ms >=500:
                    print(f"  !!!!!turn {frame['turn']:4d}: {ms:7.2f}ms")
            print(f"  ---")
            print(f"  average : {avg_ms:.2f}ms")
            print(f"  max     : {max_ms:.2f}ms")
            print(f"  # of moves : {len(timings)}")

        assert avg_ms < 500, (
            f"Average move time {avg_ms:.1f}ms exceeds the 500ms timeout."
        )
