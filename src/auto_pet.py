import asyncio
import traceback
from asyncio import CancelledError

from loguru import logger
from pymem.exception import MemoryReadError
from wizwalker import HookAlreadyActivated, HookNotActive, HookNotReady, Client, Keycode, XYZ
from wizwalker.memory import HookHandler, SimpleHook

from src.paths import *
from src.teleport_math import navmap_tp_leader_quest
from src.utils import navigate_to_ravenwood, click_window_by_path, is_visible_by_path, navigate_to_commons_from_ravenwood, post_keys, get_window_from_path, safe_wait_for_zone_change, LoadingScreenNotFound, FriendBusyOrInstanceClosed, get_popup_title, attempt_activate_mouseless, attempt_deactivate_mouseless

_dance_moves_transtable = str.maketrans("abcd", "WDSA")


# Thanks to peechez for this class
class DanceGameMovesHook(SimpleHook):
    pattern = rb"\x48\x8B\xF8\x48\x39\x70\x10"
    instruction_length = 7
    exports = [("dance_game_moves", 8)]
    noops = 2

    async def bytecode_generator(self, packed_exports):
        return (
                b"\x48\x8B\xF8"
                b"\x48\x8B\x00"
                b"\x48\xA3" + packed_exports[0][1] +
                b"\x48\x8B\xC7"
                b"\x48\x39\x70\x10"
        )



async def activate_dance_game_moves_hook(
        self, *, wait_for_ready: bool = False, timeout: float = None
):
    if self._check_if_hook_active(DanceGameMovesHook):
        raise HookAlreadyActivated("DanceGameMovesHook")

    await self._check_for_autobot()

    hook = DanceGameMovesHook(self)
    await hook.hook()

    self._active_hooks.append(hook)
    self._base_addrs["dance_game_moves"] = hook.dance_game_moves

    if wait_for_ready:
        await self._wait_for_value(hook.dance_game_moves, timeout)


HookHandler.activate_dance_game_moves_hook = activate_dance_game_moves_hook


async def deactivate_dance_game_moves_hook(self):
    if not self._check_if_hook_active(DanceGameMovesHook):
        raise HookNotActive("DanceGameMovesHook")

    hook = self._get_hook_by_type(DanceGameMovesHook)
    self._active_hooks.remove(hook)
    await hook.unhook()

    del self._base_addrs["dance_game_moves"]


HookHandler.deactivate_dance_game_moves_hook = deactivate_dance_game_moves_hook

async def attempt_activate_dance_hook(client: Client, sleep_time: float = 0.1):
    # Attempts to activate dance hook, in a try block in case it's already off for this client
    if not client.dance_hook_status:
        try:
            await client.hook_handler.activate_dance_game_moves_hook()
        except:
            pass

        client.dance_hook_status = True
    await asyncio.sleep(sleep_time)

async def attempt_deactivate_dance_hook(client: Client, sleep_time: float = 0.1):
    # Attempts to deactivate dance hook, in a try block in case it's already off for this client
    if client.dance_hook_status:
        try:
            await client.hook_handler.deactivate_dance_game_moves_hook()
        except:
            pass

        client.dance_hook_status = False
    await asyncio.sleep(sleep_time)


async def read_current_dance_game_moves(self) -> str:
    try:
        addr = self._base_addrs["dance_game_moves"]
    except KeyError:
        raise HookNotActive("DanceGameMovesHook")

    try:
        moves = await self.read_bytes(addr, 8)
    except MemoryReadError:
        raise HookNotReady("DanceGameMovesHook")
    return moves.partition(b"\0")[0].decode().translate(_dance_moves_transtable)


HookHandler.read_current_dance_game_moves = read_current_dance_game_moves



async def navigate_to_pavilion_from_commons(cl: Client):
    # Teleport to pet pavilion door
    pavilion_XYZ = XYZ(8426.3779296875, -2165.6982421875, -27.913818359375)
    await navmap_tp_leader_quest(cl, pavilion_XYZ)
    await cl.wait_for_zone_change(name='WizardCity/WC_Hub')
    await asyncio.sleep(2.0)


async def navigate_to_dance_game(cl: Client):
    # Walk forward, to Milo Barker
    await cl.goto(x=-1738.7811279296875, y=-387.345458984375)
    # Walk in front of pet game
    await cl.goto(x=-4090.10888671875, y=-1186.3660888671875)
    # Walk onto sigil
    await cl.goto(x=-4449.36669921875, y=-992.9967651367188)


async def nomnom(client: Client, ignore_pet_level_up: bool, only_play_dance_game: bool):
    finished_feeding = False
    dance_hook_activated = False
    mouseless_active = False

    while not finished_feeding:
        popup_title = await get_popup_title(client)
        while not popup_title == 'Dance Game':
            await asyncio.sleep(.125)
            popup_title = await get_popup_title(client)

        # wait for dance game popup, and click until the popup goes away and the pet window opens
        while not await is_visible_by_path(client, pet_feed_window_visible_path):
            while popup_title == 'Dance Game':
                await client.send_key(Keycode.X, 0.1)
                popup_title = await get_popup_title(client)
                await asyncio.sleep(.125)
            popup_title = await get_popup_title(client)
            await asyncio.sleep(.125)

        if not mouseless_active:
            mouseless_active = True
            await attempt_activate_mouseless(client)
        # click until feeder opens
        # while await client.is_in_npc_range():
        #     await client.send_key(Keycode.X, 0.1)
        #     await asyncio.sleep(.2)

        # wait for pet window to open
        # while not await is_visible_by_path(client, pet_feed_window_visible_path):
        #     await asyncio.sleep(.1)

        energy_cost_txt = await get_window_from_path(client.root_window, pet_feed_window_energy_cost_textbox_path)
        total_energy_txt = await get_window_from_path(client.root_window, pet_feed_window_your_energy_textbox_path)

        energy_cost = await energy_cost_txt.maybe_text()
        total_energy = await total_energy_txt.maybe_text()

        energy_cost = energy_cost[8:]
        total_energy = total_energy[8:]
        total_energy = total_energy.split('/', 1)[0]
        energy_cost = int(energy_cost)
        total_energy = int(total_energy)

        # if player has enough energy to play the game
        if total_energy >= energy_cost:
            # if the config forces us to play the dance game or we are unable to skip games yet - and the hook is not already active - activate the hook
            if (only_play_dance_game or not await is_visible_by_path(client, skip_pet_game_button_path)) and not dance_hook_activated:
                logger.debug('Client ' + client.title + ': Activating dance game hook.')
                # dance hook seems to need time to activate fully - without a sleep, it will miss turns in the game
                await attempt_activate_dance_hook(client, sleep_time=5.0)
                dance_hook_activated = True


            # skip game if it is an option and the user's config for always playing the game is off
            if await is_visible_by_path(client, skip_pet_game_button_path) and not only_play_dance_game:
                # click skip game button until window changes
                while await is_visible_by_path(client, pet_feed_window_visible_path):
                    if await is_visible_by_path(client, skip_pet_game_button_path):
                        await click_window_by_path(client, skip_pet_game_button_path)
                        await asyncio.sleep(.2)

                # wait for reward window to show up
                while not await is_visible_by_path(client, skipped_pet_game_rewards_window_path):
                    await asyncio.sleep(.1)

                # click 'Next' button
                if await is_visible_by_path(client, skipped_pet_game_continue_and_feed_button_path):
                    await click_window_by_path(client, skipped_pet_game_continue_and_feed_button_path)
                    await asyncio.sleep(.5)

                # click first snack
                if await is_visible_by_path(client, skipped_first_pet_snack_path):
                    await click_window_by_path(client, skipped_first_pet_snack_path)
                    await asyncio.sleep(.2)

                    # Click 'Feed Pet'
                    if await is_visible_by_path(client, skipped_pet_game_continue_and_feed_button_path):
                        await click_window_by_path(client, skipped_pet_game_continue_and_feed_button_path)
                        await asyncio.sleep(1.0)

                        # Handle what happens when the pet levels up
                        # if user has ignore_pet_level_up = True, exit out of the level up screen and continue questing
                        # otherwise, leave it up and force user to close it themselves
                        if await is_visible_by_path(client, skipped_pet_leveled_up_window_path):
                            if not ignore_pet_level_up:
                                if mouseless_active:
                                    mouseless_active = False
                                    await attempt_deactivate_mouseless(client)
                                logger.info('Auto Pet - Client ' + client.title + '\'s pet leveled uclient.  Please close the window to continue, or exit Deimos if you wish to stop questing.')
                                logger.info('These pauses can be disabled in the config file by setting ignore_pet_level_up = True')

                                # wait for the user to realize their pet leveled up and wait for them to manually close the window
                                while await is_visible_by_path(client, skipped_pet_leveled_up_window_path):
                                    await asyncio.sleep(1.0)

                                if not mouseless_active:
                                    mouseless_active = True
                                    await attempt_activate_mouseless(client)
                            else:
                                # while pet leveled up window is open, continually click exit button
                                while await is_visible_by_path(client, skipped_pet_leveled_up_window_path):
                                    if await is_visible_by_path(client, exit_skipped_pet_leveled_up_path):
                                        await click_window_by_path(client, exit_skipped_pet_leveled_up_path)
                                        await asyncio.sleep(.2)

                        # wait for final screen
                        while not await is_visible_by_path(client, skipped_finish_pet_button):
                            await asyncio.sleep(.1)

                        # click 'Finish' button to exit all the way out
                        while await is_visible_by_path(client, skipped_finish_pet_button):
                            await click_window_by_path(client, skipped_finish_pet_button)
                            await asyncio.sleep(.2)

                        # wait for reward screen to close
                        while await is_visible_by_path(client, skipped_pet_game_rewards_window_path):
                            await asyncio.sleep(.1)
                else:
                    logger.info('Auto Pet - Client ' + client.title + ' is out of snacks.')
                    finished_feeding = True

                await asyncio.sleep(.5)
            # play dance game since the user has not unlocked skip game yet (or if config is set to always play)
            # thanks to Peechez for the actual dance game playing code
            else:
                # wait for pet game selection window to appear
                while await is_visible_by_path(client, pet_feed_window_visible_path):
                    # click wizard city game
                    if await is_visible_by_path(client, wizard_city_dance_game_path):
                        await click_window_by_path(client, wizard_city_dance_game_path)
                        await asyncio.sleep(.2)

                    # click play
                    if await is_visible_by_path(client, play_dance_game_button_path):
                        await click_window_by_path(client, play_dance_game_button_path)
                        await asyncio.sleep(.1)

                # automatic success method
                # play the dance game and win it
                await dancedance(client)

                # automatic failure method
                # while not await is_visible_by_path(client, won_pet_game_rewards_window_path):
                #     await client.send_key(Keycode.D)
                #     await asyncio.sleep(.2)

                # if we leveled up from the small amount of XP the pet game gave us, account for it
                if await is_visible_by_path(client, won_pet_leveled_up_window_path):
                    await won_game_leveled_up(client, won_pet_leveled_up_window_path)
                # else:
                # click 'Next'
                if await is_visible_by_path(client, won_pet_game_continue_and_feed_button_path):
                    await click_window_by_path(client, won_pet_game_continue_and_feed_button_path)
                    await asyncio.sleep(.5)

                # click first snack
                if await is_visible_by_path(client, won_first_pet_snack_path):
                    await click_window_by_path(client, won_first_pet_snack_path)
                    await asyncio.sleep(.2)

                    # Click 'Feed Pet'
                    if await is_visible_by_path(client, won_pet_game_continue_and_feed_button_path):
                        # Handle what happens when the pet levels up
                        # if user has ignore_pet_level_up = True, exit out of the level up screen and continue questing
                        # otherwise, leave it up and force user to close it themselves
                        await won_game_leveled_up(client, ignore_pet_level_up)

                        # wait for reward screen
                        while not await is_visible_by_path(client, won_finish_pet_button):
                            await asyncio.sleep(.1)

                        # click 'Finish'
                        while await is_visible_by_path(client, won_finish_pet_button):
                            await click_window_by_path(client, won_finish_pet_button)
                            await asyncio.sleep(.2)

                        # wait for reward screen to close
                        while await is_visible_by_path(client, won_pet_game_rewards_window_path):
                            await asyncio.sleep(.1)
                else:
                    logger.info('Auto Pet - Client ' + client.title + ' is out of snacks.')
                    finished_feeding = True

                await asyncio.sleep(.5)
        else:
            logger.info('Auto Pet - Client ' + client.title + ' is out of energy.')
            finished_feeding = True

    # feed window may still be open, close it
    while await is_visible_by_path(client, pet_feed_window_visible_path):
        if await is_visible_by_path(client, pet_feed_window_cancel_button_path):
            await click_window_by_path(client, pet_feed_window_cancel_button_path)
            await asyncio.sleep(.2)


    if mouseless_active:
        await attempt_deactivate_mouseless(client)

    if dance_hook_activated:
        logger.debug('Client ' + client.title + ': Deactivating dance game hook.')
        await attempt_deactivate_dance_hook(client)

    # home button can in rare cases be greyed out after auto_buy - wait some time to make sure that clients don't get stuck if other code tries to send them home
    await asyncio.sleep(6.5)


# Thanks to Peechez for this code from wizdancer
async def dancedance(client: Client):
    # wait for the dance game text box to appear
    while not await is_visible_by_path(client, dance_game_action_textbox_path):
        await asyncio.sleep(.1)

    action_window = await get_window_from_path(client.root_window, dance_game_action_textbox_path)

    for _ in range(5):
        while await action_window.maybe_text() == "<center>Go!":
            await asyncio.sleep(0.125)
        while await action_window.maybe_text() != "<center>Go!":
            await asyncio.sleep(0.125)

        await asyncio.sleep(1.5)
        await post_keys(client, await client.hook_handler.read_current_dance_game_moves())
    await asyncio.sleep(3)


async def won_game_leveled_up(client: Client, auto_pet_ignore_pet_level_up):
    await click_window_by_path(client, won_pet_game_continue_and_feed_button_path)
    await asyncio.sleep(1.0)
    if await is_visible_by_path(client, won_pet_leveled_up_window_path):
        if not auto_pet_ignore_pet_level_up:
            await client.mouse_handler.deactivate_mouseless()
            logger.info('Auto Pet - Client ' + client.title + '\'s pet leveled up.  Please close the window to continue, or exit Deimos if you wish to stop questing.')
            logger.info('These pauses can be disabled in the config file by setting auto_pet_ignore_pet_level_up = True')

            # wait for the user to realize their pet leveled up and wait for them to manually close the window
            while await is_visible_by_path(client, won_pet_leveled_up_window_path):
                await asyncio.sleep(1.0)

            await client.mouse_handler.activate_mouseless()
        else:
            # while pet leveled up window is open, continually click exit button
            while await is_visible_by_path(client, won_pet_leveled_up_window_path):
                if await is_visible_by_path(client, exit_won_pet_leveled_up_path):
                    await click_window_by_path(client, exit_won_pet_leveled_up_path)
                    await asyncio.sleep(.2)


async def auto_pet(client: Client, ignore_pet_level_up: bool, only_play_dance_game: bool, questing: bool = False):
    started_at_pavilion = False
    if await client.zone_name() != 'WizardCity/WC_Streets/Interiors/WC_PET_Park':
        await client.send_key(Keycode.PAGE_DOWN, 0.1)
        await asyncio.sleep(.5)
        # Navigate to ravenwood
        await navigate_to_ravenwood(client)
        # Navigate to commons from ravenwood
        await navigate_to_commons_from_ravenwood(client)
        # Navigate to pet pavilion from commons
        await navigate_to_pavilion_from_commons(client)
        # Navigate to sigil
        await navigate_to_dance_game(client)
    else:
        started_at_pavilion = True
        try:
            await client.teleport(XYZ(x=-4450.57958984375, y=-994.8973388671875, z=-8.041412353515625))
        except ValueError:
            await asyncio.sleep(3.0)
            await client.teleport(XYZ(x=-4450.57958984375, y=-994.8973388671875, z=-8.041412353515625))

        # for i in range(3):
        #     await client.send_key(Keycode.END, 0.1)
        #
        # try:
        #     await safe_wait_for_zone_change(client, name='WizardCity/WC_Streets/Interiors/WC_PET_Park')
        # # commons button was probably on cooldown.  wait and try again
        # except LoadingScreenNotFound:
        #     logger.debug('Failed to return to commons - sleeping and trying again.')
        #     await asyncio.sleep(30.0)
        #     for i in range(3):
        #         await client.send_key(Keycode.END, 0.1)
        #
        #     await client.wait_for_zone_change(name='WizardCity/WC_Streets/Interiors/WC_PET_Park')
        #
        # await asyncio.sleep(2.0)
        # # Navigate to pet pavilion from commons
        # await navigate_to_pavilion_from_commons(client)
        # # Navigate to sigil
        # await navigate_to_dance_game(client)

    # lets outer functions know when the client has leveled up and has more energy to use
    if questing:
        client.character_level = await client.stats.reference_level()

    await asyncio.sleep(1.0)
    # feed the pet
    await nomnom(client, ignore_pet_level_up, only_play_dance_game)

    if not started_at_pavilion:
        # return to last location
        await client.send_key(Keycode.PAGE_UP, 0.1)

        # account for teleporting to mark
        # if any error occurs, just let auto quest take care of it
        try:
            await safe_wait_for_zone_change(client, name='WizardCity/WC_Streets/Interiors/WC_PET_Park', handle_hooks_if_needed=True)
        # something may have gone wrong initially with the teleport mark - we never entered a loading screen
        except LoadingScreenNotFound:
            logger.debug('Client ' + client.title + 'failed to recall from pet pavilion.')
            pass
        # we attempted to teleport to a closed dungeon
        except FriendBusyOrInstanceClosed:
            logger.debug('Client ' + client.title + 'failed to recall from pet pavilion - instance was closed.')
            pass

