"""Flask server wrapper exposing Battlesnake HTTP endpoints."""

import datetime
import json
import logging
import os
import typing

from flask import Flask
from flask import request

_GAME_LOG_DIR = os.path.join(os.path.dirname(__file__), "tests", "test_files")

# game_id -> open file handle
_game_logs: typing.Dict[str, typing.IO] = {}


def _open_game_log(game_state: dict) -> None:
    game_id = game_state["game"]["id"]
    snake_name = game_state["you"]["name"]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{snake_name}_{timestamp}.json"
    os.makedirs(_GAME_LOG_DIR, exist_ok=True)
    path = os.path.join(_GAME_LOG_DIR, filename)
    f = open(path, "w")
    f.write(json.dumps(game_state["game"]) + "\n")
    f.flush()
    _game_logs[game_id] = f


def _append_game_log(game_state: dict) -> None:
    game_id = game_state["game"]["id"]
    f = _game_logs.get(game_id)
    if f:
        f.write(json.dumps(game_state) + "\n")
        f.flush()


def _close_game_log(game_state: dict) -> None:
    game_id = game_state["game"]["id"]
    f = _game_logs.pop(game_id, None)
    if f:
        f.close()


def run_server(handlers: typing.Dict):
    """Run the Battlesnake HTTP server with the provided lifecycle handlers."""
    app = Flask("Battlesnake")

    @app.get("/")
    def on_info():
        """Return Battlesnake metadata."""
        return handlers["info"]()

    @app.post("/start")
    def on_start():
        """Dispatch game start events."""
        game_state = request.get_json()
        handlers["start"](game_state)
        _open_game_log(game_state)
        return "ok"

    @app.post("/move")
    def on_move():
        """Dispatch per-turn move requests."""
        game_state = request.get_json()
        _append_game_log(game_state)
        return handlers["move"](game_state)

    @app.post("/end")
    def on_end():
        """Dispatch game end events."""
        game_state = request.get_json()
        handlers["end"](game_state)
        _close_game_log(game_state)
        return "ok"

    @app.after_request
    def identify_server(response):
        """Attach a server identifier header for Battlesnake tooling."""
        response.headers.set(
            "server", "battlesnake/github/starter-snake-python"
        )
        return response

    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8000"))

    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    print(f"\nRunning Battlesnake at http://{host}:{port}")
    app.run(host=host, port=port)
