from enum import Enum, auto
import queue
import re
import PySimpleGUI as gui


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

	SetScale = auto()

	# deimos -> window
	UpdateWindow = auto()



class GUICommand:
	def __init__(self, com_type: GUICommandType, data=None):
		self.com_type = com_type
		self.data = data


def hotkey_button(name: str, auto_size: bool, text_color: str, button_color: str):
	return gui.Button(name, button_color=(text_color, button_color), auto_size_button=auto_size)


def create_gui(gui_theme, gui_text_color, gui_button_color, tool_name, tool_version, gui_on_top):
	gui.theme(gui_theme)

	gui.popup('Deimos will always be free and open-source.\nBy using Deimos, you agree to the GPL v3 license agreement.\nIf you bought this, you got scammed!', title='License Agreement', keep_on_top=True, text_color=gui_text_color, button_color=(gui_text_color, gui_button_color))

	global hotkey_button
	original_hotkey_button = hotkey_button

	def hotkey_button(name, auto_size=False, text_color=gui_text_color, button_color=gui_button_color):
		return original_hotkey_button(name, auto_size, text_color, button_color)

	toggles = ['Speedhack', 'Combat', 'Dialogue', 'Sigil', 'Questing', 'Auto Pet']
	hotkeys = ['Quest TP', 'Freecam', 'Freecam TP']
	mass_hotkeys = ['Mass TP', 'XYZ Sync', 'X Press']
	toggles_layout = [[hotkey_button(name), gui.Text(f'Disabled', key=f'{name}Status', auto_size_text=False, size=(7, 1), text_color=gui_text_color)] for name in toggles]
	framed_toggles_layout = gui.Frame('Toggles', toggles_layout, title_color=gui_text_color)
	hotkeys_layout = [[hotkey_button(name)] for name in hotkeys]
	framed_hotkeys_layout = gui.Frame('Hotkeys', hotkeys_layout, title_color=gui_text_color)
	mass_hotkeys_layout = [[hotkey_button(name)] for name in mass_hotkeys]
	framed_mass_hotkeys_layout = gui.Frame('Mass Hotkeys', mass_hotkeys_layout, title_color=gui_text_color)

	client_title = gui.Text('Client: ', key='Title', text_color=gui_text_color)

	x_pos = gui.Text('x: ', key='x', auto_size_text=False, text_color=gui_text_color)
	y_pos = gui.Text('y: ', key='y', auto_size_text=False, text_color=gui_text_color)
	z_pos = gui.Text('z: ', key='z', auto_size_text=False, text_color=gui_text_color)
	yaw = gui.Text('Yaw: ', key='Yaw', auto_size_text=False, text_color=gui_text_color)

	zone_info = gui.Text('Zone: ', key='Zone', auto_size_text=False, size=(62, 1), text_color=gui_text_color)

	copy_pos = hotkey_button('Copy Position')
	copy_zone = hotkey_button('Copy Zone')
	copy_yaw = hotkey_button('Copy Rotation')

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

	framed_utils_layout = gui.Frame('Utils', utils_layout, title_color=gui_text_color)

	custom_tp_layout = [
		[gui.Text('The utils shown below are for advanced users and no support will be provided on them.', text_color=gui_text_color)],
		[gui.Text('X:', text_color=gui_text_color), gui.InputText(size=(8, 1), key='XInput'), gui.Text('Y:', text_color=gui_text_color), gui.InputText(size=(8, 1), key='YInput'), gui.Text('Z:', text_color=gui_text_color), gui.InputText(size=(8, 1), key='ZInput'), gui.Text('Yaw: ', text_color=gui_text_color), gui.InputText(size=(8, 1), key='YawInput'), hotkey_button('Custom TP')],
		[gui.Text('Entity Name:', text_color=gui_text_color), gui.InputText(size=(43, 1), key='EntityTPInput'), hotkey_button('Entity TP')]
	]

	framed_custom_tp_layout = gui.Frame('TP Utils', custom_tp_layout, title_color=gui_text_color)

	dev_utils_layout = [
		[gui.Text('The utils shown below are for advanced users and no support will be provided on them.', text_color=gui_text_color)],
		[hotkey_button('Copy Entity List', True), hotkey_button('Copy Camera Position', True), hotkey_button('Copy Camera Rotation', True), hotkey_button('Copy UI Tree', True)],
		[gui.Text('Zone Name:', text_color=gui_text_color), gui.InputText(size=(29, 1), key='ZoneInput'), hotkey_button('Go To Zone'), hotkey_button('Mass Go To Zone', True)],
		[gui.Text('World Name:', text_color=gui_text_color), gui.Combo(['WizardCity', 'Krokotopia', 'Marleybone', 'MooShu', 'DragonSpire', 'Grizzleheim', 'Celestia', 'Wysteria', 'Zafaria', 'Avalon', 'Azteca', 'Khrysalis', 'Polaris', 'Mirage', 'Empyrea', 'Karamelle', 'Lemuria'], text_color=gui_text_color, size=(27, 1), key='WorldInput'), hotkey_button('Go To World', True), hotkey_button('Mass Go To World', True)],
		[hotkey_button('Go To Bazaar', True), hotkey_button('Mass Go To Bazaar', True), hotkey_button('Refill Potions', True), hotkey_button('Mass Refill Potions', True)]
	]

	framed_dev_utils_layout = gui.Frame('Dev Utils', dev_utils_layout, title_color=gui_text_color)

	camera_controls_layout = [
		[gui.Text('The utils shown below are for advanced users and no support will be provided on them.', text_color=gui_text_color)],
		[gui.Text('X:', text_color=gui_text_color), gui.InputText(size=(12, 1), key='CamXInput'), gui.Text('Y:', text_color=gui_text_color), gui.InputText(size=(12, 1), key='CamYInput'), gui.Text('Z:', text_color=gui_text_color), gui.InputText(size=(11, 1), key='CamZInput'), hotkey_button('Set Camera Position', True)],
		[gui.Text('Yaw:', text_color=gui_text_color), gui.InputText(size=(16, 1), key='CamYawInput'), gui.Text('Roll:', text_color=gui_text_color), gui.InputText(size=(16, 1), key='CamRollInput'), gui.Text('Pitch:', text_color=gui_text_color), gui.InputText(size=(15, 1), key='CamPitchInput')],
		[gui.Text('Entity:', text_color=gui_text_color), gui.InputText(size=(25, 1), key='CamEntityInput'), hotkey_button('Anchor', text_color=gui_text_color), hotkey_button('Toggle Camera Collision', True)],
		[gui.Text('Distance:', text_color=gui_text_color), gui.InputText(size=(10, 1), key='CamDistanceInput'), gui.Text('Min:', text_color=gui_text_color), gui.InputText(size=(10, 1), key='CamMinInput'), gui.Text('Max:', text_color=gui_text_color), gui.InputText(size=(11, 1), key='CamMaxInput'), hotkey_button('Set Distance', True)]
	]

	framed_camera_controls_layout = gui.Frame('Camera Controls', camera_controls_layout, title_color=gui_text_color)

	# UNFINISHED - slack
	stat_viewer_layout = [
		[gui.Text('The utils shown below are for advanced users and no support will be provided on them.', text_color=gui_text_color)],
		# [hotkey_button('Enemy 1'), hotkey_button('Enemy 2'), hotkey_button('Enemy 3'), hotkey_button('Enemy 4')],
		# [hotkey_button('Enemy 5'), hotkey_button('Enemy 6'), hotkey_button('Enemy 7'), hotkey_button('Enemy 8')],
		[gui.Text('Enemy Index:', text_color=gui_text_color), gui.Combo([1, 2, 3, 4, 5, 6, 7, 8], text_color=gui_text_color, size=(3, 1), default_value=1, key='EnemyInput'), hotkey_button('View Stats'), hotkey_button('Copy Enemy Stats', True)],
		[gui.Multiline('No client has been selected.', key='stat_viewer', size=(66, 9), text_color=gui_text_color, horizontal_scroll=True)],
		[gui.Text('Note that the stat viewer does not work in PvP.', text_color=gui_text_color)]
		]

	framed_stat_viewer_layout = gui.Frame('Stat Viewer', stat_viewer_layout, title_color=gui_text_color)

	flythrough_layout = [
		[gui.Text('The utils shown below are for advanced users and no support will be provided on them.', text_color=gui_text_color)],
		[gui.Multiline(key='flythrough_creator', size=(66, 11), text_color=gui_text_color, horizontal_scroll=True)],
		[
			gui.Input(key='flythrough_file_path', visible=False), 
			gui.FileBrowse('Import Flythrough', file_types=(("Text Files", "*.txt"),), auto_size_button=True, button_color=(gui_text_color, gui_button_color)),
			gui.Input(key='flythrough_save_path', visible=False),
			gui.FileSaveAs('Export Flythrough', file_types=(("Text Files", "*.txt"),), auto_size_button=True, button_color=(gui_text_color, gui_button_color)),
			hotkey_button('Execute Flythrough', True),
			hotkey_button('Kill Flythrough', True)
			],
	]

	framed_flythrough_layout = gui.Frame('Flythrough Creator', flythrough_layout, title_color=gui_text_color)

	bot_creator_layout = [
		[gui.Text('The utils shown below are for advanced users and no support will be provided on them.', text_color=gui_text_color)],
		[gui.Multiline(key='bot_creator', size=(66, 11), text_color=gui_text_color, horizontal_scroll=True)],
		[
			gui.Input(key='bot_file_path', visible=False), 
			gui.FileBrowse('Import Bot', file_types=(("Text Files", "*.txt"),), auto_size_button=True, button_color=(gui_text_color, gui_button_color)),
			gui.Input(key='bot_save_path', visible=False),
			gui.FileSaveAs('Export Bot', file_types=(("Text Files", "*.txt"),), auto_size_button=True, button_color=(gui_text_color, gui_button_color)),
			hotkey_button('Run Bot', True),
			hotkey_button('Kill Bot', True)
			],
	]

	framed_bot_creator_layout = gui.Frame('Bot Creator', bot_creator_layout, title_color=gui_text_color)

	misc_utils_layout = [
		[gui.Text('The utils shown below are for advanced users and no support will be provided on them.', text_color=gui_text_color)],
		[gui.Text('Scale:', text_color=gui_text_color), gui.InputText(size=(8, 1), key='scale'), hotkey_button('Set Scale')],
	]

	framed_misc_utils_layout = gui.Frame('Misc Utils', misc_utils_layout, title_color=gui_text_color)

	tabs = [
		[
			gui.Tab('Hotkeys', [[framed_toggles_layout, framed_hotkeys_layout, framed_mass_hotkeys_layout, framed_utils_layout]], title_color=gui_text_color),
			gui.Tab('Camera', [[framed_camera_controls_layout]], title_color=gui_text_color),
			gui.Tab('Dev Utils', [[framed_custom_tp_layout], [framed_dev_utils_layout]], title_color=gui_text_color),
			gui.Tab('Stat Viewer', [[framed_stat_viewer_layout]], title_color=gui_text_color),
			gui.Tab('Flythrough', [[framed_flythrough_layout]], title_color=gui_text_color),
			gui.Tab('Bot Creator', [[framed_bot_creator_layout]], title_color=gui_text_color),
			gui.Tab('Misc', [[framed_misc_utils_layout]], title_color=gui_text_color)
		]
	]

	layout = [
		[gui.Text('Deimos will always be a free tool. If you paid for this, you got scammed!')],
		[gui.TabGroup(tabs)],
		[client_info_layout]
	]

	window = gui.Window(title= f'{tool_name} GUI v{tool_version}', layout= layout, keep_on_top=gui_on_top, finalize=True)
	return window


def manage_gui(send_queue: queue.Queue, recv_queue: queue.Queue, gui_theme, gui_text_color, gui_button_color, tool_name, tool_version, gui_on_top):
	window = create_gui(gui_theme, gui_text_color, gui_button_color, tool_name, tool_version, gui_on_top)

	running = True

	enemy_ids = []

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
			case 'Speedhack' | 'Combat' | 'Dialogue' | 'Sigil' | 'Questing' | 'Auto Pet' | 'Freecam' | \
						'Toggle Camera Collision':
				send_queue.put(GUICommand(GUICommandType.ToggleOption, event.replace('Toggle', '').strip()))

			# Copying
			case 'Copy Zone' | 'Copy Position' | 'Copy Rotation' | 'Copy Entity List' | \
						'Copy Camera Position' | 'Copy Camera Rotation' | 'Copy UI Tree' | \
						'Copy Enemy Stats':
				send_queue.put(GUICommand(GUICommandType.Copy, event.replace('Copy', '').strip()))
			
			# Simple teleports
			case 'Quest TP' | 'Mass TP' | 'Freecam TP':
				send_queue.put(GUICommand(GUICommandType.Teleport, event.replace('TP', '').strip()))

			# Custom tp
			case 'Custom TP':
				tp_inputs = [inputs['XInput'], inputs['YInput'], inputs['ZInput'], inputs['YawInput']]
				if any(tp_inputs):
					send_queue.put(GUICommand(GUICommandType.CustomTeleport, {
						'X': tp_inputs[0],
						'Y': tp_inputs[1],
						'Z': tp_inputs[2],
						'Yaw': tp_inputs[3],
					}))

			# Entity tp
			case 'Entity TP':
				if inputs['EntityTPInput']:
					send_queue.put(GUICommand(GUICommandType.EntityTeleport, inputs[14]))

			# XYZ Sync
			case 'XYZ Sync':
				send_queue.put(GUICommand(GUICommandType.XYZSync))

			# X Press
			case 'X Press':
				send_queue.put(GUICommand(GUICommandType.XPress))

			# Cam stuff
			case 'Anchor':
				send_queue.put(GUICommand(GUICommandType.AnchorCam, inputs['CamEntityInput']))

			case 'Set Camera Position':
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

			case 'Set Distance':
				distance_inputs = [inputs['CamDistanceInput'], inputs['CamMinInput'], inputs['CamMaxInput']]
				if any(distance_inputs):
					send_queue.put(GUICommand(GUICommandType.SetCamDistance, {
						"Distance": distance_inputs[0],
						"Min": distance_inputs[1],
						"Max": distance_inputs[2],
					}))

			# Gotos
			case 'Go To Zone':
				if inputs['ZoneInput']:
					send_queue.put(GUICommand(GUICommandType.GoToZone, (False, str(inputs['ZoneInput']))))

			case 'Mass Go To Zone':
				if inputs['ZoneInput']:
					send_queue.put(GUICommand(GUICommandType.GoToZone, (True, str(inputs['ZoneInput']))))

			case 'Go To World':
				if inputs['WorldInput']:
					send_queue.put(GUICommand(GUICommandType.GoToWorld, (False, inputs['WorldInput'])))

			case 'Mass Go To World':
				if inputs['WorldInput']:
					send_queue.put(GUICommand(GUICommandType.GoToWorld, (True, inputs['WorldInput'])))

			case 'Go To Bazaar':
				send_queue.put(GUICommand(GUICommandType.GoToBazaar, False))

			case 'Mass Go To Bazaar':
				send_queue.put(GUICommand(GUICommandType.GoToBazaar, True))

			case 'Refill Potions':
				send_queue.put(GUICommand(GUICommandType.RefillPotions, False))

			case 'Mass Refill Potions':
				send_queue.put(GUICommand(GUICommandType.RefillPotions, True))

			case 'Execute Flythrough':
				send_queue.put(GUICommand(GUICommandType.ExecuteFlythrough, inputs['flythrough_creator']))

			case 'Kill Flythrough':
				send_queue.put(GUICommand(GUICommandType.KillFlythrough))

			case 'Run Bot':
				send_queue.put(GUICommand(GUICommandType.ExecuteBot, inputs['bot_creator']))

			case 'Kill Bot':
				send_queue.put(GUICommand(GUICommandType.KillBot))

			case 'Set Scale':
				send_queue.put(GUICommand(GUICommandType.SetScale, inputs['scale']))

			case 'View Stats':
				enemy_index = re.sub(r'[^0-9]', '', str(inputs['EnemyInput']))
				send_queue.put(GUICommand(GUICommandType.SelectEnemy, int(enemy_index)))

			# Other
			case _:
				pass

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
