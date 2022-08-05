import asyncio
import traceback
import math
import re
from loguru import logger
from difflib import SequenceMatcher
from fuzzywuzzy import fuzz

from wizwalker import XYZ, Keycode, MemoryReadError, Client
from wizwalker.file_readers.wad import Wad
from wizwalker.memory import DynamicClientObject

from src.teleport_math import *
from src.sprinty_client import SprintyClient
from src.utils import *
from src.paths import *


class Quester():
    def __init__(self, client: Client, clients: list[Client], leader_pid: int):
        self.client = client
        self.clients = clients
        self.leader_pid = leader_pid

    # TODO: Make auto questing accept an optional XYZ param so we can have team based questing

    async def read_popup_(self):
        popup_msgtext_path = ["WorldView", "NPCRangeWin", "imgBackground", "NPCRangeTxtMessage"]
        popup_text_path = await get_window_from_path(self.client.root_window, popup_msgtext_path)
        txtmsg = await popup_text_path.maybe_text()
        return txtmsg

    async def find_safe_entities_from(self, fixed_position1, fixed_position2, safe_distance: float = 700, is_mob: bool = False):
        cli = SprintyClient(self.client)
        mob_positions = []
        
        if is_mob:
            for mob in await cli.get_mobs():
                mob_positions.append(await mob.location())
            fixed_position2 = mob_positions
        if fixed_position2:
            pass
        else:
            return True

        for p in fixed_position2:
            dist = math.dist(p, fixed_position1)

        if dist < safe_distance:
            return False
        else:
            return True


    async def find_quest_entites(self, parsed_quest_info: list, entity: dict, quest_name_path, safe_cords):
        collect_counter = 0
        types_list = ['BehaviorInstance', 'ObjectStateBehavior', 'RenderBehavior', 'SelectBehavior', 'CollisionBehaviorClient']
        points = await self.Nav_Hull()
        Hull = points  # [0::2]  # TODO remove points that are close to draw distance of each other
        # teleport around the hull and collect rendered objects, add them to a dict and their location
        for points in Hull:
            points = XYZ(points.x, points.y, points.z - 550)

            while not await is_free(self.client):
                await asyncio.sleep(0.1)

            if await is_free(self.client):
                await self.client.teleport(points, move_after=False, wait_on_inuse=True)
                await self.client.teleport(points, wait_on_inuse=True)

            entities = await self.client.get_base_entity_list()
            for e in entities:
                object_template = await e.object_template()
                display_name_code = await object_template.display_name()
                display_name = await self.client.cache_handler.get_langcode_name(display_name_code)

                print(parsed_quest_info, display_name)

                # match = SequenceMatcher(None, display_name.lower(), str(parsed_quest_info[0]).lower()).ratio()
                match = fuzz.ratio(display_name.lower(), str(parsed_quest_info[0]).lower())
                # if parsed_quest_info[0].lower() == display_name.lower():
                if match > 80:
                    duplicate = False
                    xyz = await e.location()

                    if display_name in entity:
                        for i in entity[display_name]:
                            if str(i) == str(xyz):
                                duplicate = True
                        if duplicate == False:

                            can_Teleport = await self.find_safe_entities_from(xyz, None, safe_distance=2600, is_mob=True)  # checks if safe to collect
                            while not await is_free(self.client):
                                pass

                            if can_Teleport and await is_free(self.client):
                                entity[display_name].append(xyz)

                                await navmap_tp(self.client, xyz)  # teleports to the npc

                                await asyncio.sleep(.2)
                                if await is_visible_by_path(self.client, path=npc_range_path):
                                    for i in range(5):
                                        await asyncio.gather(*[p.send_key(Keycode.X, .1) for p in self.clients])

                                    print('Collecting')
                                    collect_counter = collect_counter + 1
                            await self.combat()
                            try:
                                _, count = await self.parse_quest_stuff()  # breaks when collect quest format for the string under the pointer

                                try:
                                    count_nums = count.split(" / ")
                                # for quests that ask for only one pickup (not tested - there are likely other areas that will crash these quests)
                                except:
                                    count_nums = [0, 1]

                                print(count_nums)
                                if collect_counter >= (int(count_nums[1]) - int(count_nums[0])):
                                    completed = True
                                    await self.client.teleport(safe_cords, wait_on_inuse=True)
                                    print("finished quest")
                                    return True
                            except IndexError:
                                completed = True
                                await self.client.teleport(safe_cords, wait_on_inuse=True)
                                print("finished quest")
                                return True
                    else:
                        # create a new array in this slot

                        can_Teleport = await self.find_safe_entities_from(xyz, None, safe_distance=2600, is_mob=True)  # checks if safe to collect

                        while not await is_free(self.client):
                            await asyncio.sleep(0.1)

                        if can_Teleport and await is_free(self.client):
                            entity[display_name] = [xyz]

                            await navmap_tp(self.client, xyz)  # teleports to the npc

                            # await asyncio.sleep(1)
                            await asyncio.sleep(.2)
                            if await is_visible_by_path(self.client, path=npc_range_path):
                                for i in range(5):
                                    await asyncio.gather(*[p.send_key(Keycode.X, .1) for p in self.clients])

                                print('Collecting')
                                collect_counter = collect_counter + 1
                        await self.combat()
                        try:
                            _, count = await self.parse_quest_stuff()  # breaks when collect quest format for the string under the pointer

                            try:
                                count_nums = count.split(" / ")
                            # for quests that ask for only one pickup (not tested - there are likely other areas that will crash these quests)
                            except:
                                count_nums = [0, 1]

                            print(count_nums)
                            if collect_counter >= (int(count_nums[1]) - int(count_nums[0])):
                                completed = True
                                await self.client.teleport(safe_cords, wait_on_inuse=True)
                                print("finished quest")
                                return True
                        except IndexError:
                            completed = True
                            await self.client.teleport(safe_cords, wait_on_inuse=True)
                            print("finished quest")
                            return True


        return entity


    async def Nav_Hull(self):
        wad = await self.load_wad(await self.client.zone_name())
        nav_data = await wad.get_file("zone.nav")
        vertices = []
        vertices, _ = parse_nav_data(nav_data)
        XY = []
        x_values = []
        y_values = []
        master_list = []

        for v in vertices:
            x_values.append(v.x)
            y_values.append(v.y)

        XY = list(zip(x_values, y_values))
        # https://github.com/senhorsolar/concavehull
        # glist = [(0, 0)]
        # glist = concavehull(XY, chi_factor=0.1)
        # print(XY)

        for a in XY:
            for l in vertices:
                if a[0] == l.x and a[1] == l.y:
                    master_list.append(l)

        return calc_chunks(master_list, entity_distance=1500)
        

    async def parse_quest_stuff(self):
        quest_name = await get_window_from_path(self.client.root_window, quest_name_path)
        raw = await quest_name.maybe_text() # <center>Collect Cog in Triton Avenue (0 of 3)</center>

        # Looking to get ["Cog", "Triton Avenue", "0", "3"]
        unparsed = re.findall("(?<=>).*?(?=<)|$", raw)[0] # "Collect Cog in Triton Avenue (0 of 3)""
        uniform_spacing = re.sub("\s+ ", " ", unparsed) # Check for double spaces cause KI

        # (0 of 3) is not guaranteed
        multiple_collects = uniform_spacing.find("(") != -1
        if multiple_collects:
            stripped = uniform_spacing.replace("of ", "").replace(")", "") 
        else:
            stripped = uniform_spacing

        parsed = stripped.split(" ", 1)[1].split(" in") # ["Cog", "Triton Avenue (0 3"]

        item = parsed[0] # "Cog"
        if multiple_collects:
            location, amount = parsed[1].split(" (") # ["Triton Avenue", "0 3"]
            gotten, total = amount.split(" ") # ["0", "3"]
        else:
            location = parsed[1]
            gotten = 0
            total = 0

        return item, f"{gotten} / {total}"


    async def load_wad(self, path: str):
        return Wad.from_game_data(path.replace("/", "-"))


    async def combat(self): # ????????
        # battle = Fighter(self.client, self.clients)
        # while await battle.is_fighting() == True and self.client.questing_status:
        while await self.client.in_battle():
            await asyncio.sleep(0.1)


    async def auto_collect(self, collect_client):
        temp_leader_client = self.client
        self.client = collect_client
        entity = dict()
        safe_cords = await collect_client.body.position()

        if result := await self.parse_quest_stuff():
            parsed_quest_info = result
        else:
            self.client = temp_leader_client
            return

        entity = await self.find_quest_entites(parsed_quest_info, entity, quest_name_path, safe_cords)

        await self.combat()

        self.client = temp_leader_client


    async def followers_in_correct_zone(self):
        zone = await self.client.zone_name()
        in_correct_zone = True
        for c in self.clients:
            if await c.zone_name() != zone:
                in_correct_zone = False

        return in_correct_zone


    async def auto_quest_leader(self):
        while self.client.questing_status:
            await asyncio.sleep(1)

            # get the client that belongs to leader's process id
            # this doesn't seem to work - calling functions from 'leader' instead of 'self.client' causes a crash 'coroutine' has no object __
            # leader = pid_to_client(self.clients, self.leader_pid)

            for p in self.clients:
                if await is_free(p):
                    if await is_potion_needed(p) and await p.stats.current_mana() > 1 and await p.stats.current_hitpoints() > 1:
                        await collect_wisps(p)

            if await is_free(self.client):
                # fix crash on potion use (use, not rebuy)
                await asyncio.gather(*[auto_potions(c, True, buy=True) for c in self.clients])

                quest_xyz = await self.client.quest_position.position()

                if not await self.followers_in_correct_zone():
                    # if followers in different zone, try X presses (for X zone changes that require delayed presses between clients)
                    for c in self.clients:
                        if c.process_id != self.leader_pid:
                            await c.send_key(Keycode.X, 0.1)
                            await asyncio.sleep(2.5)

                    await asyncio.sleep(2)
                    for c in self.clients:
                        while await c.is_loading():
                            await asyncio.sleep(0.1)

                    # if we still aren't in correct zone after X presses, send all to hub and retry
                    if not await self.followers_in_correct_zone():
                        for c in self.clients:
                            await c.send_key(Keycode.END)
                            await c.send_key(Keycode.END)
                            await asyncio.sleep(3)
                            # use is_loading instead of wait_for_change, as one client could already be in the hub
                            while await c.is_loading():
                                await asyncio.sleep(0.1)

                        await asyncio.sleep(2)

                distance = calc_Distance(quest_xyz, XYZ(0.0, 0.0, 0.0))
                if distance > 1:
                    if await is_free(self.client):
                        await asyncio.gather(*[navmap_tp(p, quest_xyz, leader_client=self.client) for p in self.clients])

                    await asyncio.sleep(0.7)
                    for c in self.clients:
                        if await is_visible_by_path(c, cancel_chest_roll_path):
                            # Handles chest reroll menu, will always cancel
                            await click_window_by_path(c, cancel_chest_roll_path)

                    current_pos = await self.client.body.position()
                    if await is_visible_by_path(self.client, npc_range_path) and calc_Distance(quest_xyz, current_pos) < 750.0:
                        # Handles interactables
                        sigil_msg_check = await self.read_popup_()
                        if "to enter" in sigil_msg_check.lower():
                            # Handles entering dungeons
                            await asyncio.gather(*[p.send_key(Keycode.X, 0.1) for p in self.clients])
                            for c in self.clients:
                                while not await c.is_loading():
                                    if await is_visible_by_path(c, dungeon_warning_path):
                                        await c.send_key(Keycode.ENTER, 0.1)
                                    await asyncio.sleep(0.1)

                            for c in self.clients:
                                while await c.is_loading():
                                    await asyncio.sleep(0.1)
                        else:
                            await asyncio.gather(*[p.send_key(Keycode.X, 0.1) for p in self.clients])

                            await asyncio.sleep(2)
                            was_loading = False
                            for c in self.clients:
                                while await c.is_loading():
                                    was_loading = True
                                    await asyncio.sleep(0.1)

                                # try to correct for zone lag on follower clients by giving follower clients a second to get into the zone before teleporting
                                if was_loading:
                                    await asyncio.sleep(1)


                            # Exit NPC menus (spell menus, quest menus, etc)
                            # await asyncio.sleep(2)
                            await asyncio.gather(*[exit_menus(c) for c in self.clients])

                            await asyncio.sleep(0.75)

                            if await is_visible_by_path(self.client, spiral_door_teleport_path):
                                # Handles spiral door navigation
                                await spiral_door_with_quest(self.client)

                                await asyncio.sleep(1)
                                leader_world = (await self.client.zone_name()).split('/', 1)[0]

                                # Follower clients use seperate spiral door navigation than leader (since they may not have the same quest)
                                for c in self.clients:
                                    if c.process_id != self.leader_pid:
                                        if await is_visible_by_path(c, spiral_door_teleport_path):
                                            await go_to_new_world(c, leader_world)

                    quest_objective = await get_quest_name(self.client)

                    if "Photomance" in quest_objective:
                        # Photomancy quests (WC, KM, LM)
                        await asyncio.gather(*[p.send_key(key=Keycode.Z, seconds=0.1) for p in self.clients])
                        await asyncio.gather(*[p.send_key(key=Keycode.Z, seconds=0.1) for p in self.clients])

                    for c in self.clients:
                        if await is_visible_by_path(c, missing_area_path):
                            # Handles when an area hasn't been downloaded yet
                            while not await is_visible_by_path(c, missing_area_retry_path):
                                await asyncio.sleep(0.1)
                            await click_window_by_path(c, missing_area_retry_path, True)

                else:
                    quest_objective = await get_quest_name(self.client)
                    forbidden_quests = ['Break Mining Equipment in Tyrian Gorge', 'Steal Barrel of Kermes Fire in Tyrian Gorge']

                    # if on a bad collect quest, tell the user to complete manually
                    # some zones / quests are impossible to complete or for several reasons should be avoided
                    if any(map(quest_objective.__contains__, forbidden_quests)):
                        logger.debug('Cannot complete this quest - Please complete it manually to continue.')

                        # wait until it is completed manually
                        while any(map(quest_objective.__contains__, forbidden_quests)):
                            await asyncio.sleep(2)
                            quest_objective = await get_quest_name(self.client)

                        logger.debug('Quest completed manually - continuing Auto Quest.')
                    else:
                        for c in self.clients:
                            if c.process_id != self.leader_pid:
                                try:
                                    await self.auto_collect(c)
                                except:
                                    print(traceback.print_exc())

                        for c in self.clients:
                            if c.process_id == self.leader_pid:
                                self.client = c

                        # finally, collect items on the leader
                        await self.auto_collect(self.client)


    async def auto_quest(self):
        while self.client.questing_status:
            await asyncio.sleep(1)

            if await is_free(self.client):
                if await is_potion_needed(
                        self.client) and await self.client.stats.current_mana() > 1 and await self.client.stats.current_hitpoints() > 1:
                    await collect_wisps(self.client)

            if await is_free(self.client):
                await auto_potions(self.client, True, buy=True)
                quest_xyz = await self.client.quest_position.position()

                distance = calc_Distance(quest_xyz, XYZ(0.0, 0.0, 0.0))
                if distance > 1:
                    try:
                        await navmap_tp(self.client, quest_xyz)
                    except:
                        # some level of error output may be required in navmap_tp, at the moment it is not producing output without traceback
                        print(traceback.print_exc())

                    await asyncio.sleep(0.5)
                    if await is_visible_by_path(self.client, cancel_chest_roll_path):
                        # Handles chest reroll menu, will always cancel
                        await click_window_by_path(self.client, cancel_chest_roll_path)

                    current_pos = await self.client.body.position()
                    if await is_visible_by_path(self.client, npc_range_path) and calc_Distance(quest_xyz, current_pos) < 750.0:
                        # Handles interactables
                        sigil_msg_check = await self.read_popup_()
                        if "to enter" in sigil_msg_check.lower():
                            # Handles entering dungeons
                            await asyncio.gather(*[p.send_key(Keycode.X, 0.1) for p in self.clients])
                            for c in self.clients:
                                while not await c.is_loading():
                                    if await is_visible_by_path(c, dungeon_warning_path):
                                        await c.send_key(Keycode.ENTER, 0.1)
                                    await asyncio.sleep(0.1)

                            for c in self.clients:
                                while await c.is_loading():
                                    await asyncio.sleep(0.1)
                        else:
                            await self.client.send_key(Keycode.X, 0.1)

                            await asyncio.sleep(0.75)
                            if await is_visible_by_path(self.client, spiral_door_teleport_path):
                                # Handles spiral door navigation
                                await spiral_door_with_quest(self.client)

                    quest_objective = await get_quest_name(self.client)

                    if "Photomance" in quest_objective:
                        # Photomancy quests (WC, KM, LM)
                        await self.client.send_key(key=Keycode.Z, seconds=0.1)
                        await self.client.send_key(key=Keycode.Z, seconds=0.1)

                    if await is_visible_by_path(self.client, missing_area_path):
                        # Handles when an area hasn't been downloaded yet
                        while not await is_visible_by_path(self.client, missing_area_retry_path):
                            await asyncio.sleep(0.1)
                        await click_window_by_path(self.client, missing_area_retry_path, True)

                else:
                    await self.auto_collect(self.client)


    async def check_entities(self, entities: list[DynamicClientObject], relevant_str: str, pet_mode: bool = False):
        quest_objective = await get_quest_name(self.client)
        for entity in entities:
            entity_pos = await entity.location()

            if not pet_mode:
                await self.client.teleport(entity_pos)
            else:
                await self.client.pet_teleport(entity_pos)

            await asyncio.sleep(0.25)

            if await get_quest_name(self.client) != quest_objective:
                quest_pos = await self.client.quest_position.position()

                distance = calc_Distance(quest_pos, XYZ(0.0, 0.0, 0.0))
                if distance < 1:
                    break


            elif await is_visible_by_path(self.client, npc_range_path):
                if await is_popup_title_relevant(self.client, relevant_str):
                    await asyncio.gather(*[p.send_key(Keycode.X, 0.1) for p in self.clients])
                    await asyncio.sleep(0.25)


    async def parse_quest_objective(self) -> str:
        objective_str = await get_quest_name(self.client)
        objective_list = objective_str.split(' ')
        if objective_list:
            objective_list = [s.lower() for s in objective_list.copy()]
            collect_keywords = ['collect', 'get', 'gather', 'find', 'obtain', 'use', 'open', 'locate', 'destroy']
            if len(objective_list) >= 2:
                for i, collect_str in enumerate(collect_keywords):
                    if collect_str in objective_list:
                        if len(objective_list) >= i + 2:
                            return objective_list[i + 1]

            return objective_list[0]


    async def relevant_named_entities(self, entities: list[DynamicClientObject], relevant_str: str) -> list[
        DynamicClientObject]:
        for entity in entities.copy():
            try:
                object_template = await entity.object_template()
                display_name_code = await object_template.display_name()
                try:
                    display_name: str = await self.client.cache_handler.get_langcode_name(display_name_code)
                except ValueError:
                    display_name = await object_template.object_name()

                if 'Basic' not in display_name:
                    match_ratio = SequenceMatcher(None, display_name.lower(), relevant_str.lower()).ratio()

                    if match_ratio > 0.7:
                        pass
                    else:
                        entities.remove(entity)

                else:
                    entities.remove(entity)

            except MemoryReadError:
                await asyncio.sleep(0.05)
            except AttributeError:
                await asyncio.sleep(0.05)
            except ValueError:
                pass

        return entities
