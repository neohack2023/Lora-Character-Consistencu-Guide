import pytest

from game.prison_cell_intro import (
    EscapeMethod,
    Player,
    attempt_break_door,
    attempt_lockpick,
    attempt_persuade_guard,
    attempt_spell_unlock,
    attempt_tunnel_escape,
)


def test_lockpick_success():
    player = Player(items={"Lockpick"}, skills={"lockpicking": 60})
    assert attempt_lockpick(player)
    assert player.escape_method is EscapeMethod.LOCKPICK


def test_lockpick_failure_without_item():
    player = Player(skills={"lockpicking": 60})
    assert not attempt_lockpick(player)
    assert player.escape_method is None


def test_spell_unlock_uses_magicka():
    player = Player(spells={"Unlock I"}, magicka=10)
    assert attempt_spell_unlock(player, cost=5)
    assert player.escape_method is EscapeMethod.SPELL
    assert player.magicka == 5


def test_persuade_guard_threshold():
    player = Player(skills={"speechcraft": 30}, reputation=15)
    assert attempt_persuade_guard(player, threshold=40)
    assert player.escape_method is EscapeMethod.PERSUADE


def test_break_door_by_strength():
    player = Player(strength=80)
    assert attempt_break_door(player, threshold=70)
    assert player.escape_method is EscapeMethod.VIOLENT


def test_tunnel_escape_sets_method():
    player = Player()
    assert attempt_tunnel_escape(player)
    assert player.escape_method is EscapeMethod.TUNNEL
