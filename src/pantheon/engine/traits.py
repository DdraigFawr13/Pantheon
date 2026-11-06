"""Class traits the engine runs (D-044). Each is data in `world/data/combat.yaml`; this module reads it.

Every bonus here feeds the same check calculation as the odds on screen (GAME-02), so a trait shows on
an option before the player picks it.
"""

from __future__ import annotations

from pantheon.engine.state import GameState
from pantheon.world.schemas import Evolution, GameData, Skill, Trait

_ATTACK = "attack"


def trait_of(state: GameState, data: GameData) -> Trait | None:
    """The character's class trait; an evolved class keeps its base class's trait."""
    cls = data.class_of(state.class_id)
    if cls is None:
        return None
    base = cls.from_class if isinstance(cls, Evolution) else cls.id
    return data.combat.traits.get(base)


def needs_attunement(state: GameState, data: GameData) -> bool:
    trait = trait_of(state, data)
    return bool(trait and trait.attunements) and state.attunement is None


def skill_data(data: GameData, skill: str | None) -> Skill | None:
    name = (skill or "").lower()
    return next((s for s in data.skills if s.id == name), None)


def skill_cost(state: GameState, data: GameData, skill: Skill) -> int:
    """A skill's cost after the class trait's discounts, rounded in the player's favour."""
    trait = trait_of(state, data)
    if trait is None or skill.pool is None:
        return skill.cost
    percent = trait.pool_discount_percent.get(skill.pool, 0)
    if skill.affinity is not None and skill.affinity == state.attunement and skill.pool == "mana":
        percent += trait.attuned_discount_percent
    return skill.cost - skill.cost * min(percent, 100) // 100


def defence_stat(state: GameState, data: GameData, stat: str, move: str) -> str:
    """Still Centre: guard and flee roll the best of the trait's stats when that beats the one named."""
    trait = trait_of(state, data)
    if move == _ATTACK or trait is None or not trait.defence_stats or "armour" in state.equipped:
        return stat  # Still Centre needs the character unarmoured.
    return max((stat, *trait.defence_stats), key=lambda s: state.stats[s])


def bonuses(
    state: GameState,
    data: GameData,
    stat: str,
    skill: str | None,
    move: str | None = None,
    target: str | None = None,
    activating: bool = False,
) -> list[tuple[str, int]]:
    """Each trait bonus on this check, as (trait name, amount). `activating`: the move uses the trait now."""
    found: list[tuple[str, int]] = []
    weapon = data.item_of(state.equipped.get("weapon", ""))
    if weapon is not None and weapon.attack_bonus and move == _ATTACK and state.fight is not None:
        found.append((weapon.name, weapon.attack_bonus))
    trait = trait_of(state, data)
    if trait is None:
        return found
    used = skill_data(data, skill)
    if trait.attuned_bonus and used and used.affinity and used.affinity == state.attunement:
        found.append((trait.name, trait.attuned_bonus))
    fight = state.fight
    if fight is None or move is None:
        return found
    attack = move == _ATTACK
    if state.hp * 2 < state.max_hp:
        amount = trait.low_hp_attack_bonus if attack else trait.low_hp_defence_bonus
        if amount:
            found.append((trait.name, amount))
    if attack and trait.attack_bonus_per_success and fight.momentum:
        found.append((trait.name, fight.momentum))
    if attack and trait.ambush_attack_bonus and fight.ambush and not fight.opened:
        found.append((trait.name, trait.ambush_attack_bonus))
    if attack and trait.studied_attack_bonus and fight.exchange >= trait.studied_from_exchange:
        found.append((trait.name, trait.studied_attack_bonus))
    cursing = activating and trait.once_per_fight == "curse"
    if attack and trait.curse_attack_bonus and (fight.cursed == target or cursing):
        found.append((trait.name, trait.curse_attack_bonus))
    in_form = fight.form or (activating and trait.once_per_fight == "form")
    if in_form and stat in trait.form_stats:
        found.append((trait.name, trait.form_bonus))
    return found


def next_momentum(state: GameState, data: GameData, attacked: bool, landed: bool) -> int:
    """Momentum after an exchange: a clean attack builds it, a costly or failed one loses it."""
    trait = trait_of(state, data)
    fight = state.fight
    if fight is None or trait is None or not trait.attack_bonus_per_success:
        return 0
    if not attacked:
        return fight.momentum
    if not landed:
        return 0
    return min(trait.attack_bonus_cap, fight.momentum + trait.attack_bonus_per_success)
