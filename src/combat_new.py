from typing import List, Dict, Any, Set, Tuple, Iterable

from wizwalker import Client
from wizwalker.combat import CombatHandler, CombatCard
from wizwalker.utils import maybe_wait_for_any_value_with_timeout

from src.utils import class_snapshot
from src.combat_cache import cache_get, cache_get_multi, filter_caches, Cache

import pyperclip
import yaml


def member_cache_adv_time_sim(cache: Cache, rounds: int = 1, ppip_threshold: float = 0.85) -> Cache:
    result_cache = cache

    pip_count = cache_get(cache, "get_participant.pip_count")
    main_schools = ("balance", "death", "life", "myth", "storm", "fire", "ice")
    total_spips = sum((pip_count[f"{s}_pips"] for s in main_schools))


    total_spips = sum((pip_count[f"{s}_pips"] for s in main_schools))
    max_ppips = 7 - total_spips
    max_pips = max_ppips - pip_count["power_pips"]


    #TODO: finish unified clamping pips function,



class Fighter(CombatHandler):
    def __init__(self, client: Client, clients: list[Client]):
        self._spell_check_boxes = None
        self.client = client
        self.clients = clients
        self.duel_cache: Cache = {}
        self.ally_caches: List[Cache] = {}
        self.enemy_caches: List[Cache] = {}
        self.client_member_cache: Cache = {}
        self.hand_cache: List[Cache] = []


    async def update_member_caches(self, update_client_member: bool = True):
        '''Updates the local record of the sets of ally and enemy CombatMember objects.'''
        self.ally_caches.clear()
        self.enemy_caches.clear()
        members = await self.get_members()
        member_caches = [await class_snapshot(m) for m in members]

        #Get the client's cache, then the team ID
        client_matches, _ = filter_caches(member_caches, {"is_client": True})
        client_cache = client_matches[0] #TODO: This shouldn't ever fail, but the indexing is sussy nonetheless. Fix it. -slack
        ally_team_id = cache_get(client_cache, "get_participant.team_id")

        if update_client_member: #Update client if needed
            self.client_member_cache = client_cache

        self.ally_caches, _ = filter_caches(member_caches, {"get_participant.team_id": ally_team_id})
        self.enemy_caches, _ = filter_caches(member_caches, {"get_participant.team_id": ally_team_id}, True)


    async def update_duel_caches(self):
        '''Updates the local record of the client.duel object.'''
        self.duel_cache.clear()
        self.duel_cache = await class_snapshot(self.client.duel)


    async def update_hand_cache(self):
        '''Updates the local record of the list of CombatCards in our hand.'''
        self.hand_cache.clear()
        cards = await self.get_cards()
        self.hand_cache = [await class_snapshot(card) for card in cards]


    async def update_combat_caches(self):
        '''Top-level function for updating all caches. Should be done at the beginning of every round.'''
        await self.update_duel_caches()
        await self.update_member_caches()
        await self.update_hand_cache()



    async def handle_round(self):
        print("Getting snapshot data...")
        await self.update_hand_cache()
        hand_data = yaml.dump(self.hand_cache)
        pyperclip.copy(hand_data)
        # await self.update_member_caches()
        # member_data = yaml.dump(self.ally_caches)
        # pyperclip.copy(member_data)
        # await self.update_duel_caches()
        # duel_data = yaml.dump(self.duel_cache)
        # pyperclip.copy(duel_data)
        print("All done!")