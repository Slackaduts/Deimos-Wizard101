import asyncio
import functools

from typing import Optional
from enum import Enum, auto

from loguru import logger

import regex

from wizwalker.utils import maybe_wait_for_value_with_timeout

from src.teleport_math import *
from src.utils import *
from src.paths import quest_name_path, npc_range_path


class QuestKind(Enum):
    go_to = auto()
    talk_to = auto()
    defeat = auto()
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
        self.quest_kind: Optional[QuestKind] = None
        self.quest_xyz: Optional[XYZ] = None


class Quester:
    def __init__(self, client: Client):
        self.client = client
        self.current_context: Optional[QuestCtx] = None

    async def _create_context(self):
        print("refreshing context")
        ctx = QuestCtx()
        ctx.owner = self.client
        ctx.full_text = await self.fetch_quest_text()
        ctx.clean_text = self.clean_quest_text(ctx.full_text)
        ctx.quest_kind = self.identify_quest_kind(ctx.clean_text)
        ctx.quest_xyz = await self.client.quest_position.position()
        self.current_context = ctx

    def clean_quest_text(self, quest_text: str) -> str:
        ## Cleans quest text for use in other functions with uniform structure.
        clean_text = regex.sub(r"<\/?([^>])+>", "", quest_text)
        lower_clean = clean_text.lower()
        return lower_clean

    def identify_quest_kind(self, quest_text: str) -> QuestKind:
        ## Attempts to identify a quest kind, returns unknown if it is unable to do so.
        if quest_text.startswith("talk to"):
            return QuestKind.talk_to
        elif quest_text.startswith("defeat"):
            return QuestKind.defeat
        elif quest_text.startswith("go to"):
            return QuestKind.go_to
        logger.error(f"Unable to identify quest kind for quest: `{quest_text}`\nUsing fallback method.")
        return QuestKind.unknown

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

    async def _ctx_tp(self) -> TeleportResult:
        ## Uses the current context to perform a navmap tp
        assert self.current_context is not None
        assert self.current_context.quest_xyz is not None
        starting_zone_name = await self.client.zone_name()
        await navmap_tp(self.client, xyz=self.current_context.quest_xyz)
        await asyncio.sleep(2.0)
        if await self.client.is_loading() or await self.client.zone_name() != starting_zone_name:
            return TeleportResult.new_zone
        return TeleportResult.same_zone

    async def _handle_interact(self):
        popup_window = await get_window_from_path(self.client.root_window, popup_title_path)
        if not popup_window or not await popup_window.is_visible():
            return
        await self.client.send_key(Keycode.X, 0.1)
        await asyncio.sleep(0.5)

    async def _step_impl(self, ctx: Optional[QuestCtx] = None):
        if await self._is_blocked():
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

        assert self.current_context is not None
        # These are not strictly needed. But keeping them in case one of them needs special handling later.
        print(self.current_context.quest_kind)
        match self.current_context.quest_kind:
            case QuestKind.go_to:
                await self._ctx_tp()
            case QuestKind.talk_to:
                if await self._ctx_tp() == TeleportResult.same_zone:
                    print("Zone did not change!")
                    try:
                        await asyncio.wait_for(wait_for_visible_by_path(self.client, npc_range_path), timeout=5.0)
                    except TimeoutError:
                        pass # timed out, maybe we'll have better luck next iteration.
                    else:
                        # it did not time out, there should be an interactible here.
                        await self._handle_interact()
            case QuestKind.defeat:
                await self._ctx_tp()
            case QuestKind.unknown:
                # use a generic handler that teleports towards the location and tries to handle dialog
                if await self._ctx_tp() == TeleportResult.same_zone:
                    await asyncio.sleep(1.0)
                    await self._handle_interact()


    async def step(self, ctx: Optional[QuestCtx] = None):
        try:
            await self._step_impl(ctx)
        except Exception as e:
            logger.exception("Questing error", e)
            raise
