"""Basic prison cell escape mechanics for a Daggerfall-inspired prototype.

This module models a few different escape routes from a prison cell. It is not a
full game implementation but provides enough structure to experiment with the
intro sequence logic described in the design plan.

Escape methods are represented using :class:`EscapeMethod` to avoid fragile
string comparisons in calling code.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Set


class EscapeMethod(Enum):
    """Enumerates the ways the player can escape the cell."""

    LOCKPICK = "Lockpick"
    SPELL = "Spell"
    PERSUADE = "Persuade"
    VIOLENT = "Violent"
    TUNNEL = "Tunnel"


@dataclass
class Player:
    """Simple representation of the player during the prison intro."""

    items: Set[str] = field(default_factory=set)
    skills: Dict[str, int] = field(default_factory=dict)
    spells: Set[str] = field(default_factory=set)
    magicka: int = 0
    strength: int = 0
    reputation: int = 0
    escape_method: Optional[EscapeMethod] = None

    def has_item(self, item: str) -> bool:
        return item in self.items

    def knows_spell(self, spell: str) -> bool:
        return spell in self.spells


def attempt_lockpick(player: Player, difficulty: int = 50) -> bool:
    """Attempt to unlock the cell door with a lockpick."""
    if player.has_item("Lockpick") and player.skills.get("lockpicking", 0) >= difficulty:
        player.escape_method = EscapeMethod.LOCKPICK
        return True
    return False


def attempt_spell_unlock(player: Player, cost: int = 5) -> bool:
    """Attempt to open the door with a spell."""
    if player.knows_spell("Unlock I") and player.magicka >= cost:
        player.magicka -= cost
        player.escape_method = EscapeMethod.SPELL
        return True
    return False


def attempt_persuade_guard(player: Player, threshold: int = 40) -> bool:
    """Attempt to persuade the guard to open the door."""
    effective_score = player.skills.get("speechcraft", 0) + player.reputation
    if effective_score >= threshold:
        player.escape_method = EscapeMethod.PERSUADE
        return True
    return False


def attempt_break_door(player: Player, threshold: int = 70) -> bool:
    """Attempt to break the door using brute force."""
    if player.strength >= threshold:
        player.escape_method = EscapeMethod.VIOLENT
        return True
    return False


def attempt_tunnel_escape(player: Player, has_tunnel: bool = True) -> bool:
    """Attempt to escape through a secret tunnel."""
    if has_tunnel:
        player.escape_method = EscapeMethod.TUNNEL
        return True
    return False
