#!/usr/bin/env python3

import logging
import re
import shlex
import sys
from datetime import datetime
from enum import Enum, auto


logger = logging.getLogger(__name__)

MAX_EDGE = 20
MIN_EDGE = 2
EDGE = MAX_EDGE

MAX_SOLDIERS = EDGE ** 2
MIN_SOLDIERS = 2
SOLDIERS = MIN_SOLDIERS

PROMPT = "time=%t, round=%r)> "

PROMPT_MAP = {
    "t": lambda _: datetime.now().strftime("%s"),
    "r": lambda g: g.round,
}


class Game:
    def __init__(self, config):
        self._actions = {
            "get": GetSetting,
            "quit": QuitGame,
            "set": SetSetting,
        }
        self._config = None
        self._prompt_map = PROMPT_MAP
        self._round = 0
        self._state = None

        self.config = config
        self.state = GameState.UNSTARTED

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config

    def get_user_input(self):
        sys.stdout.write(self.prompt)
        return input()

    @property
    def has_started(self):
        return self.state in [GameState.STARTING, GameState.STARTED,]

    @property
    def has_stopped(self):
        return self.state in [GameState.STOPPED,]

    def process_user_input(self, user_input):
        stripped_input = user_input.strip()
        output = None

        if not user_input:
            return

        action, *arguments = shlex.split(stripped_input)

        try:
            output = self._actions[action](self).run(*arguments)
        except KeyError as exc:
            sys.stderr.write(f"ERROR: Unknown action: {action}\n")
        except GameActionError as exc:
            sys.stderr.write(f"ERROR: {exc}\n")

        if output:
            sys.stdout.write(f"{output}\n")

        return

    @property
    def prompt(self):
        return re.sub(
            f"(?:%([{''.join(self.prompt_map.keys())}]))",
            lambda m: str(self.prompt_map[m.group(1)](self)),
            self.config.prompt,
        )

    @property
    def prompt_map(self):
        return self._prompt_map

    @property
    def round(self):
        return self._round

    def start(self):
        self.state = GameState.STARTING
        # <…>
        self.state = GameState.STARTED

    def stop(self):
        self.state = GameState.STOPPING
        # <…>
        self.state = GameState.STOPPED

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state
        logger.debug(f'"state" set to {self.state.name}')


class GameError(Exception):
    pass


class GameConfig:
    def __init__(self, edge=EDGE, prompt=PROMPT, soldiers=SOLDIERS):
        self._edge = None
        self._prompt = None
        self._soldiers = None

        self.edge = edge
        self.prompt = prompt
        self.soldiers = soldiers

    @property
    def edge(self):
        return self._edge

    @edge.setter
    def edge(self, edge):
        self._edge = edge
        logger.debug(f'"edge" set to {self.edge}')

    @property
    def prompt(self):
        return self._prompt

    @prompt.setter
    def prompt(self, prompt):
        self._prompt = prompt
        logger.debug(f'"prompt" set to {self.prompt}')

    @property
    def soldiers(self):
        return self._soldiers

    @soldiers.setter
    def soldiers(self, soldiers):
        self._soldiers = soldiers
        logger.debug(f'"soldiers" set to {self.soldiers}')

    def validate(self):
        if type(self.edge) != int:
            raise TypeError('"edge" must be of type integer')

        if type(self.soldiers) != int:
            raise TypeError('"soldiers" must be of type integer')

        if self.edge < MIN_EDGE or self.edge > MAX_EDGE:
            raise ValueError(
                f'"edge" must be between {MIN_EDGE} and {MAX_EDGE}'
            )

        if self.soldiers < MIN_SOLDIERS or self.soldiers > MAX_SOLDIERS:
            raise ValueError(
                f'"soldiers" must be between {MIN_SOLDIERS} and {MAX_SOLDIERS}'
            )


class GameAction:
    def __init__(self, game):
        self._game = game


class GameActionError(GameError):
    pass


class GetSetting(GameAction):
    def run(self, setting=None):
        if setting is None:
            raise GameActionError(f"Missing argument: setting")

        for _property, _value in self._game.config.__class__.__dict__.items():
            if _property == setting and isinstance(_value, property):
                return repr(getattr(self._game.config, setting))
        else:
            raise GameActionError(f"Unknown setting: {setting}")


class SetSetting(GameAction):
    def run(self, setting=None, value=None):
        if setting is None:
            raise GameActionError(f"Missing argument: setting")

        if value is None:
            raise GameActionError(f"Missing argument: value")

        for _property, _value in self._game.config.__class__.__dict__.items():
            if _property != setting or not isinstance(_value, property):
                continue

            try:
                return setattr(
                    self._game.config,
                    setting,
                    type(getattr(self._game.config, setting))(value),
                )
            except ValueError:
                raise GameActionError(
                    f"Illegal value for setting: {setting}"
                )
        else:
            raise GameActionError(f"Unknown setting: {setting}")


class QuitGame(GameAction):
    def run(self):
        self._game.stop()


class GameState(Enum):
    UNSTARTED = auto()
    STARTING = auto()
    STARTED = auto()
    STOPPING = auto()
    STOPPED = auto()


def main():
    logger.addHandler(logging.StreamHandler(sys.stderr))
    logger.setLevel(logging.DEBUG)

    config = GameConfig()
    config.validate()

    game = Game(config)
    game.start()

    try:
        while game.has_started and not game.has_stopped:
            game.process_user_input(game.get_user_input())
    except (EOFError, KeyboardInterrupt):
        sys.stdout.write("\n")
        game.stop()
    finally:
        pass


if __name__ == "__main__":
    sys.exit(main())
