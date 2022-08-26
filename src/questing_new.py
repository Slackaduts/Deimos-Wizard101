import asyncio
import traceback
import math
from loguru import logger

# from Deimos import sync_camera
from wizwalker.extensions.scripting.utils import _maybe_get_named_window

from src.teleport_math import *
from wizwalker import XYZ, Keycode, MemoryReadError, Client, Rectangle
from wizwalker.file_readers.wad import Wad
from wizwalker.memory import DynamicClientObject
from wizwalker.extensions.scripting import teleport_to_friend_from_list
from src.sprinty_client import SprintyClient
from src.utils import *
from src.paths import *
from difflib import SequenceMatcher
from fuzzywuzzy import fuzz


# from Deimos import sync_camera


class Quester():
    def __init__(self, client: Client, clients: list[Client], leader_pid: int):
        self.client = client
        self.clients = clients
        self.leader_pid = leader_pid
        self.current_leader_client = client
        self.current_leader_pid = leader_pid

    async def read_popup_(self, p: Client):
        try:
            popup_text_path = await get_window_from_path(p.root_window, popup_msgtext_path)
            txtmsg = await popup_text_path.maybe_text()
        except:
            txtmsg = ""
        return txtmsg

    async def detected_interact_from_popup_(self, p: Client):
        try:
            popup_text_path = await get_window_from_path(p.root_window, popup_msgtext_path)
            txtmsg = await popup_text_path.maybe_text()
        except:
            txtmsg = ""

        if 'to enter' in txtmsg.lower() or 'to interact' in txtmsg.lower() or 'to activate' in txtmsg.lower():
            return True
        else:
            return False

    async def distance_to_nearest_mob(self, p: Client, safe_distance: float = 700, is_mob: bool = False, time_limit=2):
        cli = SprintyClient(self.client)
        mob_positions = []
        closest_mob = None
        pos = await p.body.position()
        try:
            if is_mob:
                for mob in await cli.get_mobs():
                    distance = calc_Distance(pos, await mob.location())
                    if closest_mob is None:
                        closest_mob = distance
                    elif distance < closest_mob:
                        closest_mob = distance
        except TypeError:
            pass

        return closest_mob

    async def find_safe_entities_from(self, fixed_position1, fixed_position2, safe_distance: float = 700,
                                      is_mob: bool = False):
        cli = SprintyClient(self.client)
        mob_positions = []
        can_Teleport = bool
        try:
            if is_mob:
                for mob in await cli.get_mobs():
                    mob_positions.append(await mob.location())
                fixed_position2 = mob_positions
            if fixed_position2:
                pass
            else:
                return True
        except ValueError:
            await asyncio.sleep(0.12)

        for p in fixed_position2:
            try:
                dist = math.dist(p, fixed_position1)
            except:
                print(traceback.format_exc())
        try:
            if dist < safe_distance:
                return False
            else:
                can_Teleport = True
        except TypeError:
            pass
        return can_Teleport

    async def find_quest_entites(self, parsed_quest_info: list, entity: dict, quest_name_path, safe_cords):
        collect_counter = 0
        types_list = ['BehaviorInstance', 'ObjectStateBehavior', 'RenderBehavior', 'SelectBehavior',
                      'CollisionBehaviorClient']
        points = await self.Nav_Hull()
        Hull = points  # [0::2]  # TODO remove points that are close to draw distance of each other
        # teleport around the hull and collect rendered objects, add them to a dict and their location
        for points in Hull:
            points = XYZ(points.x, points.y, points.z - 550)

            while not await is_free(self.client) or self.client.entity_detect_combat_status:
                await asyncio.sleep(0.1)

            if await is_free(self.client) and not self.client.entity_detect_combat_status:
                await self.client.teleport(points, move_after=False, wait_on_inuse=True)
                await self.client.teleport(points, wait_on_inuse=True)

            entities = await self.client.get_base_entity_list()
            for e in entities:
                try:
                    object_template = await e.object_template()
                    display_name_code = await object_template.display_name()
                    display_name = await self.client.cache_handler.get_langcode_name(display_name_code)



                    # await asyncio.sleep(1000000)

                    # match = SequenceMatcher(None, display_name.lower(), str(parsed_quest_info[0]).lower()).ratio()
                    match = fuzz.ratio(display_name.lower(), str(parsed_quest_info[0]).lower())
                    # if parsed_quest_info[0].lower() == display_name.lower():
                    if match > 80:
                        duplicate = False
                        try:
                            xyz = await e.location()
                        except:
                            print(traceback.format_exc())

                        if display_name in entity:
                            for i in entity[display_name]:
                                if str(i) == str(xyz):
                                    duplicate = True
                            if duplicate == False:

                                can_Teleport = await self.find_safe_entities_from(xyz, None, safe_distance=2600,
                                                                                  is_mob=True)  # checks if safe to collect
                                while not await is_free(self.client) or self.client.entity_detect_combat_status:
                                    pass

                                if can_Teleport and await is_free(
                                        self.client) and not self.client.entity_detect_combat_status:
                                    entity[display_name].append(xyz)

                                    try:
                                        try:
                                            await navmap_tp(self.client, xyz)  # teleports to the npc
                                        except:
                                            print(traceback.format_exc())

                                        # await asyncio.sleep(1)
                                        await asyncio.sleep(.2)
                                        if await is_visible_by_path(self.client, path=npc_range_path):
                                            for i in range(5):
                                                await asyncio.gather(*[p.send_key(Keycode.X, .1) for p in self.clients])

                                            print('Collecting')
                                            collect_counter = collect_counter + 1
                                    # await asyncio.sleep(2)
                                    except:
                                        await asyncio.sleep(0.01)
                                await self.combat()
                                try:
                                    _, count = await self.parse_quest_stuff(
                                        quest_name_path)  # breaks when collect quest format for the string under the pointer

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

                            can_Teleport = await self.find_safe_entities_from(xyz, None, safe_distance=2600,
                                                                              is_mob=True)  # checks if safe to collect

                            while not await is_free(self.client) or self.client.entity_detect_combat_status:
                                await asyncio.sleep(0.1)

                            if can_Teleport and await is_free(
                                    self.client) and not self.client.entity_detect_combat_status:
                                entity[display_name] = [xyz]

                                try:
                                    try:
                                        await navmap_tp(self.client, xyz)  # teleports to the npc
                                    except:
                                        print(traceback.format_exc())

                                    # await asyncio.sleep(1)
                                    await asyncio.sleep(.2)
                                    if await is_visible_by_path(self.client, path=npc_range_path):
                                        for i in range(5):
                                            await asyncio.gather(*[p.send_key(Keycode.X, .1) for p in self.clients])

                                        print('Collecting')
                                        collect_counter = collect_counter + 1
                                except:
                                    await asyncio.sleep(0.01)
                            await self.combat()
                            try:
                                _, count = await self.parse_quest_stuff(
                                    quest_name_path)  # breaks when collect quest format for the string under the pointer

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

                        # break
                except MemoryReadError:
                    await asyncio.sleep(0.05)
                except AttributeError:
                    await asyncio.sleep(0.05)
                except ValueError:
                    pass

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
        arr = []
        # print(vertices)
        for v in vertices:
            x_values.append(v.x)
            y_values.append(v.y)

        XY = list(zip(x_values, y_values))
        # https://github.com/senhorsolar/concavehull
        # glist = [(0, 0)]
        # glist = concavehull(XY, chi_factor=0.1)
        # print(XY)

        # print(master_list)
        for a in XY:
            for l in vertices:
                if a[0] == l.x:
                    if a[1] == l.y:
                        master_list.append(l)
        # print(master_list)
        # print(master_list)
        current_pos = await self.client.body.position()
        full = calc_chunks(master_list, entity_distance=1500)
        return full

    async def parse_quest_stuff(self, quest_name_path):
        quest_name = await get_window_from_path(self.client.root_window, quest_name_path)
        unsplitted = await quest_name.maybe_text()
        try:
            quest_helper = unsplitted.split("\n</center>")
            unsplitted = quest_helper[1]
            return False
        except IndexError:
            pass
        split1_qst = unsplitted.split("<center>Collect ")
        if not len(split1_qst) > 1:
            split1_qst = unsplitted.split("<center>Open ")
            if not len(split1_qst) > 1:
                split1_qst = unsplitted.split("<center>Use ")
                if not len(split1_qst) > 1:
                    split1_qst = unsplitted.split("<center>Find ")
                    if not len(split1_qst) > 1:
                        split1_qst = unsplitted.split("<center>Gather ")
                        if not len(split1_qst) > 1:
                            split1_qst = unsplitted.split("<center>Destroy ")

        print(split1_qst)
        try:
            split2_qst = split1_qst[1].split(" in")  # Parsing the quest name
        except IndexError:
            split2_qst = split1_qst[0].split("  in")
        questnameparsed = split2_qst[0]

        # example of a collect quest the only stuff that change are
        # "Cog", "Triton Avenue" and "(0 of 3)" the rest is static
        # <center>Collect Cog in Triton Avenue (0 of 3)</center>

        split1_amt = unsplitted.split(" (")
        split2_amt = split1_amt[1].replace(")</center>", "")
        amount_to_get_parsed = split2_amt.split("of ")[1]  # Parsing the amount of stuff to pick up
        amount_gotten_parsed = split2_amt.split(" of")[0]  # Parsing the amount of stuff that has been picked up

        # some collect quests do not have numbers (ex: 0 / 6) - for these only one item must be picked up
        # while this does fix collects for these quests, it can cause non - collects to be read as collects
        # except:
        #     #print(traceback.print_exc())
        #     amount_to_get_parsed = 1
        #     amount_gotten_parsed = 0

        return questnameparsed, f"{amount_gotten_parsed} / {amount_to_get_parsed}"

    async def load_wad(self, path: str):
        return Wad.from_game_data(path.replace("/", "-"))

    async def combat(self):
        # battle = Fighter(self.client, self.clients)
        # while await battle.is_fighting() == True and self.client.questing_status:
        while await self.client.in_battle():
            await asyncio.sleep(0.1)

    async def auto_collect_new(self, collect_client):
        cli = SprintyClient(collect_client)
        quest_name_path = ["WorldView", "windowHUD", "QuestHelperHud", "ElementWindow", "", "txtGoalName"]
        popup_msgtext_path = ["WorldView", "NPCRangeWin", "imgBackground", "NPCRangeTxtMessage"]
        # popup_title_path =["WorldView", "NPCRangeWin"]
        entity = dict()
        entity2 = dict()
        collect_counter = 0
        safe_cords = await collect_client.body.position()
        completed = False

        if result := await self.parse_quest_stuff(quest_name_path):
            parsed_quest_info = result
        else:
            return

        try:
            await self.find_quest_entites(parsed_quest_info, entity, quest_name_path, safe_cords)
        except:
            print(traceback.format_exc())

        try:
            # this may not work
            await self.combat()
        except:
            print(traceback.format_exc())

    async def auto_collect(self, collect_client):
        temp_leader_client = self.client
        self.client = collect_client
        cli = SprintyClient(collect_client)
        quest_name_path = ["WorldView", "windowHUD", "QuestHelperHud", "ElementWindow", "", "txtGoalName"]
        popup_msgtext_path = ["WorldView", "NPCRangeWin", "imgBackground", "NPCRangeTxtMessage"]
        # popup_title_path =["WorldView", "NPCRangeWin"]
        entity = dict()
        entity2 = dict()
        collect_counter = 0
        safe_cords = await collect_client.body.position()
        completed = False

        if result := await self.parse_quest_stuff(quest_name_path):
            parsed_quest_info = result
        else:
            self.client = temp_leader_client
            return

        try:
            entity = await self.find_quest_entites(parsed_quest_info, entity, quest_name_path, safe_cords)
        except:
            print(traceback.format_exc())

        try:
            # this may not work
            await self.combat()
        except:
            print(traceback.format_exc())

        self.client = temp_leader_client

    async def handle_collect_quest(self):
        navmap_points = await get_navmap_data(self.client)
        current_pos = await self.client.body.position()
        adjusted_pos = XYZ(current_pos.x, current_pos.y, current_pos.z - 350)
        chunks = calc_chunks(navmap_points, adjusted_pos)
        quest_objective = await get_quest_name(self.client)

        sprinter = SprintyClient(self.client)
        for chunk in chunks:
            if await is_free(self.client) and self.client.questing_status:
                # await navmap_tp(self.client, chunk)
                await self.client.teleport(chunk, wait_on_inuse=True)

            await asyncio.sleep(1)

            entities = await sprinter.get_base_entity_list()
            safe_entities = await sprinter.find_safe_entities_from(entities, safe_distance=2600)
            relevant_str = await self.parse_quest_objective()
            relevant_entities = await self.relevant_named_entities(safe_entities, relevant_str)

            if relevant_entities:
                await self.check_entities(relevant_entities, relevant_str)

            if await get_quest_name(self.client) != quest_objective:
                quest_xyz = await self.client.quest_position.position()

                distance = calc_Distance(quest_xyz, XYZ(0.0, 0.0, 0.0))
                if distance < 1:
                    break

            else:
                await self.check_entities(safe_entities, relevant_str)

    async def followers_in_correct_zone(self):
        zone = await self.current_leader_client.zone_name()
        is_correct_zone = True
        for c in self.clients:
            if await c.zone_name() != zone:
                is_correct_zone = False

        return is_correct_zone

    async def determine_solo_zone(self):
        sprinter = SprintyClient(self.current_leader_client)
        entities = await sprinter.get_base_entity_list()

        player_count = 0
        for entity in entities:
            entity_name = await entity.object_name()
            if entity_name == 'Player Object':
                player_count += 1

                if player_count == 2:
                    break

        if player_count == 1:
            return True
        else:
            return False

    async def get_truncated_quest_objectives(self, p: Client):
        quest_objective = await get_quest_name(p)
        if '(' in quest_objective:
            quest_objective = quest_objective.split('(', 1)
            quest_objective = quest_objective[0]

        return quest_objective

    # get a list of clients that are questing alongside the leader (not boosting)
    async def get_questing_clients(self):
        questing_clients = [self.current_leader_client]
        quest_objective_leader = await self.get_truncated_quest_objectives(self.current_leader_client)

        for c in self.clients:
            quest_objective_follower = await self.get_truncated_quest_objectives(c)

            if quest_objective_follower == quest_objective_leader and c.process_id != self.current_leader_client.process_id:
                questing_clients.append(c)

        return questing_clients

    # get a dict of client quests for clients that are on the same quest as the leader
    async def get_client_quests(self, questing_clients: list[Client]):
        quest_objective_leader = await self.get_truncated_quest_objectives(self.current_leader_client)

        client_quests = dict()
        client_quests.update({self.current_leader_client: quest_objective_leader})

        for c in questing_clients:
            quest_objective_follower = await self.get_truncated_quest_objectives(c)

            if quest_objective_follower == quest_objective_leader and c.process_id != self.current_leader_client.process_id:
                client_quests.update({c: quest_objective_follower})

        return client_quests

    async def get_follower_clients(self):
        follower_clients = []
        for c in self.clients:
            if c.process_id != self.current_leader_client.process_id:
                follower_clients.append(c)

        return follower_clients

    async def zone_recorrect_hub(self):
        if not await self.followers_in_correct_zone():
            for p in self.clients:
                await p.send_key(Keycode.END)
                await p.send_key(Keycode.END)
                await asyncio.sleep(3)
                # use is_loading instead of wait_for_change, as one client could already be in the hub
                while await p.is_loading():
                    await asyncio.sleep(0.1)

            await asyncio.sleep(2)

    # handle zone recorrection in follow leader mode using friend TP.  Also quest all questing clients individually when they are in a solo zone
    async def zone_recorrect_friend_tp(self, maybe_solo_zone: bool):
        # for solo zone questing support across multiple clients
        async def solo_zone_questing_loop(clients_in_solo: List[Client], zone: str):
            async def solo_zone_questing(solo_cl: Client):
                # solo_zone_clients = []
                # for sc in clients_in_solo:
                #     solo_zone_clients.append(sc)

                questing = Quester(solo_cl, self.clients, None)
                while solo_cl.questing_status and await solo_cl.zone_name() == zone:
                    await asyncio.sleep(1.0)

                    if solo_cl in self.clients and solo_cl.questing_status:
                        await questing.auto_quest_solo()

                # solo_zone_clients.remove(solo_cl)

            await asyncio.gather(*[solo_zone_questing(cl) for cl in clients_in_solo])

        if len(self.clients) > 1:
            clients_in_solo_zone = []
            # if clients are not in same zone as leader, teleport there, or quest leader individually
            while not await self.followers_in_correct_zone() or maybe_solo_zone:
                leader_in_solo_zone = False
                was_loading = False
                for c in self.clients:
                    if c.process_id != self.current_leader_pid:
                        c_zone = await c.zone_name()
                        leader_zone = await self.current_leader_client.zone_name()
                        if c_zone != leader_zone or maybe_solo_zone:
                            if await is_free(c) and not c.entity_detect_combat_status:
                                # teleport to leader
                                await c.send_key(Keycode.F, 0.1)

                                await attempt_activate_mouseless(c)

                                await asyncio.sleep(.4)

                                await teleport_to_friend_from_list(c, name=self.current_leader_client.wizard_name)  # icon_list=1, icon_index=self.current_leader_client.questing_friend_teleport_icon)

                                if c_zone != leader_zone:
                                    while not await c.is_loading():
                                        await asyncio.sleep(.1)
                                        # friend TP may fail due to leader being in a solo zone
                                        if await is_visible_by_path(c, friend_is_busy_path):
                                            await click_window_by_path(c, friend_is_busy_path)

                                            solo_zone = await self.current_leader_client.zone_name()

                                            # if leader is in solo zone, others may be too - meaning the user is likely trying to quest multiple clients at the same time.  Keep track of these questing clients
                                            for p in self.clients:
                                                if await p.zone_name() == await self.current_leader_client.zone_name():
                                                    clients_in_solo_zone.append(p)

                                            await attempt_deactivate_mouseless(c)
                                            leader_in_solo_zone = True
                                            break

                                    if not leader_in_solo_zone:
                                        while await c.is_loading():
                                            was_loading = True
                                            await asyncio.sleep(0.1)

                                            # friend TP may fail due to leader being in a solo zone
                                            if await is_visible_by_path(c, friend_is_busy_path):
                                                await click_window_by_path(c, friend_is_busy_path)

                                                solo_zone = await self.current_leader_client.zone_name()

                                                # if leader is in solo zone, others may be too - meaning the user is likely trying to quest multiple clients at the same time.  Keep track of these questing clients
                                                for p in self.clients:
                                                    if await p.zone_name() == await self.current_leader_client.zone_name():
                                                        clients_in_solo_zone.append(p)

                                                await attempt_deactivate_mouseless(c)
                                                leader_in_solo_zone = True
                                                break

                                        # we successfully teleported, which means we are clearly not in a solo zone anymore
                                        if not leader_in_solo_zone:
                                            maybe_solo_zone = False

                                        await attempt_deactivate_mouseless(c)
                                    else:
                                        break
                                else:
                                    await asyncio.sleep(2.0)

                                    # friend TP may fail due to leader being in a solo zone
                                    if await is_visible_by_path(c, friend_is_busy_path):
                                        await click_window_by_path(c, friend_is_busy_path)

                                        solo_zone = await self.current_leader_client.zone_name()

                                        # if leader is in solo zone, others may be too - meaning the user is likely trying to quest multiple clients at the same time.  Keep track of these questing clients
                                        for p in self.clients:
                                            if await p.zone_name() == await self.current_leader_client.zone_name():
                                                clients_in_solo_zone.append(p)

                                        await attempt_deactivate_mouseless(c)
                                        leader_in_solo_zone = True
                                        break
                                    else:
                                        maybe_solo_zone = False

                        # else:
                        #     await c.teleport(await self.current_leader_client.body.position())

                        # if a client is in the same zone as the leader, it cannot be a solo zone
                        #     maybe_solo_zone = False
                        #     await asyncio.sleep(1.0)
                # leaving a loading screen is not equivalent to being ready to move - give clients time to truly load into a zone
                if was_loading:
                    await asyncio.sleep(3.0)

                # if client(s) in solo zone, switch to non-leader auto questing and quest each valid client on their own until their zone changes
                if len(clients_in_solo_zone) > 0:
                    for solo_client in clients_in_solo_zone:
                        logger.debug('Client ' + solo_client.title + ' is in solo zone - questing alone')
                        solo_client.in_solo_zone = True

                    solo_zone_task = asyncio.create_task(
                        solo_zone_questing_loop(clients_in_solo=clients_in_solo_zone, zone=solo_zone))
                    await asyncio.wait([solo_zone_task])

                    for solo_client in clients_in_solo_zone:
                        logger.debug('Client ' + solo_client.title + ' may have left solo zone')
                        solo_client.in_solo_zone = False

                        maybe_solo_zone = await self.determine_solo_zone()
                        if maybe_solo_zone:
                            logger.debug('Some clients appear to still be in the solo zone.')
                        else:
                            logger.debug('Clients all appear to have left the solo zone.')

                    clients_in_solo_zone = []

    async def heal_and_handle_potions(self):
        for p in self.clients:
            if await is_free(p):
                if await is_potion_needed(
                        p) and await p.stats.current_mana() > 1 and await p.stats.current_hitpoints() > 1:
                    await collect_wisps(p)

            if await is_free(p):
                if await is_potion_needed(p, minimum_mana=16):
                    await use_potion(p)

        for p in self.clients:
            # If we have less than 1 potion left, send all clients to get potions (even if some don't need it).  Only do this once per questing loop
            if await p.stats.potion_charge() < 1.0 and await p.stats.reference_level() >= 5:
                await asyncio.gather(*[refill_potions(p, mark=True) for p in self.clients])
                break

    # if followers in different zone, try X presses (for X zone changes that require delayed presses between clients)
    async def X_press_zone_recorrect(self):
        for c in self.clients:
            if c.process_id != self.current_leader_pid:
                await c.send_key(Keycode.X, 0.1)
                await asyncio.sleep(2.5)

        await asyncio.sleep(2)
        for c in self.clients:
            while await c.is_loading():
                await asyncio.sleep(0.1)

    async def enter_dungeon(self):
        # Handles entering dungeons
        await asyncio.gather(*[p.send_key(Keycode.X, 0.1) for p in self.clients])

        await asyncio.sleep(1.5)

        for c in self.clients:
            if await is_visible_by_path(c, dungeon_warning_path):
                await c.send_key(Keycode.ENTER, 0.1)

        await asyncio.gather(*[c.wait_for_zone_change() for c in self.clients])

        # for c in self.clients:
        #     while not await c.is_loading():
        #         print('1')
        #         if await is_visible_by_path(c, dungeon_warning_path):
        #             await c.send_key(Keycode.ENTER, 0.1)
        #         await asyncio.sleep(0.1)
        #
        # for c in self.clients:
        #     while await c.is_loading():
        #         print('2')
        #         await asyncio.sleep(0.1)

    async def handle_spiral_navigation(self):
        # Handles spiral door navigation
        await spiral_door_with_quest(self.current_leader_client)

        await asyncio.sleep(1)
        leader_world = (await self.current_leader_client.zone_name()).split('/', 1)[0]

        # Follower clients use separate spiral door navigation than leader (since they may not have the same quest)
        for c in self.clients:
            if c.process_id != self.current_leader_pid:
                if await is_visible_by_path(c, spiral_door_teleport_path):
                    await go_to_new_world(c, leader_world)

    async def auto_tfc_friend_all_wizards(self):
        for code_generator in self.clients:
            for code_redeemer in self.clients:
                if code_generator.process_id != code_redeemer.process_id:
                    friend_already_in_list = await check_for_friend_in_list(code_generator, code_redeemer.wizard_name)

                    if not friend_already_in_list:
                        tfc = await generate_tfc(code_generator)
                        await accept_tfc(code_redeemer, tfc)

    # This is horribly inconsistent due to wizwalker reading incorrect values
    # @logger.catch()
    async def auto_friend_all_wizards(self):
        # await self.current_leader_client.send_key(Keycode.END, 0.1)
        # await asyncio.sleep(4)
        # while await self.current_leader_client.is_loading():
        #    await asyncio.sleep(.1)

        # move leader forward so they are not overlapped with other arriving clients
        await self.current_leader_client.send_key(Keycode.W, .5)

        await asyncio.sleep(2)
        await asyncio.gather(*[navigate_to_ravenwood(p) for p in self.clients])
        # await toZone(self.clients, 'WizardCity/WC_Ravenwood')  # await self.current_leader_client.zone_name())

        # send all to a common realm (Centaur)
        for c in self.clients:
            while not await is_visible_by_path(c, check_spellbook_open_path):
                await c.send_key(Keycode.ESC, 0.1)

            await attempt_activate_mouseless(c)

            for i in range(3):
                await c.mouse_handler.click_window_with_name('RealmsButton')
                await asyncio.sleep(.1)

            for i in range(3):
                await c.mouse_handler.click_window_with_name('btnRealm' + str(6))
                await asyncio.sleep(.1)

            for i in range(3):
                if not await c.is_loading():
                    try:
                        await c.mouse_handler.click_window_with_name('btnGoToRealm')
                    except ValueError:
                        await asyncio.sleep(.1)
                    await asyncio.sleep(.5)

            await asyncio.sleep(2.0)
            while await c.is_loading():
                await asyncio.sleep(.1)

            if await is_visible_by_path(c, close_spellbook_path):
                await click_window_by_path(c, close_spellbook_path)

            await attempt_deactivate_mouseless(c)

        for requester in self.clients:
            requester_original_position = await requester.body.position()
            # teleport to a wacky spot in Ravenwood so that we dont accidentally click the wrong player
            # yaw moves our camera really close (because we're colliding with a wall), reducing the chance of mis-clicking
            await requester.teleport(XYZ(x=-1884.0, y=-2328.0, z=0.0), yaw=0.7693982720375061)
            await asyncio.sleep(.3)
            await requester.send_key(Keycode.W, 0.1)

            for acceptor in self.clients:
                if requester.process_id != acceptor.process_id:
                    friend_already_in_list = await check_for_friend_in_list(requester, acceptor.wizard_name)

                    if not friend_already_in_list:
                        original_acceptor_location = await acceptor.body.position()
                        # teleport the clients that are friending each other to the same location
                        await acceptor.teleport(await requester.body.position(), yaw=await requester.body.yaw())
                        await asyncio.sleep(10)

                        # Click a few times initially and pray it works, as wiz sometimes lies about the add friend window being visible when it isn't

                        await attempt_activate_mouseless(requester)
                        rect: Rectangle = requester.window_rectangle
                        width = (rect.x2 - rect.x1)
                        height = (rect.y2 - rect.y1)
                        # Width and Height are always off by a set number - unsure if this interferes with clicking
                        # width = abs(width + 16)
                        # height = height - 39
                        width = abs(width)
                        center_x = width / 2
                        center_y = height / 2

                        for i in range(5):
                            await requester.mouse_handler.click(x=int(center_x), y=int(center_y), sleep_duration=0.3)
                            await asyncio.sleep(.2)

                        # friend_title = await get_friend_popup_wizard_name(requester)

                        # continually click until the correct friend popup window appears
                        # this code may never run, as reading the friend popup window is inaccurate
                        # while friend_title != acceptor.wizard_name:
                        #     await requester.send_key(Keycode.D, 0.3)
                        #     await requester.mouse_handler.click(x=int(center_x), y=int(center_y), sleep_duration=0.3)
                        #     friend_title = await get_friend_popup_wizard_name(requester)

                        # Click add friend
                        for i in range(2):
                            if await is_visible_by_path(requester, add_remove_friend_path):
                                await click_window_by_path(requester, add_remove_friend_path)

                        # Confirm sending the request
                        for i in range(2):
                            if await is_visible_by_path(requester, confirm_send_friend_request):
                                await asyncio.sleep(.2)
                                await click_window_by_path(requester, confirm_send_friend_request)

                        # Wait for accept friend popup to appear
                        for i in range(2):
                            while not await is_visible_by_path(acceptor, confirm_accept_friend_request):
                                await asyncio.sleep(.1)

                        await attempt_activate_mouseless(acceptor)

                        # Accept friend request
                        for i in range(2):
                            if await is_visible_by_path(acceptor, confirm_accept_friend_request):
                                await asyncio.sleep(.4)
                                await click_window_by_path(acceptor, confirm_accept_friend_request)

                        await attempt_deactivate_mouseless(acceptor)

                        # Close friend window on requestor
                        # This fails consistently, even when the friends list is actually open.  Detecting whether the friends list is open is also horrifically inconsistent so just brute force it
                        for i in range(5):
                            try:
                                await click_window_by_path(requester, close_real_friend_list_button_path)
                                await asyncio.sleep(.1)
                            except ValueError:
                                await asyncio.sleep(.1)

                        await attempt_deactivate_mouseless(requester)

                        await acceptor.teleport(original_acceptor_location)
                        await acceptor.send_key(Keycode.W, 0.1)
                        await asyncio.sleep(1)

            await requester.teleport(requester_original_position)


    async def num_clients_in_same_area(self):
        sprinter = SprintyClient(self.current_leader_client)
        entities = await sprinter.get_base_entity_list()

        player_count = 0
        list_of_present_clients = []
        for entity in entities:
            entity_name = await entity.object_name()
            if entity_name == 'Player Object':
                for c in self.clients:
                    if c.process_id not in list_of_present_clients:
                        distance = calc_Distance(await c.body.position(), await entity.location())
                        # this is almost certainly one of our clients
                        if distance < 20:
                            player_count += 1
                            list_of_present_clients.append(c.process_id)
                            break

                if player_count == len(self.clients):
                    break

        return player_count

    async def determine_new_leader_and_followers(self, client_quests: dict, questing_clients: list[Client],
                                                 follower_clients: list[Client]):
        original_length = len(client_quests)
        if len(client_quests) > 0:
            for c in questing_clients:
                if c in client_quests:
                    if await self.get_truncated_quest_objectives(c) != client_quests.get(c):
                        client_quests.pop(c)

            # if all clients have moved on from their previous quest
            if len(client_quests) == 0:
                # pass leader back to original leader client
                if self.current_leader_client.title != self.client.title:
                    logger.debug('Clients caught up - resetting leader to client ' + self.client.title)
                    self.current_leader_client = self.client
                    self.current_leader_pid = self.client.process_id
                    follower_clients = await self.get_follower_clients()

                client_quests = await self.get_client_quests(questing_clients)

            elif len(client_quests) < original_length:

                # pass leader to next client in dict
                logger.debug('client(s) fell behind - new leader ' + list(client_quests)[0].title + ' assigned')
                self.current_leader_client = list(client_quests)[0]
                self.current_leader_pid = self.current_leader_client.process_id
                follower_clients = await self.get_follower_clients()
        else:
            client_quests = await self.get_client_quests(questing_clients)

        return follower_clients, client_quests


    async def correct_dungeon_desync(self, follower_clients):
        for c in self.clients:
            await c.mouse_handler.activate_mouseless()

        # await asyncio.gather(*[await c.mouse_handler.activate_mouseless() for c in self.clients])

        # attempt to correct the desync by simply teleporting all clients to the leader
        await asyncio.gather(*[teleport_to_friend_from_list(c, name=self.current_leader_client.wizard_name) for c in follower_clients])

        await asyncio.sleep(1.5)

        # this may fail - some zones cannot be teleported to even if they have public sigils - detect whether this zone is locked off to teleports
        teleport_banned_zone = False
        for c in self.clients:
            if await is_visible_by_path(c, friend_is_busy_path):
                await click_window_by_path(c, friend_is_busy_path)
                teleport_banned_zone = True

        await asyncio.sleep(.5)

        # if we cannot teleport, send all to hub, then teleport
        # teleporting can never fail in the hub (due to a locked zone at least), so this is a surefire way get all clients in the same realm / area
        if teleport_banned_zone:
            logger.debug('Friend teleport correction for dungeon desync failed - sending all clients to hub and retrying teleport')
            await self.zone_recorrect_hub()
            await asyncio.gather(*[teleport_to_friend_from_list(c, name=self.current_leader_client.wizard_name) for c in follower_clients])

            await asyncio.sleep(5.0)
            for c in self.clients:
                while await c.is_loading():
                    await asyncio.sleep(.1)
        else:
            await asyncio.sleep(3.0)
            for c in self.clients:
                while await c.is_loading():
                    await asyncio.sleep(.1)

        for c in self.clients:
            await c.mouse_handler.deactivate_mouseless()

    async def auto_collect_rewrite(self, client: Client):
        quest_name_path = ["WorldView", "windowHUD", "QuestHelperHud", "ElementWindow", "",
                           "txtGoalName"]  # path to the yellow text under arrow which tells you your quest
        quest_item_list = await self.parse_quest_stuff(
            quest_name_path)  # gets quest name from path and parses it for collect quest item name
        print(quest_item_list[0])

        chunk_cords = await self.Nav_Hull()  # list of cords that load in chunk
        for points in chunk_cords:  # loops through the points
            points = XYZ(points.x, points.y, points.z - 550)  # sets cord to underground to avoid pull / detection
            await client.teleport(points, move_after=False, wait_on_inuse=True)  # teleports under the area
            await client.teleport(points, wait_on_inuse=True)  # updates cords in wizard101 server

            entities = await self.client.get_base_entity_list()  # gets the entity list of the map
            for e in entities:
                try:
                    object_template = await e.object_template()  # gets entity template
                    display_name_code = await object_template.display_name()  # gets display name code
                    display_name = await self.client.cache_handler.get_langcode_name(display_name_code)  # uses display name code to get display name text
                    match = fuzz.ratio(display_name.lower(), str(quest_item_list[0]).lower())  # fuzzywuzzy check if display name matches quest item.
                    if match > 80:  # if strings match greater than 80 it means that it's most likely the item
                        while not await is_free(self.client) or self.client.entity_detect_combat_status:
                            await asyncio.sleep(.1)

                        print('display name: ' + display_name)
                        if await self.collect_entity(e):  # grabs enity
                            return
                except ValueError:
                    pass
                except MemoryReadError:
                    pass
                except AttributeError:
                    pass

            # this is backup if displayname doesn't work
            for e in entities:
                try:
                    temp = await e.object_template()
                    e_name = str(await temp.object_name())  # entity name
                    entities_to_skip = ['Basic Positional', 'WispHealth', 'WispMana', 'KT_WispHealth', 'KT_WispMana', 'WispGold', 'DuelCircle', 'Player Object', 'SkeletonKeySigilArt', 'Basic Ambient']
                    if e_name not in entities_to_skip:  # helps speed things up
                        name_list = e_name.split('_')
                        edited_name = ''.join(name_list[1:])
                        # do stripping symbols stuff with edited_name
                        edit_name2 = ''.join([i for i in edited_name if not i.isdigit()])
                        edit_name3 = str(edit_name2).replace("_", "")
                        match = fuzz.ratio(edit_name3.lower(), str(quest_item_list[0]).lower())
                        if int(match) > 50:
                            while not await is_free(self.client) or self.client.entity_detect_combat_status:
                                await asyncio.sleep(.1)

                            print('file name: ' + edit_name3)
                            if await self.collect_entity(e):  # grabs enity
                                return
                except:
                    pass

            #await asyncio.sleep(1)

    async def collect_entity(self, e: DynamicClientObject):
        xyz = await e.location()  # gets entities xyz
        for _ in range(2):  # try's to collect item twice if not safe
            can_Teleport = await self.find_safe_entities_from(xyz, None, safe_distance=2600, is_mob=True)  # checks if safe to collect
            if can_Teleport:
                safe_location = await self.client.body.position()
                try:
                    # await self.client.teleport(xyz)
                    await navmap_tp(self.client, xyz)  # teleports to the xyz
                except:
                    print(traceback.format_exc())

                await asyncio.sleep(.2)  # waits 2 secs for the UI to load

                if await is_visible_by_path(self.client, path=npc_range_path):  # checks if there is an UI
                    for i in range(5):
                        await asyncio.gather(*[p.send_key(Keycode.X, .1) for p in self.clients])  # trys to collect by spamming x
                    print('Collecting')

                    while not await is_free(self.client) or self.client.entity_detect_combat_status:
                        await asyncio.sleep(.1)

                    # return client to their previous safe location before grabbing the entity
                    await self.client.teleport(safe_location)
                    # collected = True
                    return True
        return False

    # @logger.catch()
    async def auto_quest_leader(self, questing_friend_tp: bool):
        follower_clients = await self.get_follower_clients()

        # read and store the name of the client's wizard
        if questing_friend_tp:
            await asyncio.gather(*[set_wizard_name(c) for c in self.clients])

            # clients_already_added = True
            friend_lists = dict()
            for requester in self.clients:
                friend_names = []
                for acceptor in self.clients:
                    if requester.process_id != acceptor.process_id:
                        friend_names.append(acceptor.wizard_name)

                friend_lists.update({requester: friend_names})

            # Working but inconsistent code for checking if all clients are friends, and then automatically adding them
            # ---------------------------------------------------------------------------------------------------------
            # check if all clients have all other clients friended
            # check_all_friends = [asyncio.create_task(check_for_multiple_friends_in_list(checker, friend_lists[checker])) for checker in friend_lists]
            # done, pending = await asyncio.wait(check_all_friends)
            #
            # clients_already_added = True
            # for d in done:
            #     if not d.result():
            #         clients_already_added = False
            #
            # # if any clients don't have each other added, friend TP zone correction will fail.  To solve this, we add automatically send and accept friend requests between all clients
            # if not clients_already_added:
            #     logger.info('Auto Quest requires that all clients have added each other as friends.  Attempting to friend all clients')
            #
            #     # can_tfc = True
            #     # for c in self.clients:
            #     #     permissions = await c.game_client.account_permissions()
            #     #     if not permissions.can_true_friend_code:
            #     #         can_tfc = False
            #     #
            #     # if can_tfc:
            #     #     await self.auto_tfc_friend_all_wizards()
            #     # else:
            #     #     await self.auto_friend_all_wizards()
            #     await self.auto_friend_all_wizards()

        # determining questing clients from booster clients requires them to be within render distance of each other
        # to make questing as efficient as possible, recorrect zones right off the bat when questing first starts
        leader_pos = await self.current_leader_client.body.position()
        for c in self.clients:
            if await c.zone_name() == await self.current_leader_client.zone_name():
                errored = True
                # teleport throws should update bool
                while errored:
                    try:
                        await c.teleport(leader_pos)
                        errored = False
                    except ValueError:
                        errored = True
                        await asyncio.sleep(1.0)

        if len(self.clients) > 1:
            maybe_solo_zone = await self.determine_solo_zone()
        else:
            maybe_solo_zone = False

        # only friend TPs if clients are in different zones or we think we may be in a solo zone
        if questing_friend_tp:
            await self.zone_recorrect_friend_tp(maybe_solo_zone=maybe_solo_zone)
            maybe_solo_zone = await self.determine_solo_zone()

        # leader and follower clients can dynamically change during auto questing to account for clients being left behind
        questing_clients = await self.get_questing_clients()
        client_quests = await self.get_client_quests(questing_clients)

        if len(client_quests) > 0:
            s = ''
            for cl in client_quests:
                if s == '':
                    s = cl.title
                else:
                    s = s + ', ' + cl.title

            logger.debug('Clients on same quest: ' + s)

        leaders_previous_zone = await self.client.zone_name()

        # main loop
        while self.client.questing_status:
            await asyncio.sleep(.4)

            # Collect wisps, use potions, or get potions if necessary
            await self.heal_and_handle_potions()

            # If zone changed, try to determine if we are in a solo zone
            leaders_zone = await self.current_leader_client.zone_name()

            if leaders_zone != leaders_previous_zone:
                leaders_previous_zone = leaders_zone

                if len(self.clients) > 1:
                    maybe_solo_zone = await self.determine_solo_zone()

            # dynamically change leader client when follower's get left behind
            # if there were previously clients on the same quest check for quest objective change on all clients
            follower_clients, client_quests = await self.determine_new_leader_and_followers(client_quests, questing_clients, follower_clients)

            quest_xyz = await self.current_leader_client.quest_position.position()

            # if followers in wrong zone, first attempt to click X - this may send them into the next zone if they are near an interactible door
            # don't do this when friend tp is active (as x press correction for some reason appears to be inconsistent)
            if (not await self.followers_in_correct_zone() or maybe_solo_zone) and not questing_friend_tp:
                logger.debug('Clients may be in wrong zone - attempting to correct with X press')
                await self.X_press_zone_recorrect()

            if not await self.followers_in_correct_zone() or maybe_solo_zone:
                if not questing_friend_tp:
                    # if still in the wrong zone, try sprinter navigation
                    if not await self.followers_in_correct_zone() or maybe_solo_zone:
                        await toZone(self.clients, await self.current_leader_client.zone_name())

                    # if we still aren't in correct zone, send all to hub and retry
                    await self.zone_recorrect_hub()
                else:
                    # if still in the wrong zone, try friend teleport
                    await self.zone_recorrect_friend_tp(maybe_solo_zone)
                    await asyncio.sleep(2.0)

            if await is_free(self.current_leader_client):
                distance = calc_Distance(quest_xyz, XYZ(0.0, 0.0, 0.0))
                if distance > 1:
                    if await is_free(self.current_leader_client):
                        try:
                            for c in self.clients:
                                if c.entity_detect_combat_status:
                                    await asyncio.sleep(.1)

                            leader_objective = await self.get_truncated_quest_objectives(self.current_leader_client)

                            # complex teleport logic for defeat quests to prevent mob battle separation
                            if 'defeat' in leader_objective.lower():
                                logger.debug(
                                    'Leader ' + self.current_leader_client.title + ' on defeat quest - staggering teleports')
                                leader_client_objective_xyz = await self.current_leader_client.quest_position.position()

                                location_before_sendback = await self.current_leader_client.body.position()
                                zone_before_teleport = await self.current_leader_client.zone_name()
                                await self.current_leader_client.teleport(leader_client_objective_xyz)
                                await asyncio.sleep(1.0)

                                # we collided and were sent back - we likely aren't in the right zone for our defeat quest
                                distance = calc_Distance(location_before_sendback,
                                                         await self.current_leader_client.body.position())

                                # leader client collided and got sent back
                                if distance < 20:
                                    # dist = await self.distance_to_nearest_mob(self.current_leader_client, is_mob=True)
                                    logger.debug(
                                        'client ' + self.current_leader_client.title + ' collided on initial teleport')
                                    await navmap_tp(client=self.current_leader_client,
                                                    xyz=leader_client_objective_xyz)  # , leader_client=self.current_leader_client)

                                # leader did not collide
                                # else:
                                await asyncio.sleep(1.0)
                                while await self.current_leader_client.is_loading():
                                    await asyncio.sleep(.1)

                                # leader_current_zone = await self.current_leader_client.zone_name()
                                detected_dungeon = await self.detected_interact_from_popup_(self.current_leader_client)

                                # changed zones or we are in front of an interactible
                                if await self.current_leader_client.zone_name() != zone_before_teleport or detected_dungeon:
                                    logger.debug('leader zone changed or interactible reached - syncing all clients')
                                    await asyncio.gather(*[navmap_tp(client=c, xyz=leader_client_objective_xyz,
                                                                     leader_client=self.current_leader_client) for c in
                                                           follower_clients])

                                # objective changed, let questing loop cycle and assign a new leader in case some got left behind
                                elif leader_objective != await self.get_truncated_quest_objectives(
                                        self.current_leader_client):
                                    pass

                                # leader is likely waiting for combat in the correct zone
                                else:
                                    logger.debug('leader waiting for combat')
                                    await asyncio.sleep(1)
                                    sprinter = SprintyClient(self.current_leader_client)
                                    while not self.current_leader_client.entity_detect_combat_status:
                                        try:
                                            await sprinter.tp_to_closest_mob()
                                        # wizwalker throws should update bool even with wait_on_inuse on
                                        except ValueError:
                                            await asyncio.sleep(1.0)

                                        await asyncio.sleep(1.0)

                                    while self.current_leader_client.entity_detect_combat_status:
                                        await asyncio.sleep(.1)

                            # if we aren't doing a mob / boss fight, we have no need to stagger teleports
                            # furthermore staggered teleports can break certain quests in dungeons for certain clients
                            else:
                                await asyncio.gather(
                                    *[navmap_tp(p, quest_xyz, leader_client=self.current_leader_client) for p in
                                      self.clients])

                            for c in self.clients:
                                while await c.is_loading():
                                    await asyncio.sleep(0.1)
                        except:
                            # some level of error output may be required in navmap_tp, at the moment it is not producing output without traceback
                            print(traceback.print_exc())

                    await asyncio.sleep(0.7)

                    # Handles chest reroll menu, will always cancel
                    await asyncio.gather(*[safe_click_window(c, cancel_chest_roll_path) for c in self.clients])
                    # confirm exit dungeon early button
                    await asyncio.gather(*[safe_click_window(c, exit_dungeon_path) for c in self.clients])

                    current_pos = await self.current_leader_client.body.position()

                    if await is_visible_by_path(self.current_leader_client, npc_range_path) and calc_Distance(
                            quest_xyz, current_pos) < 750.0:
                        # await self.handle_interactibles(current_leader_client)

                        # Handles interactables
                        sigil_msg_check = await self.read_popup_(self.current_leader_client)
                        if "to enter" in sigil_msg_check.lower():
                            logger.debug('Entering dungeon')
                            await self.enter_dungeon()

                            await asyncio.sleep(1.0)

                            # check for instance desync, and attempt to fix if it has happened
                            if questing_friend_tp:
                                num_visible_clients = await self.num_clients_in_same_area()

                                if num_visible_clients == len(self.clients):
                                    pass
                                elif num_visible_clients > 1:
                                    # teleport all, this clearly isnt a solo zone
                                    logger.debug('One or more clients was separated from the group - teleporting all to leader')
                                    await self.correct_dungeon_desync(follower_clients)
                        else:
                            original_zone = await self.current_leader_client.zone_name()
                            logger.debug('Sending X press to all clients')
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

                            if await is_visible_by_path(self.current_leader_client, spiral_door_teleport_path):
                                await self.handle_spiral_navigation()

                    quest_objective = await get_quest_name(self.current_leader_client)

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
                    # Double check - sometimes wiz lies about quest position - a simple sleep and re-grabbing of the quest xyz seems to solve the issue
                    await asyncio.sleep(3.0)
                    quest_xyz = await self.current_leader_client.quest_position.position()
                    distance = calc_Distance(quest_xyz, XYZ(0.0, 0.0, 0.0))

                    if distance < 1:
                        quest_objective = await get_quest_name(self.current_leader_client)

                        truncated_quest_obj = (await self.get_truncated_quest_objectives(self.current_leader_client)).lower()
                        # Key - truncated quest name
                        # Values - 0: time between entity respawns, 1-... : xyz locations of separate entities belonging to the quest
                        compatible_hardcoded_quests = {'collect sea foam crystal in the floating land': [35, XYZ(x=5330.3466796875, y=-1514.7388916015625, z=-499.20001220703125), XYZ(x=6373.23046875, y=-4622.3076171875, z=-534.3988647460938), XYZ(x=4883.55419921875, y=-5877.2265625, z=-518.2752685546875), XYZ(x=2708.878662109375, y=-4461.57568359375, z=-499.1999816894531)] }
                        incompatible_hardcoded_quests = {'find submarine parts in the floating land': [40, XYZ(x=-17412.53515625, y=10505.794921875, z=-429.19927978515625), XYZ(x=-17088.447265625, y=12284.244140625, z=-410.1100769042969), XYZ(x=-21681.78125, y=11547.5966796875, z=-429.19927978515625)]}

                        forbidden_quests = ['Break Mining Equipment in Tyrian Gorge',
                                            'Steal Barrel of Kermes Fire in Tyrian Gorge']

                        if any(map(truncated_quest_obj.__contains__, incompatible_hardcoded_quests.keys())):
                            logger.debug('Hardcoded collect')

                            entity_data = incompatible_hardcoded_quests.get(truncated_quest_obj[:-1])
                            for c in self.clients:
                                if c.process_id != self.current_leader_client.process_id:
                                    current_quest = (await self.get_truncated_quest_objectives(c)).lower()
                                    follower_on_collect = False
                                    safe_location = await c.body.position()
                                    while current_quest == truncated_quest_obj:
                                        follower_on_collect = True
                                        for coord in entity_data[1:]:
                                            try:
                                                await c.teleport(coord)
                                                await asyncio.sleep(1.0)

                                                for i in range(3):
                                                    await c.send_key(Keycode.X)
                                                    await asyncio.sleep(.15)
                                            except ValueError:
                                                pass

                                        current_quest = (await self.get_truncated_quest_objectives(c)).lower()

                                    if follower_on_collect:
                                        while not await is_free(c) or c.entity_detect_combat_status:
                                            await asyncio.sleep(1.0)

                                        if await is_free(c) and not c.entity_detect_combat_status:
                                            await c.teleport(safe_location)
                                        logger.debug('Waiting for collect items to respawn.')
                                        await asyncio.sleep((entity_data[0] + 5))

                            current_quest = truncated_quest_obj
                            safe_location = await self.current_leader_client.body.position()
                            while current_quest == truncated_quest_obj:
                                for coord in entity_data[1:]:
                                    try:
                                        await self.current_leader_client.teleport(coord)
                                        await asyncio.sleep(1.0)

                                        for i in range(3):
                                            await self.current_leader_client.send_key(Keycode.X)
                                            await asyncio.sleep(.15)
                                    except ValueError:
                                        pass

                                current_quest = (await self.get_truncated_quest_objectives(self.current_leader_client)).lower()

                            while not await is_free(self.current_leader_client) or self.current_leader_client.entity_detect_combat_status:
                                await asyncio.sleep(1.0)

                            if await is_free(self.current_leader_client) and not self.current_leader_client.entity_detect_combat_status:
                                await self.current_leader_client.teleport(safe_location)



                            entity_data = incompatible_hardcoded_quests.get(truncated_quest_obj[:-1])
                            current_quest = truncated_quest_obj
                            while current_quest == truncated_quest_obj:
                                await asyncio.sleep(1.0)
                                current_quest = (await self.get_truncated_quest_objectives(self.current_leader_client)).lower()

                            # wait until it is completed manually
                            while any(map(truncated_quest_obj.__contains__, forbidden_quests)):
                                await asyncio.sleep(2)
                                truncated_quest_obj = await get_quest_name(self.current_leader_client)

                            logger.debug('Quest completed manually - continuing Auto Quest.')
                        # if on a bad collect quest, tell the user to complete manually
                        # some zones / quests are impossible to complete or for several reasons should be avoided
                        elif any(map(quest_objective.__contains__, forbidden_quests)):
                            logger.debug('Cannot complete this quest - Please complete it manually to continue.')

                            # wait until it is completed manually
                            while any(map(quest_objective.__contains__, forbidden_quests)):
                                await asyncio.sleep(2)
                                quest_objective = await get_quest_name(self.current_leader_client)

                            logger.debug('Quest completed manually - continuing Auto Quest.')
                        else:

                            leader_obj = await self.get_truncated_quest_objectives(self.current_leader_client)
                            for c in self.clients:
                                if c.process_id != self.current_leader_client.process_id:
                                    follower_obj = await self.get_truncated_quest_objectives(c)

                                    if leader_obj == follower_obj:
                                        collect_quester = Quester(c, self.clients, None)
                                        await collect_quester.auto_collect_rewrite(c)

                            all_clients_moved_on = True
                            for c in self.clients:
                                if c.process_id != self.current_leader_client.process_id:
                                    follower_obj = await self.get_truncated_quest_objectives(c)
                                    if follower_obj == leader_obj:
                                        all_clients_moved_on = False

                            # finally, collect items on the leader
                            # only do this if all clients have already finished their own collects
                            if all_clients_moved_on:
                                await self.auto_collect_rewrite(self.current_leader_client)
                    else:
                        logger.debug('False collect quest detected.  Quest position: ' + str(distance))

    # @logger.catch()
    async def auto_quest_solo(self):
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
                    while self.client.entity_detect_combat_status:
                        await asyncio.sleep(.1)

                    await navmap_tp(self.client, quest_xyz)
                except:
                    # some level of error output may be required in navmap_tp, at the moment it is not producing output without traceback
                    print(traceback.print_exc())

                await asyncio.sleep(0.5)
                if await is_visible_by_path(self.client, cancel_chest_roll_path):
                    # Handles chest reroll menu, will always cancel
                    await click_window_by_path(self.client, cancel_chest_roll_path)

                current_pos = await self.client.body.position()
                if await is_visible_by_path(self.client, npc_range_path) and calc_Distance(quest_xyz,
                                                                                           current_pos) < 750.0:
                    # Handles interactables
                    sigil_msg_check = await self.read_popup_(self.client)
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
                # Double check - sometimes wiz lies about quest position - a simple sleep and re-grabbing of the quest xyz seems to solve the issue
                await asyncio.sleep(3.0)
                quest_xyz = await self.client.quest_position.position()
                distance = calc_Distance(quest_xyz, XYZ(0.0, 0.0, 0.0))

                if distance < 1:
                    await self.auto_collect_rewrite(self.client)

    async def auto_quest(self):
        while self.client.questing_status:
            await asyncio.sleep(1)
            await self.auto_quest_solo()

    async def handle_sigil_wait(self, min_sigil_distance: float = 750.0):
        sprinter = SprintyClient(self.client)
        sigils = await sprinter.get_base_entities_with_name('Teleport Semi Circle 4 Player Generic')

        if sigils:
            nearest_sigil = await sprinter.find_closest_of_entities(sigils)
            nearest_sigil_pos = await nearest_sigil.location()
            current_pos = await self.client.body.position()
            current_zone = await self.client.zone_name()
            if calc_Distance(nearest_sigil_pos, current_pos) < min_sigil_distance:
                while current_zone == await self.client.zone_name():
                    if await is_visible_by_path(self.client, missing_area_path):
                        while not await is_visible_by_path(self.client, missing_area_retry_path):
                            await asyncio.sleep(0.1)
                        await click_window_by_path(self.client, missing_area_retry_path, True)

                    await asyncio.sleep(0.1)

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

            # if quest_pos != XYZ(0.0, 0.0, 0.0):
            # 	break

            elif await is_visible_by_path(self.client, npc_range_path):
                if await is_popup_title_relevant(self.client, relevant_str):
                    await asyncio.gather(*[p.send_key(Keycode.X, 0.1) for p in self.clients])
                    # await self.client.send_key(Keycode.X, 0.1)
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
