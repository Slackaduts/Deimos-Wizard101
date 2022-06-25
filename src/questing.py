from typing import *
import asyncio
from wizwalker import Keycode, XYZ
import math
from loguru import logger
import struct
from io import BytesIO
from src.teleport_math import navmap_tp, TypedBytes, parse_nav_data, calc_chunks
from combat import SlackFighter
from wizwalker import XYZ, Keycode, MemoryReadError
from wizwalker.file_readers.wad import Wad
from src.sprinty_client import SprintyClient
from src.utils import get_window_from_path, click_window_by_path, is_visible_by_path
from wizwalker.extensions.scripting import teleport_to_friend_from_list 
from fuzzywuzzy import fuzz

type_format_dict = {
"char": "<c",
"signed char": "<b",
"unsigned char": "<B",
"bool": "?",
"short": "<h",
"unsigned short": "<H",
"int": "<i",
"unsigned int": "<I",
"long": "<l",
"unsigned long": "<L",
"long long": "<q",
"unsigned long long": "<Q",
"float": "<f",
"double": "<d",
}

npc_range_path = ['WorldView', 'NPCRangeWin']
decline_quest_path = ['WorldView', 'wndDialogMain', 'btnLeft']
advance_dialog_path = ['WorldView', 'wndDialogMain', 'btnRight']
dialogue_window_path = ['WorldView', 'wndDialogMain']
universe_map_window = ['WorldView', '']
dungeon_warning_path = ['MessageBoxModalWindow', 'messageBoxBG']
multiple_quests_path = ['WorldView', 'NPCServicesWin', 'ControlSprite', 'Layout', 'Option1']
spiral_door_cycle_path = ['WorldView', '', 'messageBoxBG', 'ControlSprite', 'optionWindow', 'rightButton']
spiral_door_teleport_path = ['WorldView', '', 'messageBoxBG', 'ControlSprite', 'teleportButton']
spiral_door_path = ['WorldView', '', 'messageBoxBG', 'ControlSprite', 'optionWindow']
quest_name_path =[ "WorldView", "windowHUD" , "QuestHelperHud", "ElementWindow", "" ,"txtGoalName"]
popup_title_path =["WorldView", "NPCRangeWin","wndTitleBackground","NPCRangeTxtTitle"]



class Quester():
	def __init__(self, client, clients):
		self.client = client
		self.clients = clients


	async def find_quest_world(self):
		await click_window_by_path(self.client, path=spiral_door_teleport_path)


	class TypedBytes(BytesIO):
		def split(self, index: int) -> Tuple["TypedBytes", "TypedBytes"]:
			self.seek(0)
			buffer = self.read(index)
			return type(self)(buffer), type(self)(self.read())
		def read_typed(self, type_name: str):
			type_format = type_format_dict[type_name]
			size = struct.calcsize(type_format)
			data = self.read(size)
			return struct.unpack(type_format, data)[0]


	async def find_if_questhelper(self):
		quest_name = await get_window_from_path(self.client.root_window, quest_name_path)
		unsplitted = await quest_name.maybe_text()
		try:
			quest_helper = unsplitted.split("\n</center>")
			unsplitted = quest_helper[1]
		except IndexError:
			return False
		return True
		


	async def parse_quest_stuff(self,quest_name_path):
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
			split2_qst = split1_qst[1].split(" in") #Parsing the quest name
		except IndexError:
			split2_qst = split1_qst[0].split("  in")
		questnameparsed = split2_qst[0]

		#example of a collect quest the only stuff that change are
		#"Cog", "Triton Avenue" and "(0 of 3)" the rest is static
		#<center>Collect Cog in Triton Avenue (0 of 3)</center>

		split1_amt = unsplitted.split(" (")
		split2_amt = split1_amt[1].replace(")</center>", "")
		amount_to_get_parsed = split2_amt.split("of ")[1] #Parsing the amount of stuff to pick up
		amount_gotten_parsed = split2_amt.split(" of")[0] #Parsing the amount of stuff that has been picked up

		return questnameparsed, f"{amount_gotten_parsed} / {amount_to_get_parsed}"


	async def parse_name_talk_to(self,quest_name_path):
		questnameparsed = []
		quest_name = await get_window_from_path(self.client.root_window, quest_name_path)
		unsplitted = await quest_name.maybe_text()
		unsplitted = unsplitted.lower()
		split1_qst = unsplitted.split("<center>talk to ")
		split2_qst = split1_qst[1].split(" in") #Parsing the quest name
		questnameparsed.append(split2_qst[0])
		return questnameparsed


	async def find_quest_type(self, quest_name_path):
		quest_name_path = await get_window_from_path(self.client.root_window, quest_name_path)
		quest_msg = await quest_name_path.maybe_text()
		print(quest_msg)

		if "Talk To" in quest_msg:
			#talk to quest
			quest_type = "talk to"
			return quest_type

		elif "Defeat " in quest_msg and not "(" in quest_msg and not "collect" in quest_msg.lower():
			#defeat quests mostly bosses
			quest_type = "defeat & collect"
			return quest_type

		elif "Defeat " in quest_msg and "(" in quest_msg and not "collect" in quest_msg.lower():
			#defeat multiple
			quest_type = "defeat & collect"
			return quest_type

		elif "Defeat " in quest_msg and not "(" in quest_msg and  "collect" in quest_msg.lower():
			# weird collect quest from mob
			quest_type = "defeat & collect"
			return quest_type

		elif "Defeat " in quest_msg and "(" in quest_msg and "collect" in quest_msg.lower():
			# defeat and collect
			quest_type = "defeat & collect"
			return quest_type

		elif "Use" in quest_msg and not "defeat " in quest_msg.lower() and not "(" in quest_msg and not "collect" in quest_msg.lower():
			quest_type = "talk to" #aaaaaaaaah
			return quest_type

		elif "Find " in quest_msg and not "defeat " in quest_msg.lower() and not "(" in quest_msg and not "collect" in quest_msg.lower():
			#find quest similar to goto
			quest_type = "talk to"
			return quest_type

		elif "Craft " in quest_msg:
			# craft quests
			quest_type = "craft"
			return quest_type

		elif "Photomance" in quest_msg:
			quest_type = "Photomance"
			return quest_type

		elif "Go To" in quest_msg.lower():
			# goto quests
			quest_type = "talk to"
			return quest_type
		elif "Free " in quest_msg:
			quest_type = "talk to"
			return quest_type
		#elif not "Defeat " in quest_msg.lower() and "(" in quest_msg and "collect" in quest_msg.lower():
			# collect
		#	quest_type = "collect"
		#	return quest_type

		#elif "Open " in quest_msg and "(" in quest_msg:
		#	quest_type = "collect"
		#	return quest_type

		#elif "Use" in quest_msg and not "defeat " in quest_msg.lower() and "(" in quest_msg and not "collect" in quest_msg.lower():
			#quest_type = "collect" #aaaaaaaaah
			#return quest_type
		elif "(" in quest_msg and "of" in quest_msg.lower() and ")" in quest_msg:
			quest_type = "collect" 
			return quest_type
		else:
			quest_type = "talk to"
			return quest_type


	async def click_stuff(self):
		path = (
		["WorldView", "ClassPicture", "exit"],["WorldView", "HelpHousingTips2", "toolbar","exit"],
		["WorldView","windowHUD","compassAndTeleporterButtons","ResumeInstanceButton"],["MessageBoxModalWindow","messageBoxBG","messageBoxLayout","AdjustmentWindow","Layout","rightButton"], ["MessageBoxModalWindow","messageBoxBG","messageBoxLayout","AdjustmentWindow","Layout","leftButton"])
		for i in path:
			click_button = await get_window_from_path(self.client.root_window, i)
			if click_button:
				if await click_button.is_visible():
					await self.client.mouse_handler.activate_mouseless()
					await self.client.mouse_handler.click_window(click_button)
					await self.client.mouse_handler.deactivate_mouseless()
     
	@logger.catch()
	async def boosting_logic(self):
		boosting_bool = True
		while boosting_bool and self.client.questing_status:
			#finding what client is p1
			if not self.client.title == "p1":
				await self.auto_health()
				await self.combat()
				#print("1")
				#notp1= [c for c in self.clients if not c.title == "p1"]
				p1 = [c for c in self.clients if c.title == "p1"]
				p1 = p1[0]
				#print("2")
				p1zonename = await p1.zone_name()
				#print("3")
				p1xyz = await p1.body.position()
				#print("4")
				if await self.client.zone_name() == p1zonename and not await self.client.body.position() == p1xyz:
					#print("5")
					await self.client.teleport(p1xyz, wait_on_inuse = True)
					await self.client.send_key(key=Keycode.A, seconds=0.2)
					await self.client.send_key(key=Keycode.D, seconds=0.2)
					await self.combat()
					#print("6")
				else:
					#print("7")
					try:
						await self.client.mouse_handler.activate_mouseless()
					except:
						pass
					#print("8")
					await self.client.send_key(key=Keycode.F, seconds=0.1)
					try:
						await teleport_to_friend_from_list(client=self.client, icon_list=1, icon_index=50)
					except:
						pass
					#print("9")
					try:
						await self.client.mouse_handler.deactivate_mouseless()
					except:
						pass
					#print("10")
					await asyncio.sleep(3)
					#print("11")
					await self.click_stuff()
					await self.combat()

					#print("8")
				if await is_visible_by_path(self.client, path=npc_range_path) or await is_visible_by_path(self.client, path=dialogue_window_path):
					sigil_msg_check = await self.read_popup_()
					if "to enter" in sigil_msg_check.lower():
						await self.client.send_key(key=Keycode.X, seconds=0.1) #if in npc range press x
						zone_name = await self.client.zone_name()
						countdown = 17
						print("wating for zone change ")
						while await self.client.zone_name() == zone_name and countdown > 0 and self.client.questing_status:
							await asyncio.sleep(1)
							countdown -= 1
			else:
				break
	@logger.catch()
	async def auto_quest(self):
		
		#a = await self.Nav_Hull()
		#print(a)
		#for i in a:
			#await self.client.teleport(i)
			#await asyncio.sleep(4)
		#return
  
		await self.boosting_logic()
		
		await self.loading_check()

		#await self.dialog()

		await self.auto_health()

		await self.click_stuff()

		await self.tp_to_quest_mob()

		await self.combat()
		
		await self.auto_health()
		quest_type = await self.find_quest_type(quest_name_path)
		print(quest_type)
		if quest_type == "talk to":
			#TODO add code for going to new world
			while True and self.client.questing_status:
				#await self.dialog()
				try:
					await navmap_tp(client=self.client) #teleports to the npc
				except:
					await asyncio.sleep(0.1)
				await self.loading_check()
				await self.world_door_check()
				#await self.dialog()
				#await self.tp_to_quest_mob2()
				if await is_visible_by_path(self.client, path=npc_range_path) or await is_visible_by_path(self.client, path=dialogue_window_path): # checks twice for bug fix
					#if await self.parse_name_talk_to(quest_name_path) in await self.read_popup_()
					sigil_msg_check = await self.read_popup_()
					txtmsg = await get_window_from_path(self.client.root_window,popup_title_path)
					maybe = await txtmsg.maybe_text()
					quest_name = await get_window_from_path(self.client.root_window, quest_name_path)
					quest_msg = await quest_name.maybe_text()
					if not maybe.lower() in quest_msg.lower():
						try:
							await navmap_tp(client=self.client) #teleports to the npc
						except:
							await asyncio.sleep(0.1)
						await asyncio.sleep(1)#fixes repair bug
					if await is_visible_by_path(self.client, path=npc_range_path) or await is_visible_by_path(self.client, path=dialogue_window_path):
						if "to enter" in sigil_msg_check.lower():
							await self.client.send_key(key=Keycode.X, seconds=0.1) #if in npc range press x
							zone_name = await self.client.zone_name()
							countdown = 17
							print("wating for zone change ")
							while await self.client.zone_name() == zone_name and countdown > 0 and self.client.questing_status:
								await asyncio.sleep(1)
								countdown -= 1
							await asyncio.sleep(1)
							await self.loading_check()
							#await self.dialog()
							await self.client.send_key(key=Keycode.W, seconds=0.3)
							quest_type = await self.find_quest_type(quest_name_path)
							if quest_type == "talk to":
								await self.boss_check()
						else:
							await self.client.send_key(key=Keycode.X, seconds=0.1)
						await asyncio.sleep(0.5)
						await self.world_door_check()
						#await self.dialog() # does dialog that may pause and start again
						#for i in range(3):
							#await asyncio.sleep(1)
						#	if await is_visible_by_path(self.client, path=dialogue_window_path):
								#await self.dialog()
								#break
				#await self.dialog()
				break
		elif quest_type == "defeat & collect":
			#TODO somehow be able to get mobs
			while True and self.client.questing_status:
				#await self.dialog()
				if await self.tp_to_quest_mob():
					print("tped to mob")
				else:
					print("could not tp to mob")
					print("navmap tping")
					try:
						await navmap_tp(client=self.client)
					except:
						await asyncio.sleep(0.1)
				await self.tp_to_quest_mob()
				await self.loading_check()
				await self.world_door_check()
				# check for sigil code
				if await is_visible_by_path(self.client, path=npc_range_path):
					sigil_msg_check = await self.read_popup_()
					await asyncio.sleep(1)
					if "to enter" in sigil_msg_check.lower():
						await self.client.send_key(key=Keycode.X, seconds=0.1)
						zone_name = await self.client.zone_name()
						countdown = 17
						print("wating for zone change ")
						while await self.client.zone_name() == zone_name and countdown > 0 and self.client.questing_status:
							await asyncio.sleep(1)
							countdown -= 1
						await self.loading_check()
						#await self.dialog()
						await self.client.send_key(key=Keycode.W, seconds=0.3)
						try:
							await navmap_tp(client=self.client)
						except:
							await asyncio.sleep(0.1)
						await self.loading_check()
						#await self.dialog()
						print("going into battle")
						for i in range(10):
							await asyncio.sleep(0.35)
							await self.tp_to_quest_mob()
					else:
						await self.client.send_key(key=Keycode.X, seconds=0.1)

				break

		elif quest_type == "go to":
			while quest_type == "go to" and self.client.questing_status:
				try:
					await navmap_tp(client=self.client)
				except:
					await asyncio.sleep(0.1)
				await self.loading_check()
				await self.world_door_check()
				if await is_visible_by_path(self.client, path=npc_range_path):
					sigil_msg_check = await self.read_popup_()
					if "to enter" in sigil_msg_check.lower():
						await self.client.send_key(key=Keycode.X, seconds=0.1)
						zone_name = await self.client.zone_name()
						countdown = 17
						print("wating for zone change ")
						while await self.client.zone_name() == zone_name and countdown > 0:
							await asyncio.sleep(1)
							countdown -= 1
						await self.loading_check()
						#await self.dialog()
						await self.client.send_key(key=Keycode.W, seconds=0.3)
						try:
							await navmap_tp(client=self.client)
						except:
							await asyncio.sleep(0.1)
						await self.loading_check()
						#await self.dialog()
						for i in range(10):
							await self.combat()
							await asyncio.sleep(0.2)
						break
					else:
						await self.client.send_key(key=Keycode.X, seconds=0.1)
					quest_type = await self.find_quest_type(quest_name_path)
					break
		elif quest_type == "collect":
			while True and self.client.questing_status:
				await self.auto_collect()
				break
		elif quest_type == "use":
			while True and self.client.questing_status:
				try:
					await navmap_tp(client=self.client)
				except:
					await asyncio.sleep(0.1)
				await self.loading_check()
				#await self.dialog()
				if await is_visible_by_path(self.client, path=npc_range_path):
					await self.client.send_key(key=Keycode.X, seconds=0.1) #if in npc range press x
				break
		elif quest_type == "Photomance":
			while True and self.client.questing_status:
				try:
					await navmap_tp(client=self.client)
				except:
					await asyncio.sleep(0.1)
				await self.loading_check()
				await self.client.send_key(key=Keycode.Z, seconds=0.1)
				await self.client.send_key(key=Keycode.Z, seconds=0.1)
				break


	async def world_door_check(self):
		if await is_visible_by_path(self.client, path=npc_range_path):
			sigil_msg_check = await self.read_popup_()
			if "interact" in sigil_msg_check.lower():
				await self.client.send_key(key=Keycode.X, seconds=0.1)
				await asyncio.sleep(1)
			if await is_visible_by_path(self.client, path=spiral_door_path):
					await self.client.mouse_handler.activate_mouseless()
					await self.find_quest_world()
					await self.client.mouse_handler.deactivate_mouseless()
					await asyncio.sleep(0.1)
					await self.loading_check()


	async def loading_check(self):
		await asyncio.sleep(1)
		while await self.client.is_loading() and self.client.questing_status:
			await asyncio.sleep(0.1)


	async def boss_check(self):
		sprinty = SprintyClient(self.client)
		try:
			entities=await sprinty.get_mobs()
			for i in entities:
				temp = await i.object_template()
				name= await temp.object_name()
				if "Boss-" in name:
					await sprinty.tp_to(i)
					return True
		except:
			return False


	async def combat(self):
		battle = SlackFighter(self.client, self.clients)
		while await battle.is_fighting() == True and self.client.questing_status:
			await asyncio.sleep(0.1)
		#else:
			#if await self.find_if_questhelper():
				#clients = [c for c in self.clients if not self.client == c]
				#for i in clients:
				#	otherbattle = SlackFighter(i)
					#if await otherbattle.is_fighting() == True:
					#	logger.debug("teleporting to player")
					#	await self.client.mouse_handler.activate_mouseless()
					#	try:
					#		await teleport_to_friend_from_list(client=self.client, icon_list=1, icon_index=50)
					#		await asyncio.sleep(5)
					#		#send a key
					#		await self.client.send_key(key=Keycode.W, seconds=0.3)
					#		await self.client.send_key(key=Keycode.S, seconds=0.3)
					#	except:
					#		await asyncio.sleep(0)
					#	await self.client.mouse_handler.deactivate_mouseless()


	async def combat1(self):
		#TODO: add check for having a high level carry
		battle = SlackFighter(self.client,self.clients)
		if await battle.is_fighting()== True:
		#	if len(self.clients) >= 2:
		#		for player in self.clients:
		#			if not player == self.client:
		#				logger.debug("teleporting to player")
		#				await player.mouse_handler.activate_mouseless()
		#				await asyncio.sleep(0.25)
		#				try:
		#					await teleport_to_friend_from_list(client=player, icon_list=1, icon_index=50)
		#				except:
		#					await asyncio.sleep(0)
		#				await player.mouse_handler.deactivate_mouseless()
			logger.debug(f'Client {self.client.title} in combat, handling combat.')
			self.client.combat_status = True
			await battle.wait_for_combat()
			logger.debug(f'Client {self.client.title} combat ended, closing combat.')
			self.client.combat_status = False
			await asyncio.sleep(4)
			#await self.dialog()


	async def read_popup_(self):
		popup_msgtext_path =["WorldView", "NPCRangeWin","imgBackground","NPCRangeTxtMessage"]
		try:
			popup_text_path = await get_window_from_path(self.client.root_window,popup_msgtext_path)
			txtmsg = await popup_text_path.maybe_text()
		except:
			txtmsg = ""
		return txtmsg


	async def dialog(self):
		await asyncio.sleep(1)
		if await is_visible_by_path(self.client, path=dialogue_window_path):
		# dialogue handling
			await self.client.mouse_handler.activate_mouseless()
			while await is_visible_by_path(self.client, path=dialogue_window_path) and self.client.questing_status:
				if await is_visible_by_path(self.client, path=decline_quest_path):
					await click_window_by_path(self.client, path=decline_quest_path)
				else:
					await click_window_by_path(self.client, path=advance_dialog_path)
				await asyncio.sleep(0.1)
			await self.client.mouse_handler.deactivate_mouseless()
		await asyncio.sleep(0.1)
		while await is_visible_by_path(self.client, path=multiple_quests_path) and self.client.questing_status:
			await self.client.mouse_handler.activate_mouseless()
			# if the NPC's quest menu had multiple options, this might break non-dialogue NPCS like bazaar
			await click_window_by_path(self.client, path=multiple_quests_path)
			await self.client.mouse_handler.deactivate_mouseless()

	async def find_safe_entities_from(self, fixed_position1, fixed_position2, safe_distance: float = 700, is_mob: bool = False):
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
			dist = math.dist(p, fixed_position1)
		try:
			if dist < safe_distance:
				return False
			else:
				can_Teleport = True
		except TypeError:
			pass
		return can_Teleport


	async def read_popup_title(self,parsed_quest_info):
		popup_title_path =["WorldView", "NPCRangeWin","wndTitleBackground","NPCRangeTxtTitle"]
		txtmsg = await get_window_from_path(self.client.root_window,popup_title_path)
		maybe_collect_item = await txtmsg.maybe_text()
		if maybe_collect_item.lower() in str(parsed_quest_info[0]).lower():
			return True
		return False

	async def find_quest_entites(self, parsed_quest_info: list, entity: dict):
		types_list = ['BehaviorInstance', 'ObjectStateBehavior', 'RenderBehavior', 'SelectBehavior','CollisionBehaviorClient']
		points = await self.Nav_Hull()
		Hull = points #[0::2]  # TODO remove points that are close to draw distance of each other
		# teleport around the hull and collect rendered objects, add them to a dict and their location
		for points in Hull:
			points = XYZ(points.x, points.y, points.z - 550)
			await self.client.teleport(points, move_after=False,wait_on_inuse=True)
			await self.client.teleport(points,wait_on_inuse=True)
			entities = await self.client.get_base_entity_list()
			for e in entities:
				try:
					object_template = await e.object_template()
					display_name_code = await object_template.display_name()
					display_name = await self.client.cache_handler.get_langcode_name(display_name_code)
					print(parsed_quest_info, display_name)
					match = fuzz.ratio(display_name.lower(),str(parsed_quest_info[0]).lower())
					#if parsed_quest_info[0].lower() == display_name.lower():
					if match > 80:
						duplicate = False
						xyz = await e.location()
						if display_name in entity:
							for i in entity[display_name]:
								if str(i) == str(xyz):
									duplicate = True
							if duplicate == False:
								entity[display_name].append(xyz)
						else:
							# create a new array in this slot
							entity[display_name] = [xyz]
							break
				except MemoryReadError:
					await asyncio.sleep(0.05)
				except AttributeError:
					await asyncio.sleep(0.05)
				except ValueError:
					pass


	async def find_quest_entites_fuzzywuzzy(self, parsed_quest_info:list ,entity: dict):
		#types_list = ['BehaviorInstance', 'ObjectStateBehavior', 'RenderBehavior', 'SelectBehavior', 'CollisionBehaviorClient']
		points = await self.Nav_Hull()
		Hull = points #[0::2] # TODO remove points that are close to draw distance of each other
		#teleport around the hull and collect rendered objects, add them to a dict and their location
		for points in Hull:
			points = XYZ(points.x, points.y, points.z - 350)
			await self.client.teleport(points,move_after = False,wait_on_inuse = True)
			await self.client.teleport(points,wait_on_inuse = True)
			entities = await self.client.get_base_entity_list()
			for e in entities:
				types_app = []
				try:
					temp = await e.object_template()
					ename = str(await temp.object_name())
					print(ename)
					if not ename == "Basic Positional":
						name_list = ename.split('_')
						edited_name = ''.join(name_list[1:])
						#do stripping symbols stuff with edited_name
						res = ''.join([i for i in edited_name if not i.isdigit()])	
						name2 = str(res).replace("_","")
						#name3 = re.findall('[A-Z][a-z]*', name2)
						match = fuzz.ratio(name2.lower(),str(parsed_quest_info[0]).lower())
						if int(match) > 70:
							duplicate = False
							xyz = await e.location()
							if name2 in entity:
								for i in entity[name2]:
									if str(i) == str(xyz):
										duplicate = True
								if duplicate == False:
									entity[name2].append(xyz)
							else:
								# create a new array in this slot
								entity[name2] = [xyz]
								break
				except MemoryReadError:
					await asyncio.sleep(0.05)
				except AttributeError:
					await asyncio.sleep(0.05)


	async def load_wad(self, path: str):
			return Wad.from_game_data(path.replace("/", "-"))


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
		#glist = [(0, 0)]
		# glist = concavehull(XY, chi_factor=0.1)
		#print(XY)
		
		#print(master_list)
		for a in XY:
			for l in vertices:
				if a[0] == l.x:
					if a[1] == l.y:
						master_list.append(l)
		#print(master_list)
		#print(master_list)
		current_pos = await self.client.body.position()
		full = calc_chunks(master_list, entity_distance=1500)
		return full


	async def auto_collect(self):
		cli = SprintyClient(self.client)
		quest_name_path =[ "WorldView", "windowHUD" , "QuestHelperHud", "ElementWindow", "" ,"txtGoalName"]
		popup_msgtext_path =["WorldView", "NPCRangeWin","imgBackground","NPCRangeTxtMessage"]
		# popup_title_path =["WorldView", "NPCRangeWin"]
		entity = dict()
		entity2 = dict()
		collect_counter = 0
		safe_cords = await self.client.body.position()
		completed = False
		if result := await self.parse_quest_stuff(quest_name_path):
			parsed_quest_info = result
		else:
			return
		await self.find_quest_entites(parsed_quest_info,entity)
		if not entity:
			await self.find_quest_entites_fuzzywuzzy(parsed_quest_info, entity)
		print(f"{entity=}")
		failsafe = 0
		for key in entity.keys():
			while completed == False and self.client.questing_status:
				for i in entity[key]:
					await self.combat()
					print(i)
					# telports under quest items
					print("tp under quest item " + str(key))
					await self.client.teleport(XYZ(i.x, i.y, i.z - 350), wait_on_inuse = True)
					# for every cord in the correct quest name item
					await self.client.teleport(XYZ(i.x, i.y, i.z - 350), move_after=False, wait_on_inuse = True)
					await asyncio.sleep(.5)
					await self.client.teleport(XYZ(i.x, i.y, i.z - 350))
					await asyncio.sleep(.5)
					can_Teleport = await self.find_safe_entities_from(i, None , safe_distance=2600, is_mob=True) # checks if safe to collect
					#print(can_Teleport)
					if can_Teleport == True:
						try:
							await navmap_tp(self.client, i)  # teleports to the npc
							#await asyncio.sleep(1)
							if await is_visible_by_path(self.client, path=npc_range_path):
								await self.client.send_key(Keycode.X, .1)
								print('Collecting')
								collect_counter = collect_counter + 1
								#await asyncio.sleep(2)
						except:
							await asyncio.sleep(0.01)
					await self.combat()
					try:
						_ , count = await self.parse_quest_stuff(quest_name_path) # breaks when collect quest format for the string under the pointer
						count_nums = count.split(" / ")
						print(count_nums)
						if collect_counter >= (int(count_nums[1]) - int(count_nums[0])):
							completed = True
							await self.client.teleport(safe_cords, wait_on_inuse = True)
							print("finished quest")
							return True
					except IndexError:
							completed = True
							await self.client.teleport(safe_cords, wait_on_inuse = True)
							print("finished quest")
							return True
					await self.combat()


	async def auto_health(self):
		sprinty = SprintyClient(self.client)
		if await sprinty.needs_potion(health_percent=65, mana_percent=5)== True:
			x=0
			while await sprinty.needs_potion(health_percent=80, mana_percent=5)== True or x > 5 and self.client.questing_status:
				await sprinty.tp_to_closest_health_wisp(only_safe=True)
				await asyncio.sleep(1)
				x=x+1
				if x>5:
					x=0
					break
			while await sprinty.needs_potion(health_percent=5, mana_percent=50) == True or x > 5 and self.client.questing_status:
				await sprinty.tp_to_closest_mana_wisp(only_safe=True)
				await asyncio.sleep(1)
				x=x+1
				if x>5:
					x=0
					break
			if await sprinty.needs_potion(health_percent=65, mana_percent=5) and await sprinty.has_potion():
				await self.client.mouse_handler.activate_mouseless()
				await sprinty.use_potion()
				await self.client.mouse_handler.deactivate_mouseless()
			if await sprinty.needs_potion(health_percent=65, mana_percent=5) and not await sprinty.has_potion():
				await self.client.mouse_handler.activate_mouseless()
				await self.auto_buy_potions()
				await self.client.mouse_handler.deactivate_mouseless()


	async def auto_buy_potions(self):
		default_house = True
		potion_ui_buy = [
		"fillallpotions",
		"buyAction",
		"btnShopPotions",
		"centerButton",
		"fillonepotion",
		"buyAction",
		"exit"
	]
		# Head to home world gate
		await asyncio.sleep(0.1)
		await self.client.send_key(Keycode.HOME, 0.1)
		await asyncio.sleep(3)
		await self.loading_check()
		house_name = await self.client.zone_name()
		if house_name == "WizardCity/Interiors/WC_Housing_Dorm_Interior":
			default_house == True
		if not default_house:
			while not await self.client.is_in_npc_range() and self.client.questing_status:
				await self.client.send_key(Keycode.S, 0.1)
			await self.client.send_key(Keycode.X, 0.1)
			await asyncio.sleep(1.2)
			# Go to Wizard City
			await self.client.mouse_handler.click_window_with_name('wbtnWizardCity')
			await asyncio.sleep(0.15)
			await self.client.mouse_handler.click_window_with_name('teleportButton')
			await self.loading_check()
			# Walk to potion vendor
			await self.client.goto(-0.5264079570770264, -3021.25244140625)
			await self.client.send_key(Keycode.W, 0.5)
			await self.loading_check()
		elif default_house:
			await self.client.send_key(Keycode.S, 3)
			await asyncio.sleep(1.2)
			await self.loading_check()
		recall = await get_window_from_path(self.client.root_window,["WorldView","windowHUD","compassAndTeleporterButtons","ResumeInstanceButton"])
		if recall:
			dungeon= True
		#await self.client.goto(11.836355209350586, -1816.455078125)
		await self.client.teleport(XYZ(17.419727325439453, -1792.14453125, -88.03915405273438),6.255690097808838)
		await self.client.send_key(Keycode.W, 0.5)
		await self.loading_check()
		await self.client.goto(-880.2447509765625, 747.2051391601562)
		await self.client.goto(-4272.06884765625, 1251.950927734375)
		await asyncio.sleep(0.3)
		if not await self.client.is_in_npc_range():
			await self.client.teleport(-4442.06005859375, 1001.5532836914062)
		await self.client.send_key(Keycode.X, 0.1)
		await asyncio.sleep(6)
		# Buy potions
		for i in potion_ui_buy:
			await self.client.mouse_handler.click_window_with_name(i)
			await asyncio.sleep(1)
		# Return
		if dungeon:
			await self.client.mouse_handler.click_window(recall)
			await self.loading_check()


	async def tp_to_quest_mob(self):
		await self.loading_check()
		battle = SlackFighter(self.client, self.clients)
		sprinty = SprintyClient(self.client)
		quest_name = await get_window_from_path(self.client.root_window, quest_name_path)
		quest = await quest_name.maybe_text()
		quest_msg = quest
		if "defeat" in quest_msg.lower():
			quest_parse = quest_msg.split("<center>Defeat ")
			quest_parse2 = quest_parse[1].split(" and ")
			if not len(quest_parse2) == 2:
				quest_parse2 = quest_parse[1].split(" in ")
				final_parse = quest_parse2[0]
			else:
				final_parse = quest_parse2[0]

			attempts_to_find_closest_health_wisp = 0
			if await sprinty.needs_health(health_percent=80):
				while attempts_to_find_closest_health_wisp < 25 and self.client.questing_status:
					attempts_to_find_closest_health_wisp = attempts_to_find_closest_health_wisp + 1
					logger.debug(f' {attempts_to_find_closest_health_wisp} Attempts to collect Health Wisp after battle when health is less than 80% ')
					await sprinty.tp_to_closest_health_wisp(only_safe=True)

			ent = await self.client.get_base_entity_list()
			for i in ent:
				k = await i.inactive_behaviors()
				for j in k:
					if await j.read_type_name() == "NPCBehavior":
						if await j.read_value_from_offset(288, "bool") == True:
							mob = await self.behavior_npc_name(j)
							mob_name = await self.mob_name_parser(mob)
							#percentage = fuzz.ratio(final_parse, mob_name)
							if final_parse in mob_name:
								while not await battle.is_fighting() and self.client.questing_status:
									await sprinty.tp_to(i)
									await asyncio.sleep(0.2)
								return True


	async def tp_to_quest_mob2(self):
		sprinty = SprintyClient(self.client)
		quest_name_path =[ "WorldView", "windowHUD" , "QuestHelperHud", "ElementWindow", "" ,"txtGoalName"]
		quest_name_path = await get_window_from_path(self.client.root_window, quest_name_path)
		quest_msg = await quest_name_path.maybe_text()
		ent = await sprinty.get_mobs()
		print("hi")
		print(ent)
		display_list = []
		for i in ent:
			ant = await i.object_template()
			display_key = await ant.display_key()
			print(display_key)
			if len(display_key):
				display_list.append(display_key)
		print(display_list)
		for i in display_list:
			print(await self.client.cache_handler.get_langcode_name(i))
			#name =  await self.client.cache_handler.get_langcode_name(display_key)
			#print(name)
			#mob_name = await self.mob_name_parser(name)
			#if mob_name.lower() in quest_msg.lower():
			#	await sprinty.tp_to(i)


	async def behavior_npc_name(self,behavior):
		return await behavior.read_wide_string_from_offset(120)


	async def mob_name_parser(self,behavior):
		#"Ronin Mutineer <image;Myth> Rank 5 Elite"
		unsplit = behavior
		split1 = unsplit.split(" <")
		mob_name = split1[0]
		return mob_name

