from wizwalker import Client
from wizwalker.combat import CombatCard
from wizwalker.memory.memory_objects.enums import EffectTarget, SpellEffects
from wizwalker.memory.memory_objects.spell_effect import DynamicSpellEffect
from wizwalker.extensions.wizsprinter import CombatConfigProvider
from wizwalker.extensions.wizsprinter.combat_backends.backend_base import BaseCombatBackend
from wizwalker.extensions.wizsprinter.combat_backends.combat_api import CombatConfig, TargetType, SpellType, TemplateSpell
from wizwalker.extensions.wizsprinter import SprintyCombat
from typing import List, Dict, Tuple
# from wizwalker.client import Client

import re

class StrCombatConfigProvider(CombatConfigProvider):
    '''
    Handles string-based combat configuration. The GUI handles files so this is modified to just use a string.
    '''
    def __init__(self, config_data: str = "any<damage> @ enemy", cast_time: float = 0.2):
        super(CombatConfigProvider, self).__init__(cast_time) #Bypass init function of parent
        self.filename = "Config"
        self.config: CombatConfig = super().parse_config(config_data)

    async def handle_no_cards_given(self):
        raise RuntimeError("Full config fail! Config might be empty or contains only explicit rounds. Consider adding a pass or something else.")



def delegate_combat_configs(input_data: str, fallback_clients: int = 1, line_seperator: str = "\n") -> Dict[int, str]:
    '''
    Handles turning a raw string of file content into a dict of client combat configs.

    Args:
    - input_data (str): File content to use
    - fallback_clients(int): In the event of no clients specified, use the 
    - line_seperator (str): Symbol or string that seperates lines of the file, newline by default
    '''

    config_lines = input_data.split(line_seperator)
    client_configs: Dict[int, str] = {}

    #Match number in "###pX", where X is a number. This determines the client index. This also strips all whitespace.
    pattern = re.compile(r'###\sp\s*(\d+)')
    prev_index = -1
    prev_match: re.Match = None

    for i, line in enumerate(config_lines):
        client_match = re.search(pattern, line)

        if client_match is not None or i >= len(config_lines) - 1:
            #If this is our first match, simply update the record of previous match and move on
            if prev_match is None:
                prev_index = i
                prev_match = client_match
                continue

            #Only assign client's lines to client combat config
            client_lines = config_lines[prev_index+1:i]
            client_configs[int(prev_match.group(1))] = line_seperator.join(client_lines)
            prev_index = i
            prev_match = client_match

    #If no client was ever specified, just assign entire config to all clients
    if prev_match is None:
        for i in range(fallback_clients):
            client_configs[i] = line_seperator.join(config_lines)

    return client_configs