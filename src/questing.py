import asyncio

from typing import Optional
from enum import Enum, auto

from loguru import logger

import regex

from src.teleport_math import *
from src.utils import *
from src.paths import quest_name_path, npc_range_path
from src.task_watcher import TaskWatcher
from src.barriers import *


class QuestKind(Enum):
    collect = auto()
    unknown = auto()


class TeleportResult(Enum):
    same_zone = auto()
    new_zone = auto()


class QuestCtx:
    ## The new leader mechanism. Multiple clients may share one quest context so they perform the same actions together.
    def __init__(self):
        self.owner: Optional[Client] = None
        self.full_text: Optional[str] = None
        self.clean_text: Optional[str] = None
        self.quest_xyz: Optional[XYZ] = None


class Quester:
    def __init__(self, client: Client):
        self.client = client
        self.current_context: Optional[QuestCtx] = None
        self.barrier = TimedBarrier()
        self._teleport_result = SingleWriteValue[TeleportResult]()
        self._watchdog = TaskWatcher()
        self._teleport_task: Optional[asyncio.Task] = None

    async def _create_context(self):
        logger.debug("refreshing quest context")
        ctx = QuestCtx()
        ctx.owner = self.client
        ctx.full_text = await self.fetch_quest_text()
        ctx.clean_text = self.clean_quest_text(ctx.full_text)
        ctx.quest_xyz = await self.client.quest_position.position()
        self.current_context = ctx

    def identify_quest_kind(self, quest_text: str) -> QuestKind:
        ## Attempts to identify a quest kind, returns unknown if it is unable to do so.
        if quest_text.startswith("collect"):
            return QuestKind.collect
        logger.error(f"Unable to identify a special quest kind for quest: `{quest_text}`\nUsing fallback method.")
        return QuestKind.unknown


    def clean_quest_text(self, quest_text: str) -> str:
        ## Cleans quest text for use in other functions with uniform structure.
        clean_text = regex.sub(r"<\/?([^>])+>", "", quest_text)
        lower_clean = clean_text.lower()
        return lower_clean

    async def fetch_quest_text(self):
        ## Grabs the text instructions of a quest
        quest_text_window = await get_window_from_path(self.client.root_window, quest_name_path)
        while not quest_text_window:
            await asyncio.sleep(0.1)
            quest_text_window = await get_window_from_path(self.client.root_window, quest_name_path)
        quest_text = await quest_text_window.maybe_text()
        return quest_text

    async def _is_blocked(self):
        ## Inversion of is_free
        return not await is_free(self.client)

    def _start_ctx_tp(self):
        ## Uses the current context to perform a navmap tp
        async def _impl(self: Quester):
            assert self.current_context is not None
            assert self.current_context.quest_xyz is not None
            ticket = self.barrier.fetch()
            if self._teleport_result.filled():
                raise RuntimeError("Tried teleporting while previous teleport result hasn't been consumed.")
            try:
                starting_zone_name = await self.client.zone_name()
                await navmap_tp(self.client, xyz=self.current_context.quest_xyz)
                if await self.client.is_loading() or await self.client.zone_name() != starting_zone_name:
                    self._teleport_result.write(TeleportResult.new_zone)
                self._teleport_result.write(TeleportResult.same_zone)
            finally:
                self.barrier.submit(ticket)
        self._teleport_task = self._watchdog.new_task(_impl(self))

    async def _handle_interact(self):
        popup_window = await get_window_from_path(self.client.root_window, popup_title_path)
        if not popup_window or not await popup_window.is_visible():
            return
        await self.client.send_key(Keycode.X, 0.1)
        await asyncio.sleep(2.0)

    async def _step_impl(self, ctx: Optional[QuestCtx] = None):
        if await self._is_blocked():
            self.last_block_time = time.time()
            self.barrier.block_cooldown()
            await asyncio.sleep(0.5)
            return
        if self.barrier.is_blocked():
            return

        if ctx is not None:
            self.current_context = ctx
        elif self.current_context is not None:
            quest_text = self.clean_quest_text(await self.fetch_quest_text())
            quest_pos = await self.client.quest_position.position()
            assert self.current_context.quest_xyz is not None
            if quest_text != self.current_context.clean_text or calc_Distance(quest_pos, self.current_context.quest_xyz) > 1.0:
                # New quest text, update the context
                await self._create_context()
        else:
            # There is no context and we didn't receive one. Make a new one
            await self._create_context()

        if self._teleport_result.filled():
            # a teleport has happened and it has information for us
            tp_result = self._teleport_result.consume()
            assert self._teleport_task is not None
            self._watchdog.unregister(self._teleport_task)
            if tp_result == TeleportResult.same_zone:
                logger.debug("Zone did not change.")
                try:
                    await asyncio.wait_for(wait_for_visible_by_path(self.client, npc_range_path), timeout=5.0)
                except TimeoutError:
                    # either gonna be combat or a very slow zone transfer, do nothing.
                    pass
                else:
                    # it did not time out, there should be an interactible here.
                    logger.debug("Dialog found after tp.")
                    await self._handle_interact()
            else:
                # Zone transfer. Empty branch here for documentation purposes.
                logger.debug("Detected a zone change.")
        else:
            # begin a teleport, forces a block and waits for ticket
            self._start_ctx_tp()


    async def step(self, ctx: Optional[QuestCtx] = None):
        try:
            await self._step_impl(ctx)
        except Exception as e:
            logger.exception("Questing error", e)
            raise
