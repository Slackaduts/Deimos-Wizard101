from wizwalker.memory.memory_objects.enums import SpellEffects, MagicSchool, HangingDisposition
from typing import Dict, Any, List, Tuple, Union, Set

from src.combat_cache import *
from src.combat_math import curve_stat

from enum import Enum
import random
from math import trunc

Number = Union[int, float]

main_schools = ("balance", "death", "life", "myth", "storm", "fire", "ice")
hanging_effect_prefixes = ["hanging", "public_hanging", "aura", "shadow_spell", "death_activated", "delay_cast"]
hanging_effect_paths = [f"get_participant.{p}_effects" for p in hanging_effect_prefixes]

charm_effect_types = {
    SpellEffects.modify_outgoing_damage,
    SpellEffects.modify_outgoing_damage_flat,
    SpellEffects.modify_outgoing_heal,
    SpellEffects.modify_outgoing_heal_flat,
    SpellEffects.modify_outgoing_damage_type,
    SpellEffects.modify_outgoing_armor_piercing,
    SpellEffects.modify_accuracy,
    SpellEffects.dispel,
    # SpellEffects.cloaked_charm
}

ward_effect_types = {
    SpellEffects.modify_incoming_damage,
    SpellEffects.modify_incoming_damage_flat,
    SpellEffects.maximum_incoming_damage,
    SpellEffects.modify_incoming_heal,
    SpellEffects.modify_incoming_heal_flat,
    SpellEffects.modify_incoming_damage_type,
    SpellEffects.modify_incoming_armor_piercing,
    SpellEffects.absorb_damage,
    SpellEffects.absorb_heal,
    SpellEffects.bounce_next,
    SpellEffects.bounce_previous,
    SpellEffects.bounce_back,
    SpellEffects.bounce_all,
    # SpellEffects.cloaked_ward,
}

dot_effect_types = {
    SpellEffects.damage_over_time,
    SpellEffects.deferred_damage,
}

hot_effect_types = {
    SpellEffects.heal_over_time
}


class MagicSchoolID(MagicSchool):
    '''WizWalker MagicSchool enum extended for universal schools.'''
    universal = 80289


class MagicSchoolIndex(Enum):
    '''Converts the name of a magic school to a list index for a list of stats.'''
    MagicSchool.fire = 0
    MagicSchool.ice = 1
    MagicSchool.storm = 2
    MagicSchool.myth = 3
    MagicSchool.life = 4
    MagicSchool.death = 5
    MagicSchool.balance = 6
    MagicSchool.star = 7
    MagicSchool.sun = 8
    MagicSchool.moon = 9
    MagicSchool.gardening = 10
    MagicSchool.shadow = 11
    MagicSchool.fishing = 12
    MagicSchool.cantrips = 13
    MagicSchool.castle_magic = 14
    MagicSchool.whirly_burly = 15


# class OppositeMagicSchool(Enum):
#     MagicSchool.fire = MagicSchool.ice
#     MagicSchool.ice = MagicSchool.fire
#     MagicSchool.storm = MagicSchool.myth
#     MagicSchool.myth = MagicSchool.storm
#     MagicSchool.life = MagicSchool.death
#     MagicSchool.death = MagicSchool.life
#     MagicSchool.balance = MagicSchool.balance
#     MagicSchool.star = MagicSchool.star
#     MagicSchool.sun = MagicSchool.sun
#     MagicSchool.moon = MagicSchool.moon
#     MagicSchool.gardening = MagicSchool.gardening
#     MagicSchool.shadow = MagicSchool.shadow
#     MagicSchool.fishing = MagicSchool.fishing
#     MagicSchool.cantrips = MagicSchool.cantrips
#     MagicSchool.castle_magic = MagicSchool.castle_magic
#     MagicSchool.whirly_burly = MagicSchool.whirly_burly


def clamp(num: Number, min_value: Number, max_value: Number) -> Number:
    return max(min(num, max_value), min_value)


def collapse_effect(subeffects: List[Cache], type_name: str, caster: Cache, target: Cache) -> Cache:
    effect: Cache = None

    match type_name:
        case "RandomSpellEffect" | "RandomPerTargetSpellEffect": #Unless we want to create new permutations for every random spell effect, we should just choose a random effect.
            effect = random.choice(subeffects)

        case "VariableSpellEffect": #Handles per pip spells, like Tempest.
            pip_values = [subeffect["pip_num"] for subeffect in subeffects]
            min_pips = min(pip_values)
            max_pips = max(pip_values)
            pips = clamp(pips, min_pips, max_pips)
            effect = subeffects[pip_values.index(pips)]

        case "HangingConversionSpellEffect":
            pass # TODO: Roshambo shit here

        case "ConditionalSpellEffect":
            pass # TODO: Conditional shit

        case "EffectListSpellEffect":
            pass #TODO: Figure out what this actually means

        case _:
            pass

    return effect



# TODO: Make this handle the subeffects according to top-level effect type (type name, not enum effect type)
def sanitize_effect_list(effects: List[Cache]) -> List[Cache]:
    '''Removes broken/useless effects from a given list of SpellEffects'''
    result_effects = []
    for effect in effects:
        if effect["effect_type"] == SpellEffects.invalid_spell_effect:
            if effect["maybe_effect_list"] is None:
                continue

                


        result_effects.append(effect)

    return result_effects


def remove_used_effects(cache: Cache, effect_list_index: int, used_effect_indexes: List[int]):
    '''Removes used hanging effects from a cache, as specified by a list of used spell/enchantment template IDs. '''
    #TODO: there's probably a way to simplify this logic -slack
    index_offset = 0
    for i in used_effect_indexes:
        cache_remove(cache, f"{hanging_effect_paths[effect_list_index]}.{i - index_offset}")
        index_offset += 1


#TODO: Add global effects
def sim_outgoing_dmg_effects(cache: Cache, damage_type: int, damage: float, pierce: float) -> Tuple[Cache, int, float, float]:

    member_effects: List[Cache] = cache_get_multi(cache, hanging_effect_paths[:4])
    result_cache = Cache

    damage_type_index = MagicSchoolIndex[damage_type].value

    #Outgoing effect handling
    for i, m_effects in enumerate(member_effects):
        used_indexes: List[int] = []
        used_ids: List[Tuple[int, int]] = []
        for m_i, m_effect in enumerate(m_effects):
            if (m_effect["damage_type"] != MagicSchoolID.universal and m_effect["damage_type"] != damage_type) or ids in used_ids:
                continue

            damage = clamp(damage, 0.0, 2000000.0)

            ids = (m_i, m_effect["spell_template_id"], m_effect["enchantment_spell_template_id"])
            param = m_effect["effect_param"]

            match m_effect["effect_type"]: #Keep in mind these effects are reused for auras/shadow, they're not strictly charms
                case SpellEffects.modify_outgoing_damage: #Normal blades/weakness
                    damage *= (param / 100) + 1

                case SpellEffects.modify_outgoing_damage_flat: #Flat damage blades/weakness
                    damage += param

                case SpellEffects.modify_outgoing_armor_piercing: #Pierce blades
                    pierce += param / 100
                    pierce = round(pierce, 2)

                case SpellEffects.modify_outgoing_damage_type: #Prism blade, Old One's Endgame + Lifebane
                    damage_type = param
                    damage_type_index = MagicSchoolIndex[param].value

                case _:
                    continue

            used_indexes.append(m_i)
            used_ids.append(ids)

        # Skip effect removal if it's aura/shadow/etc
        if i > 1:
            continue

        remove_used_effects(result_cache, i, used_indexes)

    return result_cache, damage_type, damage, pierce


def sim_outgoing_heal_effects(cache: Cache, heal_type: int, heal: float) -> Tuple[Cache, float]:
    member_effects: List[Cache] = cache_get_multi(cache, hanging_effect_paths[:4])
    result_cache = Cache

    for i, m_effects in enumerate(member_effects):
        used_indexes: List[int] = []
        used_ids: List[Tuple[int, int]] = []
        for m_i, m_effect in enumerate(m_effects):
            if (m_effect["damage_type"] != MagicSchoolID.universal and m_effect["damage_type"] != heal_type) or ids in used_ids:
                continue

            heal = clamp(heal, 0.0, 2000000.0)

            ids = (m_i, m_effect["spell_template_id"], m_effect["enchantment_spell_template_id"])
            param = m_effect["effect_param"]

            match m_effect["effect_type"]: #Keep in mind these effects are reused for auras/shadow, they're not strictly charms
                case SpellEffects.modify_outgoing_heal: #Normal heal charms
                    heal *= (param / 100) + 1

                case SpellEffects.modify_outgoing_heal_flat: #Flat heal charms
                    heal += param

                case _:
                    continue

            used_indexes.append(m_i)
            used_ids.append(ids)

        # Skip effect removal if it's aura/shadow/etc
        if i > 1:
            continue

        remove_used_effects(result_cache, i, used_indexes)


# #TODO: Add global effects
def sim_incoming_dmg_effects(cache: Cache, damage_type: int, damage: float, pierce: float) -> Tuple[Cache, int, float, float]:
    member_effects: List[Cache] = cache_get_multi(cache, hanging_effect_paths[:4])
    result_cache = cache

    damage_type_index = MagicSchoolIndex[damage_type].value

    #Incoming effect (target) effect handling
    for i, m_effects in enumerate(member_effects):
        used_indexes: List[int] = []
        used_ids: List[Tuple[int, int]] = []
        for m_i, m_effect in enumerate(m_effects):
            if (m_effect["damage_type"] != MagicSchoolID.universal and m_effect["damage_type"] != damage_type) or ids in used_ids:
                continue

            damage = clamp(damage, 0.0, 2000000.0)

            ids = (m_i, m_effect["spell_template_id"], m_effect["enchantment_spell_template_id"])
            param = m_effect["effect_param"]
            max_pierce = pierce

            match m_effect["effect_type"]:
                case SpellEffects.modify_incoming_damage: #Shields + traps
                    if param < 0:
                        param += pierce
                        pierce += m_effect["effect_param"]
                        pierce = round(pierce, 2)
                        clamp(pierce, 0, max_pierce)
                        clamp(param, m_effect["effect_param"], 0)

                    damage *= (param / 100) + 1

                case SpellEffects.modify_incoming_damage_flat: #Flat resist traps/shields??
                    damage += param

                case SpellEffects.absorb_damage: #Spirit armor, frozen armor, etc
                    if damage < param:
                        cache_modify(result_cache, param - damage, f"{hanging_effect_paths[i]}.{m_i}.effect_param") #Modify absorb value if damage isn't enough to remove it
                        damage = 0
                        continue

                    damage += param

                case SpellEffects.modify_incoming_armor_piercing: #Pierce traps?
                    pierce += param / 100
                    pierce = round(pierce, 2)

                case SpellEffects.modify_incoming_damage_type: #Prisms
                    damage_type = param
                    damage_type_index = MagicSchoolIndex[param].value

                case _:
                    continue

            used_indexes.append(m_i)
            used_ids.append(ids)

        # Skip effect removal if it's aura/shadow/etc
        if i > 1:
            continue

        remove_used_effects(result_cache, i, used_indexes)

    return result_cache, damage_type, damage, pierce


#TODO: Add global effects
def sim_incoming_heal_effects(cache: Cache, heal_type: float, heal: float) -> Tuple[Cache, float]:
    member_effects: List[Cache] = cache_get_multi(cache, hanging_effect_paths[:4])
    result_cache = cache

    #Incoming effect (target) effect handling
    for i, m_effects in enumerate(member_effects):
        used_indexes: List[int] = []
        used_ids: List[Tuple[int, int]] = []
        for m_i, m_effect in enumerate(m_effects):
            if (m_effect["damage_type"] != MagicSchoolID.universal and m_effect["damage_type"] != heal_type) or ids in used_ids:
                continue

            heal = clamp(heal, 0.0, 2000000.0)

            ids = (m_i, m_effect["spell_template_id"], m_effect["enchantment_spell_template_id"])
            param = m_effect["effect_param"]

            match m_effect["effect_type"]:
                case SpellEffects.modify_incoming_heal: #Heal traps/shields? (Lord of Night)
                    heal *= (param / 100) + 1

                case SpellEffects.modify_incoming_heal_flat: #Flat heal resist ward?
                    heal += param

                case SpellEffects.absorb_heal: #Heal absorb? Akin to heal flat resist?
                    if heal < param:
                        cache_modify(result_cache, param - heal, f"{hanging_effect_paths[i]}.{m_i}.effect_param") #Modify absorb value if heal isn't enough to remove it
                        heal = 0
                        continue

                    heal += param

                case _:
                    continue

            used_indexes.append(m_i)
            used_ids.append(ids)

        # Skip effect removal if it's aura/shadow/etc
        if i > 1:
            continue

        remove_used_effects(result_cache, i, used_indexes)

    return result_cache, heal


def calc_crit(crit_rating: float, block_rating: float, caster_level: int, target_level: int, is_pvp: bool = False) -> Tuple[float]:
    if is_pvp: #PVP specific calculation
        m_b = 5 * block_rating
        crit_multiplier = 2 - (m_b / (crit_rating + m_b))
        m_c = 12 * crit_rating
        crit_chance = (caster_level / 185) * (m_c / (m_c + block_rating))
        block_chance = (target_level / 185) * (block_rating / (block_rating + m_c))

    else: #PVE calculation
        m_b = 3 * block_rating
        crit_multiplier = 2 - (m_b / (crit_rating + m_b))
        m_c = 3 * crit_rating
        crit_chance = m_c / (m_c + block_rating)
        crit_chance = clamp(crit_chance, 0.0, 0.95)
        block_chance = 0.4 * (block_rating / (block_rating + m_c))

    return crit_multiplier, crit_chance, block_chance


def sim_damage(duel: Cache, caster: Cache, target: Cache, effect: Cache, crit_threshold: float = 0.8) -> Tuple[Cache, Cache, float]:
    '''Simulates damage of any kind on a target.'''
    target_result = target
    caster_result = caster

    #For easy access of stat lists, as we only want 1 particular stat
    damage_type = effect["damage_type"]
    damage_type_index = MagicSchoolIndex[damage_type].value

    #Damage, pierce, and resist stats
    #Get and curve damage
    damage = effect["effect_param"]
    dmg_percent_stat = cache_get(caster, "get_stats.dmg_bonus_percent")[damage_type_index] + cache_get(caster, "get_stats.dmg_bonus_percent_all")
    dmg_percent_stat = round(dmg_percent_stat, 2)
    if caster["is_player"]:
        dmg_percent_stat = curve_stat(dmg_percent_stat, duel["damage_limit"], duel["d_k0"], duel["d_n0"])
    damage *= 1 + dmg_percent_stat
    damage += cache_get(caster, "get_stats.dmg_bonus_flat")[damage_type_index] + cache_get(caster, "get_stats.dmg_bonus_flat_all")

    #Get and curve target resist
    resist = cache_get(target, "get_stats.dmg_reduce_percent")[damage_type_index] + cache_get(target, "get_stats.dmg_reduce_percent_all")
    if target["is_player"]:
        resist = curve_stat(resist, duel["resist_limit"], duel["r_k0"], duel["r_n0"])
    resist = round(resist, 2)

    #Get pierce
    pierce = cache_get(caster, "get_stats.ap_bonus_percent")[damage_type_index] + cache_get(caster, "get_stats.ap_bonus_percent_all")
    pierce = round(pierce, 2)

    #Stats for Critical calculation
    caster_level = caster["level"]
    caster_crit = cache_get(caster, "get_stats.critical_hit_rating_by_school")[damage_type_index]
    caster_crit += cache_get(caster, "get_stats.critical_hit_rating_all")
    target_level = target["level"]
    target_block = cache_get(target, "get_stat.block_rating_by_school")[damage_type_index]
    target_block += cache_get(target, "get_stats.block_rating_all")

    #Critical and block calculation
    is_pvp = duel["pvp"] or duel["raid"]
    crit_damage_multiplier, crit_chance, block_chance = calc_crit(caster_crit, target_block, caster_level, target_level, is_pvp)

    #If our crit chance is over threshold, we crit.
    if effect["effect_type"] == SpellEffects.damage_no_crit: #Handles effect that never crits
        pass

    elif crit_chance >= crit_threshold * (1 - block_chance):
        damage *= crit_damage_multiplier

    # Outgoing damage hanging effects
    caster_result, damage_type, damage, pierce = sim_outgoing_dmg_effects(caster_result, damage_type, damage, pierce)

    #Incoming damage effects
    if caster["owner_id"] == target["owner_id"]: #If we are the caster and target, ignore target and only use caster
        caster_result, damage_type, damage, pierce = sim_incoming_dmg_effects(caster_result, damage_type, damage, pierce)

    else: #If the target is not ourselves, handle them normally
        target_result, damage_type, damage, pierce = sim_incoming_dmg_effects(target_result, damage_type, damage, pierce)

    damage_type_index = MagicSchoolIndex[damage_type].value

    # Flat resist
    damage -= cache_get(target, "get_stats.dmg_reduce_flat")[damage_type_index] + cache_get(target, "get_stats.dmg_reduce_flat_all")
    damage = clamp(damage, 0.0, 2000000.0) #Min/max damage possible in wiz

    # Percent resist handling
    if resist > 0:
        resist -= pierce
        if resist <= 0: #If we have more pierce than needed, we don't need to touch damage.
            resist = 1

        else: #If we don't have enough pierce, then turn resist into a reg multiplier on damage
            resist = 1 - resist

    else: #Account for boost, which is just negative resist. Turns it into a multipler on damage.
        resist = abs(resist) + 1

    damage *= resist #Apply resist to damage

    #Decrement health by damage, and clamp
    target_result["health"] = clamp(target_result["health"] - damage, 0, target_result["health"])

    return (caster_result, target_result, damage)


# TODO: Make sim_damage use this
def sim_incoming_damage(duel: Cache, target: Cache, damage_type: int, damage: float) -> Tuple[Cache, int, float]:
    '''Simulates pure damage on a member cache, only on the target side. Useful for effect handling.'''
    target_result = target

    damage_type_index = MagicSchoolIndex[damage].value

    #Get and curve target resist
    resist = cache_get(target, "get_stats.dmg_reduce_percent")[damage_type_index] + cache_get(target, "get_stats.dmg_reduce_percent_all")
    if target["is_player"]:
        resist = curve_stat(resist, duel["resist_limit"], duel["r_k0"], duel["r_n0"])
    resist = round(resist, 2)

    target_result, damage_type, damage, pierce = sim_incoming_dmg_effects(target_result, damage_type, damage, 0.0)

    # Flat resist
    damage -= cache_get(target, "get_stats.dmg_reduce_flat")[damage_type_index] + cache_get(target, "get_stats.dmg_reduce_flat_all")
    damage = clamp(damage, 0.0, 2000000.0) #Min/max damage possible in wiz

    # Percent resist handling
    if resist > 0:
        resist -= pierce
        if resist <= 0: #If we have more pierce than needed, we don't need to touch damage.
            resist = 1

        else: #If we don't have enough pierce, then turn resist into a reg multiplier on damage
            resist = 1 - resist

    else: #Account for boost, which is just negative resist. Turns it into a multipler on damage.
        resist = abs(resist) + 1

    damage *= resist #Apply resist to damage

    #Decrement health by damage, and clamp
    target_result["health"] = clamp(target_result["health"] - damage, 0, target_result["health"])

    return target_result, damage


def get_multi_effects(effects: Iterable[Cache], valid_types: Set[SpellEffects], disposition: HangingDisposition = HangingDisposition.both) -> Tuple[List[Cache], List[int]]:
    '''Filters an iterable of SpellEffect caches based on if the type of the effect lies within a set of valid effect types, and by a specific HangingDisposition.'''
    matches = []
    match_indices = []

    for i, effect in enumerate(effects):
        if effect["effect_type"] not in matches:
            continue

        match disposition:
            case HangingDisposition.beneficial:
                if effect["effect_param"] < 0:
                    continue

            case HangingDisposition.harmful:
                if effect["effect_param"] >= 0:
                    continue

            case _:
                pass

        matches.append(effect)
        match_indices.append(i)

    return matches, match_indices


def sim_heal(duel: Cache, caster: Cache, target: Cache, effect: Cache, crit_threshold: float = 0.8) -> Tuple[Cache, Cache, float]:
    '''Simulates a heal effect on given caster/target member caches.'''
    caster_result = caster
    target_result = target

    heal_type = effect["damage_type"]
    heal_type_index = MagicSchoolIndex[heal_type].value

    heal = effect["effect_param"]
    heal_percent = cache_get(caster, "get_participant.get_stats.heal_bonus_percent")[heal_type_index] + cache_get(caster, "get_participant.get_stats.heal_bonus_percent_all")
    heal *= 1 + heal_percent

    #Stats for Critical calculation
    caster_level = caster["level"]
    caster_crit = cache_get(caster, "get_stats.critical_hit_rating_by_school")[heal_type_index]
    caster_crit += cache_get(caster, "get_stats.critical_hit_rating_all")
    target_level = target["level"]
    target_block = cache_get(target, "get_stat.block_rating_by_school")[heal_type_index]
    target_block += cache_get(target, "get_stats.block_rating_all")

    #Critical and block calculation
    is_pvp = duel["pvp"] or duel["raid"]
    crit_heal_multiplier, crit_chance, _ = calc_crit(caster_crit, target_block, caster_level, target_level, is_pvp)

    #If crit chance is greater than threshold, we crit.
    if crit_chance >= crit_threshold:
        heal *= crit_heal_multiplier

    # Outgoing damage hanging effects
    caster_result, damage = sim_outgoing_heal_effects(caster_result, heal_type, damage)

    #Incoming heal stat application
    heal_inc_percent = cache_get(caster, "get_participant.get_stats.heal_inc_bonus_percent")[heal_type_index] + cache_get(caster, "get_participant.get_stats.heal_inc_bonus_percent_all")
    heal *= 1 + heal_inc_percent

    #Incoming damage effects and health increase
    if caster["owner_id"] == target["owner_id"]: #If we are the caster and target, ignore target and only use caster
        caster_result, heal = sim_incoming_heal_effects(caster_result, heal_type, heal)
        caster_result["health"] = clamp(caster_result["health"] + heal, 0, caster_result["max_health"])

    else: #If the target is not ourselves, handle them normally
        target_result, heal = sim_incoming_heal_effects(target_result, heal_type, heal)
        target_result["health"] = clamp(target_result["health"] + heal, 0, target_result["max_health"])

    return caster_result, target_result, heal


def sim_effect(duel: Cache, caster: Cache, target: Cache, effect: Cache) -> Cache:
    '''Simulates an effect being applied to a specific member cache.'''
    target_result = target
    caster_result = caster

    def _transfer_hanging_effects(origin: List[Cache], recipient: List[Cache], amount: int, valid_types: List[SpellEffects], disposition: HangingDisposition = HangingDisposition.both):
        _, effect_indices = get_multi_effects(origin, valid_types, disposition)
        for i in range(amount):
            if len(effect_indices) < amount - i: #TODO: Verify if this actually works to check if we have enough effects
                break
            effect_index = effect_indices.pop(0)
            effect = origin.pop(effect_index - i)
            recipient.insert(0, effect)


    def _pop_hanging_effects(origin: List[Cache], amount: int, valid_types: List[SpellEffects], disposition: HangingDisposition = HangingDisposition.both) -> List[Cache]:
        _, effect_indices = get_multi_effects(origin, valid_types, disposition)
        effects = []
        for i in range(amount):
            if len(effect_indices) < amount < i:
                break

            effect_index = effect_indices.pop(0)
            effect = origin.pop(effect_index - i)
            effects.append(effect)

        return effects

    caster_pips = cache_get(caster_result, "get_participant.pip_count")
    caster_total_spips = sum((caster_pips[f"{s}_pips"] for s in main_schools))
    caster_effects: List[Cache] = cache_get_multi(caster_result, hanging_effect_paths)
    caster_effects = sanitize_effect_list(caster_effects)

    target_pips = cache_get(target_result, "get_participant.pip_count")
    target_total_spips = sum((target_pips[f"{s}_pips"] for s in main_schools))
    target_effects: List[Cache] = cache_get_multi(target_result, hanging_effect_paths)
    target_effects = sanitize_effect_list(target_effects)

    #Simulate the effect of every possible spell effect on the cache.
    match effect["effect_type"]:
        case SpellEffects.damage: #Regular hits
            caster_result, target_result, _ = sim_damage(duel, caster_result, target_result, effect)

        case SpellEffects.damage_no_crit: #Incoming
            caster_result, target_result, _ = sim_damage(duel, caster_result, target_result, effect, crit_threshold = 2.0)

        case SpellEffects.steal_health:
            caster_result, target_result, damage = sim_damage(duel, caster_result, target_result, effect)
            caster_result["health"] += damage * effect["heal_modifier"]

        case SpellEffects.damage_per_total_pip_power: #Per ENEMY pips, like mana burn
            target_total_pip_value = (target_total_spips * 2) + (target_pips["power_pips"] * 2) + target_pips["generic_pips"]
            effect["effect_param"] *= target_total_pip_value
            caster_result, target_result, _ = sim_damage(duel, caster_result, target_result, effect)

        case SpellEffects.heal:
            caster_result, target_result, _ = sim_heal(duel, caster_result, target_result, effect)

        case SpellEffects.heal_percent: #This might be a tad sussy. -slack
            effect["effect_param"] /= 100
            effect["effect_param"] *= target_result["max_health"]
            caster_result, target_result, _ = sim_heal(duel, caster_result, target_result, effect)

        case SpellEffects.set_heal_percent: #TODO: Handle this, and find a spell where its used.
            pass

        case SpellEffects.reduce_over_time:
            # TODO: Simplify this
            target_dots, dot_indices = filter_caches(target_effects[0], {"effect_type": SpellEffects.damage_over_time})
            for dot, i in zip(target_dots, dot_indices):
                dot["effect_param"] -= effect["effect_param"]
                cache_modify(target_result, dot, f"{hanging_effect_paths[0]}.{i}")

        case SpellEffects.detonate_over_time: #Detonate, Incindiate, Solomon Crane, some fire utility paths on R1-6
            # TODO: Simplify this
            dots = _pop_hanging_effects(target_effects[0], effect["effect_param"], dot_effect_types, effect["disposition"])
            for dot in dots:
                target_result = sim_incoming_damage(duel, target_result, dot["damage_type"], dot["effect_param"] * effect["heal_modifier"])

        case SpellEffects.push_charm:
            _transfer_hanging_effects(caster_effects[0], target_effects[0], effect["effect_param"], charm_effect_types, effect["disposition"])

        case SpellEffects.steal_charm:
            _transfer_hanging_effects(target_effects[0], caster_effects[0], effect["effect_param"], charm_effect_types, effect["disposition"])

        case SpellEffects.push_ward:
            _transfer_hanging_effects(caster_effects[0], target_effects[0], effect["effect_param"], ward_effect_types, effect["disposition"])

        case SpellEffects.steal_ward:
            _transfer_hanging_effects(target_effects[0], caster_effects[0], effect["effect_param"], ward_effect_types, effect["disposition"])

        case SpellEffects.push_over_time:
            _transfer_hanging_effects(caster_effects[0], target_effects[0], effect["effect_param"], dot_effect_types, effect["disposition"])

        case SpellEffects.steal_over_time:
            _transfer_hanging_effects(target_effects[0], caster_effects[0], effect["effect_param"], dot_effect_types, effect["disposition"])

        case SpellEffects.swap_all: #Disjunction?
            caster_temp = caster_effects[0]
            caster_effects[0] = target_effects[0]
            target_effects[0] = caster_temp

        case SpellEffects.swap_charm:
            caster_charms = _pop_hanging_effects(caster_effects[0], effect["effect_param"], charm_effect_types, effect["disposition"])
            target_charms = _pop_hanging_effects(target_effects[0], effect["effect_param"], charm_effect_types, effect["disposition"])

            caster_effects[0] = target_charms + caster_effects[0]
            target_effects[0] = caster_charms + target_effects[0]

        case SpellEffects.swap_ward:
            caster_wards = _pop_hanging_effects(caster_effects[0], effect["effect_param"], ward_effect_types, effect["disposition"])
            target_wards = _pop_hanging_effects(target_effects[0], effect["effect_param"], ward_effect_types, effect["disposition"])

            caster_effects[0] = target_wards + caster_effects[0]
            target_effects[0] = caster_wards + target_effects[0]

        case SpellEffects.swap_over_time:
            caster_dots = _pop_hanging_effects(caster_effects[0], effect["effect_param"], dot_effect_types, effect["disposition"])
            target_dots = _pop_hanging_effects(target_effects[0], effect["effect_param"], dot_effect_types, effect["disposition"])

            caster_effects[0] = target_dots + caster_effects[0]
            target_effects[0] = caster_dots + target_effects[0]

        case SpellEffects.clue:
            pass

        case SpellEffects.delay_cast:
            pass

        case SpellEffects.modify_card_cloak:
            pass

        case SpellEffects.modify_card_damage:
            pass

        case SpellEffects.modify_card_accuracy:
            pass

        case SpellEffects.modify_card_mutation:
            pass

        case SpellEffects.modify_card_rank:
            pass

        case SpellEffects.modify_card_armor_piercing:
            pass

        case SpellEffects.summon_creature:
            pass

        case SpellEffects.teleport_player:
            pass

        case SpellEffects.reshuffle:
            pass

        case SpellEffects.modify_pips:
            pass #TODO: Make a mod pips function

        case _:
            target_effects.insert(0, effect)



spip_order = [
    "balance_pips",
    "death_pips",
    "fire_pips",
    "ice_pips",
    "life_pips",
    "myth_pips",
    "storm_pips",
]

pip_order = [
    "generic_pips",
    "power_pips"
]

all_pip_order = pip_order + spip_order

def generate_pip_list(pip_cache: Cache) -> Tuple[List[str], int]:
    '''
    Converts a pip cache to an ordered list of pips, as they would appear in game, and the shadow pip count.
    Args:
    - pip_cache (Cache): Cache of the DynamicPipCount object.
    '''
    pip_list = []
    for pip_type in all_pip_order:
        pip_num = pip_cache["pip_type"]
        if not pip_num:
            continue

        for _ in range(pip_num):
            pip_list.append(pip_type)

    return pip_list, pip_cache["shadow_pips"]


def clamp_pips(pip_cache: Cache, pip_type: str) -> Tuple[Cache, int]:
    '''
    Clamps a specific pip type of a pip cache.\n
    Args:
    - pip_cache (Cache): Cache of the DynamicPipCount object.
    - pip_type (str): String name of the pip type, as a key of the pip_cache Cache.
    '''

    pip_cache_result = pip_cache
    pip_cache_result[pip_type] = 0 #Used for getting minimum pip list

    min_pip_list, shadow_pips = generate_pip_list(pip_cache_result)
    pip_cache_result["shadow_pips"] = clamp(shadow_pips, 0, 2) #Ensure shads are within range

    max_specific_pips = 7 - len(min_pip_list)
    if max_specific_pips <= 0:
        return pip_cache_result, shadow_pips

    pip_cache_result[pip_type] = clamp(pip_cache[pip_type], 0, max_specific_pips)

    return pip_cache_result, shadow_pips


def sim_add_pips(pip_cache: Cache, pip_type: str, param: int) -> Cache:
    pip_cache_result = pip_cache
    pip_cache_result[pip_type] += param
    pip_cache_result, _ = clamp_pips(pip_cache_result, pip_type)
    return pip_cache_result


def sim_remove_pips(pip_cache: Cache, pip_type: str, param: int) -> Cache:
    pip_cache_result = pip_cache
    # TODO: THIS ENTIRE FUNCTION


def sim_modify_pips(pip_cache: Cache, pip_type: str, param: int, pip_school: int = MagicSchoolID.universal) -> Cache:
    pip_cache_result = pip_cache

    if pip_type == "shadow_pips":
        pip_cache_result[pip_type] = clamp(pip_cache[pip_type], 0, 2)
        return pip_cache_result
    
    # TODO: THIS ENTIRE FUNCTION




    # def _sim_remove_pips(pip_cache: Cache, pip_type: str)

    return pip_cache_result





# Pip -> power pip -> fire pip -> ice pip
