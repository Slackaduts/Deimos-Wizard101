import asyncio

from pymem.exception import MemoryReadError
from wizwalker import HookAlreadyActivated, HookNotActive, HookNotReady, Client
from wizwalker.memory import HookHandler, SimpleHook

from loguru import logger
import traceback

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

    self._active_hooks[DanceGameMovesHook] = hook
    #self._active_hooks.append(hook)
    self._base_addrs["dance_game_moves"] = hook.dance_game_moves

    if wait_for_ready:
        await self._wait_for_value(hook.dance_game_moves, timeout)


HookHandler.activate_dance_game_moves_hook = activate_dance_game_moves_hook


async def deactivate_dance_game_moves_hook(self):
    if not self._check_if_hook_active(DanceGameMovesHook):
        raise HookNotActive("DanceGameMovesHook")

    hook = self._get_hook_by_type(DanceGameMovesHook)
    #self._active_hooks.remove(hook)
    del self._active_hooks[DanceGameMovesHook]
    await hook.unhook()

    del self._base_addrs["dance_game_moves"]


HookHandler.deactivate_dance_game_moves_hook = deactivate_dance_game_moves_hook

async def attempt_activate_dance_hook(client: Client, sleep_time: float = 0.1):
    # Attempts to activate dance hook, in a try block in case it's already off for this client
    if not client.dance_hook_status:
        try:
            await client.hook_handler.activate_dance_game_moves_hook()
        except:
            logger.debug("failed to activate dance hook")
            logger.debug(traceback.print_exc())
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