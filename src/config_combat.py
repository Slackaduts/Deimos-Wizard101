from wizwalker import Client, utils
from wizwalker.combat import CombatCard
from wizwalker.memory.memory_objects.enums import EffectTarget, SpellEffects
from wizwalker.memory.memory_objects.spell_effect import DynamicSpellEffect
from wizwalker.extensions.wizsprinter import CombatConfigProvider
from wizwalker.extensions.wizsprinter.combat_backends.backend_base import BaseCombatBackend
from wizwalker.extensions.wizsprinter.combat_backends.combat_api import CombatConfig, TargetType, SpellType, TemplateSpell
from wizwalker.extensions.wizsprinter.combat_backends.config_backend import get_sprinty_grammar, Lark, TreeToConfig
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
        self.config: CombatConfig = self.parse_config(config_data)

    async def handle_no_cards_given(self):
        raise RuntimeError("Full config fail! Config might be empty or contains only explicit rounds. Consider adding a pass or something else.")
    
    def parse_config(self, file_contents) -> CombatConfig:
        grammar = get_sprinty_grammar()

        parser = Lark(grammar)
        tree = parser.parse(file_contents)
        return self._expand_config(TreeToConfig().transform(tree))



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
    client_to_match = -1
    local_configs: List[str] = []

    for i, line in enumerate(config_lines):
        client_match = re.search(pattern, line)
        if client_match is not None:
            if client_to_match != -1:
                client_configs[client_to_match] = line_seperator.join(local_configs)
            client_to_match = int(client_match.group(1)) - 1
            local_configs.clear()
            continue

        local_configs.append(line)

    #If no client was ever specified, just assign entire config to all clients
    if client_to_match == -1:
        for i in range(fallback_clients):
            client_configs[i] = line_seperator.join(config_lines)

    else:
        client_configs[client_to_match] = line_seperator.join(local_configs)

    return client_configs