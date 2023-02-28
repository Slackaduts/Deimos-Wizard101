from enum import Enum, auto
import gettext
import queue
import re
import PySimpleGUI as gui
from src.combat_objects import school_id_to_names
from src.paths import wizard_city_dance_game_path
from src.utils import assign_pet_level


gettext.bindtextdomain('messages', 'locale')
gettext.textdomain('messages')
tl = gettext.gettext


# TODO: Update deimos.py to work with new stuff here


class GUICommandType(Enum):
	# deimos <-> window
	Close = auto()

	# window -> deimos
	ToggleOption = auto()
	Copy = auto()
	SelectEnemy = auto()

	Teleport = auto()
	CustomTeleport = auto()
	EntityTeleport = auto()

	XYZSync = auto()
	XPress = auto()

	GoToZone = auto()
	GoToWorld = auto()
	GoToBazaar = auto()

	RefillPotions = auto()

	AnchorCam = auto()
	SetCamPosition = auto()
	SetCamDistance = auto()

	ExecuteFlythrough = auto()
	KillFlythrough = auto()

	ExecuteBot = auto()
	KillBot = auto()

	# SetPetWorld = auto()

	SetScale = auto()

	# deimos -> window
	UpdateWindow = auto()
	UpdateWindowValues = auto()


# TODO:
# - inherit from StrEnum in 3.11 to make this nicer
# - fix naming convention, it's inconsistent
class GUIKeys:
	toggle_speedhack = "togglespeedhack"
	toggle_combat = "togglecombat"
	toggle_dialogue = "toggledialogue"
	toggle_sigil = "togglesigil"
	toggle_questing = "toggle_questing"
	toggle_auto_pet = "toggleautopet"
	toggle_freecam = "togglefreecam"
	toggle_camera_collision = "togglecameracollision"

	hotkey_quest_tp = "hotkeyquesttp"
	hotkey_freecam_tp = "hotkeyfreecamtp"

	mass_hotkey_mass_tp = "masshotkeymasstp"
	mass_hotkey_xyz_sync = "masshotkeyxyzsync"
	mass_hotkey_x_press = "masshotkeyxpress"

	copy_position = "copyposition"
	copy_zone = "copyzone"
	copy_rotation = "copyrotation"
	copy_entity_list = "copyentitylist"
	copy_ui_tree = "copyuitree"
	copy_camera_position = "copycameraposition"
	copy_stats = "copystats"
	copy_camera_rotation = "copycamerarotation"

	button_custom_tp = "buttoncustomtp"
	button_entity_tp = "buttonentitytp"
	button_go_to_zone = "buttongotozone"
	button_mass_go_to_zone = "buttonmassgotozone"
	button_go_to_world = "buttongotoworld"
	button_mass_go_to_world = "buttonmassgotoworld"
	button_go_to_bazaar = "buttongotobazaar"
	button_mass_go_to_bazaar = "buttonmassgotobazaar"
	button_refill_potions = "buttonrefillpotions"
	button_mass_refill_potions = "buttonmassrefillpotions"
	button_set_camera_position = "buttonsetcameraposition"
	button_anchor = "buttonanchor"
	button_set_distance = "buttonsetdistance"
	button_view_stats = "buttonviewstats"
	button_swap_members = "buttonswapmembers"
	button_execute_flythrough = "buttonexecuteflythrough"
	button_kill_flythrough = "buttonkillflythrough"
	button_run_bot = "buttonrunbot"
	button_kill_bot = "buttonkillbot"
	button_set_scale = "buttonsetscale"


class GUICommand:
	def __init__(self, com_type: GUICommandType, data=None):
		self.com_type = com_type
		self.data = data


def hotkey_button(name: str, key, auto_size: bool, text_color: str, button_color: str):
	return gui.Button(name, button_color=(text_color, button_color), auto_size_button=auto_size, key=key)


def create_gui(gui_theme, gui_text_color, gui_button_color, tool_name, tool_version, gui_on_top):
	gui.theme(gui_theme)

	gui.popup(tl('Deimos will always be free and open-source.\nBy using Deimos, you agree to the GPL v3 license agreement.\nIf you bought this, you got scammed!'), title=tl('License Agreement'), keep_on_top=True, text_color=gui_text_color, button_color=(gui_text_color, gui_button_color))

	global hotkey_button
	original_hotkey_button = hotkey_button

	def hotkey_button(name, key, auto_size=False, text_color=gui_text_color, button_color=gui_button_color):
		return original_hotkey_button(name, key, auto_size, text_color, button_color)

	# TODO: Switch to using keys for this stuff
	toggles: list[tuple[str, str]] = [
		(tl('Speedhack'), GUIKeys.toggle_speedhack),
		(tl('Combat'), GUIKeys.toggle_combat),
		(tl('Dialogue'), GUIKeys.toggle_dialogue),
		(tl('Sigil'), GUIKeys.toggle_sigil),
		(tl('Questing'), GUIKeys.toggle_questing),
		(tl('Auto Pet', GUIKeys.toggle_auto_pet))
	]
	hotkeys: list[tuple[str, str]] = [
		(tl('Quest TP'), GUIKeys.hotkey_quest_tp),
		(tl('Freecam'), GUIKeys.toggle_freecam),
		(tl('Freecam TP'), GUIKeys.hotkey_freecam_tp)
	]
	mass_hotkeys = [
		(tl('Mass TP'), GUIKeys.mass_hotkey_mass_tp),
		(tl('XYZ Sync'), GUIKeys.mass_hotkey_xyz_sync), 
		(tl('X Press'), GUIKeys.mass_hotkey_x_press)
	]
	toggles_layout = [[hotkey_button(name, key), gui.Text(tl('Disabled'), key=f'{name}Status', auto_size_text=False, size=(7, 1), text_color=gui_text_color)] for name, key in toggles]
	framed_toggles_layout = gui.Frame(tl('Toggles'), toggles_layout, title_color=gui_text_color)
	hotkeys_layout = [[hotkey_button(name, key)] for name, key in hotkeys]
	framed_hotkeys_layout = gui.Frame(tl('Hotkeys'), hotkeys_layout, title_color=gui_text_color)
	mass_hotkeys_layout = [[hotkey_button(name, key)] for name, key in mass_hotkeys]
	framed_mass_hotkeys_layout = gui.Frame(tl('Mass Hotkeys'), mass_hotkeys_layout, title_color=gui_text_color)

	client_title = gui.Text(tl('Client') + ': ', key='Title', text_color=gui_text_color)

	# TODO: Does it make any sense to translate this? Has more occurences later in the file
	x_pos = gui.Text('x: ', key='x', auto_size_text=False, text_color=gui_text_color)
	y_pos = gui.Text('y: ', key='y', auto_size_text=False, text_color=gui_text_color)
	z_pos = gui.Text('z: ', key='z', auto_size_text=False, text_color=gui_text_color)
	yaw = gui.Text(tl('Yaw') + ': ', key='Yaw', auto_size_text=False, text_color=gui_text_color)

	zone_info = gui.Text(tl('Zone') + ': ', key='Zone', auto_size_text=False, size=(62, 1), text_color=gui_text_color)

	copy_pos = hotkey_button(tl('Copy Position'), GUIKeys.copy_position)
	copy_zone = hotkey_button(tl('Copy Zone'), GUIKeys.copy_zone)
	copy_yaw = hotkey_button(tl('Copy Rotation'), GUIKeys.copy_rotation)

	client_info_layout = [
		[client_title],
		[zone_info],
		[x_pos],
		[y_pos],
		[z_pos],
		[yaw]
	]

	utils_layout = [
		[copy_zone],
		[copy_pos],
		[copy_yaw]
	]

	framed_utils_layout = gui.Frame(tl('Utils'), utils_layout, title_color=gui_text_color)

	dev_utils_notice = tl('The utils below are for advanced users and no support will be given on them.')

	custom_tp_layout = [
		[gui.Text(dev_utils_notice, text_color=gui_text_color)],
		[
			gui.Text('X:', text_color=gui_text_color), gui.InputText(size=(6, 1), key='XInput'),
			gui.Text('Y:', text_color=gui_text_color), gui.InputText(size=(6, 1), key='YInput'),
			gui.Text('Z:', text_color=gui_text_color), gui.InputText(size=(7, 1), key='ZInput'),
			gui.Text(tl('Yaw') + ': ', text_color=gui_text_color), gui.InputText(size=(6, 1), key='YawInput'),
			hotkey_button(tl('Custom TP'), GUIKeys.button_custom_tp)
		],
		[
			gui.Text(tl('Entity Name') + ':', text_color=gui_text_color), gui.InputText(size=(36, 1), key='EntityTPInput'),
			hotkey_button(tl('Entity TP'), GUIKeys.button_entity_tp)
		]
	]

	framed_custom_tp_layout = gui.Frame(tl('TP Utils'), custom_tp_layout, title_color=gui_text_color)

	dev_utils_layout = [
		[gui.Text(dev_utils_notice, text_color=gui_text_color)],
		[
			hotkey_button(tl('Copy Entity List'), GUIKeys.copy_entity_list, True),
			hotkey_button(tl('Copy UI Tree'), GUIKeys.copy_ui_tree, True)
		],
		[
			gui.Text(tl('Zone Name') + ':', text_color=gui_text_color), gui.InputText(size=(13, 1), key='ZoneInput'),
			hotkey_button(tl('Go To Zone'), GUIKeys.button_go_to_zone),
			hotkey_button(tl('Mass Go To Zone'), GUIKeys.button_mass_go_to_zone, True)
		],
		[
			gui.Text(tl('World Name') + ':', text_color=gui_text_color),
			# TODO: Come back with some ingenius solution for this
			gui.Combo(
				['WizardCity', 'Krokotopia', 'Marleybone', 'MooShu', 'DragonSpire', 'Grizzleheim', 'Celestia', 'Wysteria', 'Zafaria', 'Avalon', 'Azteca', 'Khrysalis', 'Polaris', 'Mirage', 'Empyrea', 'Karamelle', 'Lemuria'],
				default_value='WizardCity', readonly=True,text_color=gui_text_color, size=(13, 1), key='WorldInput'
			),
			hotkey_button(tl('Go To World'), GUIKeys.button_go_to_world, True),
			hotkey_button(tl('Mass Go To World'), GUIKeys.button_mass_go_to_world, True)
		],
		[
			hotkey_button(tl('Go To Bazaar'), GUIKeys.button_go_to_bazaar, True),
			hotkey_button(tl('Mass Go To Bazaar'), GUIKeys.button_mass_go_to_bazaar, True),
			hotkey_button(tl('Refill Potions'), GUIKeys.button_refill_potions, True),
			hotkey_button(tl('Mass Refill Potions'), GUIKeys.button_mass_refill_potions, True)
		]
	]

	framed_dev_utils_layout = gui.Frame(tl('Dev Utils'), dev_utils_layout, title_color=gui_text_color)

	camera_controls_layout = [
		[gui.Text(dev_utils_notice, text_color=gui_text_color)],
		[
			gui.Text('X:', text_color=gui_text_color), gui.InputText(size=(10, 1), key='CamXInput'),
			gui.Text('Y:', text_color=gui_text_color), gui.InputText(size=(10, 1), key='CamYInput'),
			gui.Text('Z:', text_color=gui_text_color), gui.InputText(size=(10, 1), key='CamZInput'),
			hotkey_button(tl('Set Camera Position'), GUIKeys.button_set_camera_position, True)
		],
		[
			gui.Text(tl('Yaw') + ':', text_color=gui_text_color), gui.InputText(size=(10, 1), key='CamYawInput'),
			gui.Text(tl('Roll') + ':', text_color=gui_text_color), gui.InputText(size=(10, 1), key='CamRollInput'),
			gui.Text(tl('Pitch') + ':', text_color=gui_text_color), gui.InputText(size=(10, 1), key='CamPitchInput')
		],
		[
			gui.Text(tl('Entity') + ':', text_color=gui_text_color), gui.InputText(size=(18, 1), key='CamEntityInput'),
			hotkey_button(tl('Anchor'), GUIKeys.button_anchor, text_color=gui_text_color),
			hotkey_button(tl('Toggle Camera Collision'), GUIKeys.toggle_camera_collision, True)
		],
		[
			gui.Text(tl('Distance') + ':', text_color=gui_text_color), gui.InputText(size=(10, 1), key='CamDistanceInput'),
			gui.Text(tl('Min') + ':', text_color=gui_text_color), gui.InputText(size=(10, 1), key='CamMinInput'),
			gui.Text(tl('Max') + ':', text_color=gui_text_color), gui.InputText(size=(10, 1), key='CamMaxInput'),
			hotkey_button(tl('Set Distance'), GUIKeys.button_set_distance, True)
		],
		[
			hotkey_button(tl('Copy Camera Position'), GUIKeys.copy_camera_position, True),
			hotkey_button(tl('Copy Camera Rotation'), GUIKeys.copy_camera_rotation, True)
		]
	]

	framed_camera_controls_layout = gui.Frame(tl('Camera Controls'), camera_controls_layout, title_color=gui_text_color)

	# UNFINISHED - slack
	stat_viewer_layout = [
		[gui.Text(dev_utils_notice, text_color=gui_text_color)],
		[gui.Text(tl('Caster/Target Indices') + ':', text_color=gui_text_color), gui.Combo([i + 1 for i in range(12)], text_color=gui_text_color, size=(21, 1), default_value=1, key='EnemyInput', readonly=True), gui.Combo([i + 1 for i in range(12)], text_color=gui_text_color, size=(21, 1), default_value=1, key='AllyInput', readonly=True)],
		[
			gui.Text(tl('Dmg') + ':', text_color=gui_text_color), gui.InputText('', size=(7, 1), key='DamageInput'),
			gui.Text(tl('School') + ':', text_color=gui_text_color),
			# TODO: Also needs some smart solution
			gui.Combo(['Fire', 'Ice', 'Storm', 'Myth', 'Life', 'Death', 'Balance', 'Star', 'Sun', 'Moon', 'Shadow'], default_value='Fire', size=(7, 1), key='SchoolInput', readonly=True),
			gui.Text(tl('Crit') + ':', text_color=gui_text_color), gui.Checkbox(None, True, text_color=gui_text_color, key='CritStatus'),
			hotkey_button(tl('View Stats'), GUIKeys.button_view_stats, True),
			hotkey_button(tl('Copy Stats'), GUIKeys.copy_stats, True)
		],
		[gui.Multiline(tl('No client has been selected.'), key='stat_viewer', size=(66, 8), text_color=gui_text_color, horizontal_scroll=True)],
		[
			hotkey_button(tl('Swap Members'), GUIKeys.button_swap_members, True),
			gui.Text(tl('Force School Damage') + ':', text_color=gui_text_color),
			gui.Checkbox(None, text_color=gui_text_color, key='ForceSchoolStatus')
		],
	]

	framed_stat_viewer_layout = gui.Frame(tl('Stat Viewer'), stat_viewer_layout, title_color=gui_text_color)

	flythrough_layout = [
		[gui.Text(dev_utils_notice, text_color=gui_text_color)],
		[gui.Multiline(key='flythrough_creator', size=(66, 11), text_color=gui_text_color, horizontal_scroll=True)],
		[
			gui.Input(key='flythrough_file_path', visible=False), 
			gui.FileBrowse(tl('Import Flythrough'), file_types=(("Text Files", "*.txt"),), auto_size_button=True, button_color=(gui_text_color, gui_button_color)),
			gui.Input(key='flythrough_save_path', visible=False),
			gui.FileSaveAs(tl('Export Flythrough'), file_types=(("Text Files", "*.txt"),), auto_size_button=True, button_color=(gui_text_color, gui_button_color)),
			hotkey_button(tl('Execute Flythrough'), GUIKeys.button_execute_flythrough, True),
			hotkey_button(tl('Kill Flythrough'), GUIKeys.button_kill_flythrough, True)
			],
	]

	framed_flythrough_layout = gui.Frame(tl('Flythrough Creator'), flythrough_layout, title_color=gui_text_color)

	bot_creator_layout = [
		[gui.Text(dev_utils_notice, text_color=gui_text_color)],
		[gui.Multiline(key='bot_creator', size=(66, 11), text_color=gui_text_color, horizontal_scroll=True)],
		[
			gui.Input(key='bot_file_path', visible=False), 
			gui.FileBrowse('Import Bot', file_types=(("Text Files", "*.txt"),), auto_size_button=True, button_color=(gui_text_color, gui_button_color)),
			gui.Input(key='bot_save_path', visible=False),
			gui.FileSaveAs('Export Bot', file_types=(("Text Files", "*.txt"),), auto_size_button=True, button_color=(gui_text_color, gui_button_color)),
			hotkey_button(tl('Run Bot'), GUIKeys.button_run_bot, True),
			hotkey_button(tl('Kill Bot'), GUIKeys.button_kill_bot, True)
			],
	]

	framed_bot_creator_layout = gui.Frame(tl('Bot Creator'), bot_creator_layout, title_color=gui_text_color)

	misc_utils_layout = [
		[gui.Text(dev_utils_notice, text_color=gui_text_color)],
		[
			gui.Text(tl('Scale') + ':', text_color=gui_text_color), gui.InputText(size=(8, 1), key='scale'),
			hotkey_button(tl('Set Scale'), GUIKeys.button_set_scale)
		],
		[gui.Text('Select a pet world:', text_color=gui_text_color), gui.Combo(['WizardCity', 'Krokotopia', 'Marleybone', 'Mooshu', 'Dragonspyre'], default_value='WizardCity', readonly=True,text_color=gui_text_color, size=(13, 1), key='PetWorldInput')], #, hotkey_button('Set Auto Pet World', True) 
	]

	framed_misc_utils_layout = gui.Frame(tl('Misc Utils'), misc_utils_layout, title_color=gui_text_color)

	tabs = [
		[
			gui.Tab(tl('Hotkeys'), [[framed_toggles_layout, framed_hotkeys_layout, framed_mass_hotkeys_layout, framed_utils_layout]], title_color=gui_text_color),
			gui.Tab(tl('Camera'), [[framed_camera_controls_layout]], title_color=gui_text_color),
			gui.Tab(tl('Dev Utils'), [[framed_custom_tp_layout], [framed_dev_utils_layout]], title_color=gui_text_color),
			gui.Tab(tl('Stat Viewer'), [[framed_stat_viewer_layout]], title_color=gui_text_color),
			gui.Tab(tl('Flythrough'), [[framed_flythrough_layout]], title_color=gui_text_color),
			gui.Tab(tl('Bot'), [[framed_bot_creator_layout]], title_color=gui_text_color),
			gui.Tab(tl('Misc'), [[framed_misc_utils_layout]], title_color=gui_text_color)
		]
	]

	layout = [
		[gui.Text(tl('Deimos will always be a free tool. If you paid for this, you got scammed!'))],
		[gui.TabGroup(tabs)],
		[client_info_layout]
	]

	window = gui.Window(title= f'{tool_name} GUI v{tool_version}', layout= layout, keep_on_top=gui_on_top, finalize=True)
	return window


def manage_gui(send_queue: queue.Queue, recv_queue: queue.Queue, gui_theme, gui_text_color, gui_button_color, tool_name, tool_version, gui_on_top):
	window = create_gui(gui_theme, gui_text_color, gui_button_color, tool_name, tool_version, gui_on_top)

	running = True

	while running:
		event, inputs = window.read(timeout=10)
		# print(inputs)

		# Program commands
		try:
			# Eat as much as the queue gives us. We will be freed by exception
			while True:
				com = recv_queue.get_nowait()
				match com.com_type:
					case GUICommandType.Close:
						running = False

					case GUICommandType.UpdateWindow:
						window[com.data[0]].update(com.data[1])

					case GUICommandType.UpdateWindowValues:
						window[com.data[0]].update(values=com.data[1])
		except queue.Empty:
			pass

		# Window events
		match event:
			case gui.WINDOW_CLOSED:
				running = False
				send_queue.put(GUICommand(GUICommandType.Close))

			case gui.WINDOW_CLOSE_ATTEMPTED_EVENT:
				running = False
				send_queue.put(GUICommand(GUICommandType.Close))

			# Toggles
			case GUIKeys.toggle_speedhack | GUIKeys.toggle_combat | GUIKeys.toggle_dialogue | GUIKeys.toggle_sigil | \
				GUIKeys.toggle_questing | GUIKeys.toggle_auto_pet | GUIKeys.toggle_freecam | \
				GUIKeys.toggle_camera_collision: 
				send_queue.put(GUICommand(GUICommandType.ToggleOption, event))
			
			# Copying
			case GUIKeys.copy_zone | GUIKeys.copy_position | GUIKeys.copy_rotation | \
				GUIKeys.copy_entity_list | GUIKeys.copy_camera_position | \
				GUIKeys.copy_camera_rotation | GUIKeys.copy_ui_tree | GUIKeys.copy_stats:
				send_queue.put(GUICommand(GUICommandType.Copy, event))


			# Simple teleports
			case GUIKeys.hotkey_quest_tp | GUIKeys.mass_hotkey_mass_tp | GUIKeys.hotkey_freecam_tp:
				send_queue.put(GUICommand(GUICommandType.Teleport, event))


			# Custom tp
			case GUIKeys.button_custom_tp
				tp_inputs = [inputs['XInput'], inputs['YInput'], inputs['ZInput'], inputs['YawInput']]
				if any(tp_inputs):
					send_queue.put(GUICommand(GUICommandType.CustomTeleport, {
						'X': tp_inputs[0],
						'Y': tp_inputs[1],
						'Z': tp_inputs[2],
						'Yaw': tp_inputs[3],
					}))

			# Entity tp
			case GUIKeys.button_entity_tp:
				if inputs['EntityTPInput']:
					send_queue.put(GUICommand(GUICommandType.EntityTeleport, inputs['EntityTPInput']))

			# XYZ Sync
			case GUIKeys.mass_hotkey_xyz_sync:
				send_queue.put(GUICommand(GUICommandType.XYZSync))

			# X Press
			case GUIKeys.mass_hotkey_x_press:
				send_queue.put(GUICommand(GUICommandType.XPress))

			# Cam stuff
			case GUIKeys.button_anchor:
				send_queue.put(GUICommand(GUICommandType.AnchorCam, inputs['CamEntityInput']))

			case GUIKeys.button_set_camera_position:
				camera_inputs = [inputs['CamXInput'], inputs['CamYInput'], inputs['CamZInput'], inputs['CamYawInput'], inputs['CamRollInput'], inputs['CamPitchInput']]
				if any(camera_inputs):
					send_queue.put(GUICommand(GUICommandType.SetCamPosition, {
						'X': camera_inputs[0],
						'Y': camera_inputs[1],
						'Z': camera_inputs[2],
						'Yaw': camera_inputs[3],
						'Roll': camera_inputs[4],
						'Pitch': camera_inputs[5],
					}))

			case GUIKeys.button_set_distance:
				distance_inputs = [inputs['CamDistanceInput'], inputs['CamMinInput'], inputs['CamMaxInput']]
				if any(distance_inputs):
					send_queue.put(GUICommand(GUICommandType.SetCamDistance, {
						"Distance": distance_inputs[0],
						"Min": distance_inputs[1],
						"Max": distance_inputs[2],
					}))

			# Gotos
			case GUIKeys.button_go_to_zone:
				if inputs['ZoneInput']:
					send_queue.put(GUICommand(GUICommandType.GoToZone, (False, str(inputs['ZoneInput']))))

			case GUIKeys.button_mass_go_to_zone:
				if inputs['ZoneInput']:
					send_queue.put(GUICommand(GUICommandType.GoToZone, (True, str(inputs['ZoneInput']))))

			case GUIKeys.button_go_to_world:
				if inputs['WorldInput']:
					send_queue.put(GUICommand(GUICommandType.GoToWorld, (False, inputs['WorldInput'])))

			case GUIKeys.button_mass_go_to_world:
				if inputs['WorldInput']:
					send_queue.put(GUICommand(GUICommandType.GoToWorld, (True, inputs['WorldInput'])))

			case GUIKeys.button_go_to_bazaar:
				send_queue.put(GUICommand(GUICommandType.GoToBazaar, False))

			case GUIKeys.button_mass_go_to_bazaar:
				send_queue.put(GUICommand(GUICommandType.GoToBazaar, True))

			case GUIKeys.button_refill_potions:
				send_queue.put(GUICommand(GUICommandType.RefillPotions, False))

			case GUIKeys.button_mass_refill_potions:
				send_queue.put(GUICommand(GUICommandType.RefillPotions, True))

			case GUIKeys.button_execute_flythrough:
				send_queue.put(GUICommand(GUICommandType.ExecuteFlythrough, inputs['flythrough_creator']))

			case GUIKeys.button_kill_flythrough:
				send_queue.put(GUICommand(GUICommandType.KillFlythrough))

			case GUIKeys.button_run_bot:
				send_queue.put(GUICommand(GUICommandType.ExecuteBot, inputs['bot_creator']))

			case GUIKeys.button_kill_bot:
				send_queue.put(GUICommand(GUICommandType.KillBot))

			case GUIKeys.button_set_scale:
				send_queue.put(GUICommand(GUICommandType.SetScale, inputs['scale']))

			case GUIKeys.button_view_stats:
				enemy_index = re.sub(r'[^0-9]', '', str(inputs['EnemyInput']))
				ally_index = re.sub(r'[^0-9]', '', str(inputs['AllyInput']))
				base_damage = re.sub(r'[^0-9]', '', str(inputs['DamageInput']))
				school_id: int = school_id_to_names[inputs['SchoolInput']]
				send_queue.put(GUICommand(GUICommandType.SelectEnemy, (int(enemy_index), int(ally_index), base_damage, school_id, inputs['CritStatus'], inputs['ForceSchoolStatus'])))

			case GUIKeys.button_swap_members:
				enemy_input = inputs['EnemyInput']
				ally_input = inputs['AllyInput']
				window['EnemyInput'].update(ally_input)
				window['AllyInput'].update(enemy_input)

			# case 'Set Auto Pet World':
			# 	if inputs['PetWorldInput']:
			# 		send_queue.put(GUICommand(GUICommandType.SetPetWorld, (False, str(inputs['PetWorldInput']))))

			# Other
			case _:
				pass

		#Updates pet world when it changes, without the need for a button press -slack
		if inputs and inputs['PetWorldInput'] != wizard_city_dance_game_path[-1]:
			assign_pet_level(inputs['PetWorldInput'])

		def import_check(input_window_str: str, output_window_str: str):
			if inputs and inputs[input_window_str]:
				with open(inputs[input_window_str]) as file:
					file_data = file.readlines()
					file_str = ''.join(file_data)
					window[output_window_str].update(file_str)
					window[input_window_str].update('')
					file.close()

		def export_check(path_window_str: str, content_window_str: str):
			if inputs and inputs[path_window_str]:
				file = open(inputs[path_window_str], 'w')
				file.write(inputs[content_window_str])
				file.close()
				window[path_window_str].update('')

		import_check('flythrough_file_path', 'flythrough_creator')
		export_check('flythrough_save_path', 'flythrough_creator')

		import_check('bot_file_path', 'bot_creator')
		export_check('bot_save_path', 'bot_creator')

	window.close()
