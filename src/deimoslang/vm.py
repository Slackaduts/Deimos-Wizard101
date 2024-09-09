import asyncio

from wizwalker import Client, XYZ, Keycode
from wizwalker.memory import DynamicClientObject
from wizwalker.memory.memory_objects.quest_data import QuestData, GoalData
from wizwalker.extensions.wizsprinter import SprintyClient
from wizwalker.extensions.wizsprinter.wiz_sprinter import upgrade_clients
from wizwalker.extensions.wizsprinter.wiz_navigator import toZone

from .tokenizer import *
from .parser import *
from .ir import *

from src.utils import is_visible_by_path, is_free, get_window_from_path, refill_potions, refill_potions_if_needed \
                    , logout_and_in, click_window_by_path, get_quest_name
from src.command_parser import teleport_to_friend_from_list
from src.config_combat import delegate_combat_configs, default_config

from loguru import logger


class VMError(Exception):
    pass


class VM:
    def __init__(self, clients: list[Client]):
        self._clients = upgrade_clients(clients) # guarantee it's usable
        self.program: list[Instruction] = []
        self.running = False
        self.killed = False
        self._ip = 0 # instruction pointer
        self._callstack: list[int] = []

        # Every until loop condition must be checked for every vm step.
        # Once a condition becomes True, all untils that were entered later must be exited and removed.
        # This means that the stack must be rolled back to the index stored here and the rhs of this list is discarded.
        self._until_stack_sizes: list[tuple[Expression, int]] = []

    def reset(self):
        self.program = []
        self._ip = 0
        self._callstack = []
        self._until_stack_sizes = []

    def stop(self):
        self.running = False

    def kill(self):
        self.stop()
        self.killed = True

    def load_from_text(self, code: str):
        compiler = Compiler.from_text(code)
        self.program = compiler.compile()

    def player_by_num(self, num: int) -> SprintyClient:
        i = num - 1
        if i >= len(self._clients):
            tail = "client is open" if len(self._clients) == 1 else "clients are open"
            raise VMError(f"Attempted to get client {num}, but only {len(self._clients)} {tail}")
        return self._clients[i]

    def _select_players(self, selector: PlayerSelector) -> list[SprintyClient]:
        if selector.mass:
            return self._clients
        else:
            result: list[SprintyClient] = []
            if selector.inverted:
                for i in range(len(self._clients)):
                    if i + 1 in selector.player_nums:
                        continue
                    result.append(self.player_by_num(i + 1))
            else:
                for num in selector.player_nums:
                    result.append(self.player_by_num(num))
            return result

    async def _fetch_tracked_quest(self, client: SprintyClient) -> QuestData:
        tracked_id = await client.quest_id()
        qm = await client.quest_manager()
        for quest_id, quest in (await qm.quest_data()).items():
            if quest_id == tracked_id:
                return quest
        raise VMError(f"Unable to fetch the currently tracked quest for client with title {client.title}")

    async def _fetch_tracked_quest_text(self, client: SprintyClient) -> str:
        quest = await self._fetch_tracked_quest(client)
        name_key = await quest.name_lang_key()
        name: str = await client.cache_handler.get_langcode_name(name_key)
        return name.lower().strip()

    async def _fetch_tracked_goal_text(self, client: SprintyClient) -> str:
        goal_txt = await get_quest_name(client)
        if '(' in goal_txt:
            goal_txt = goal_txt[:goal_txt.find("(")]
        return goal_txt.lower().strip()

    async def _eval_command_expression(self, expression: CommandExpression):
        assert expression.command.kind == CommandKind.expr
        assert type(expression.command.data) is list
        assert type(expression.command.data[0]) is ExprKind

        selector = expression.command.player_selector
        assert selector is not None
        clients = self._select_players(selector)
        match expression.command.data[0]:
            case ExprKind.window_visible:
                for client in clients:
                    if not await is_visible_by_path(client, expression.command.data[1]):
                        return False
                return True
            case ExprKind.in_zone:
                for client in clients:
                    zone = await client.zone_name()
                    expected = "/".join(expression.command.data[1])
                    if expected != zone:
                        return False
                return True
            case ExprKind.same_zone:
                if len(clients) == 0:
                    return True
                expected_zone = await clients[0].zone_name()
                for client in clients[1:]:
                    if await client.zone_name() != expected_zone:
                        return False
                return True
            case ExprKind.playercount:
                expected_count = await self.eval(expression.command.data[1])
                assert type(expected_count) == float
                expected_count = int(expected_count)
                return expected_count == len(self._clients)
            case ExprKind.tracking_quest:
                expected_text = expression.command.data[1]
                assert type(expected_text) == str
                for client in clients:
                    name = await self._fetch_tracked_quest_text(client)
                    if name != expected_text:
                        return False
                return True
            case ExprKind.tracking_goal:
                expected_text = expression.command.data[1]
                assert type(expected_text) == str
                for client in clients:
                    text = await self._fetch_tracked_goal_text(client)
                    if text != expected_text:
                        return False
                return True
            case ExprKind.free:
                for client in clients:
                    if await client.is_loading():
                        return False
                return True
            case ExprKind.in_combat:
                for client in clients:
                    if not await client.in_battle():
                        return False
                return True
            case ExprKind.has_dialogue:
                for client in clients:
                    if await client.is_in_dialog():
                        return True
                return False
            case ExprKind.has_xyz:
                target_pos: XYZ = await self.eval(expression.command.data[1]) # type: ignore
                for client in clients:
                    client_pos = await client.body.position()
                    if abs(target_pos - client_pos) > 1:
                        return False
                return True
            case ExprKind.health_above:
                threshold:float = await self.eval(expression.command.data[1]) # type: ignore
                for client in clients:
                    client_health = await client.stats.current_hitpoints()
                    max_health = await client.stats.max_hitpoints()
                    if client_health/max_health > threshold:
                        return True
                return False
            case ExprKind.health_below:
                threshold:float = await self.eval(expression.command.data[1]) # type: ignore
                for client in clients:
                    client_health = await client.stats.current_hitpoints()
                    max_health = await client.stats.max_hitpoints()
                    if client_health/max_health < threshold:
                        return True
                return False
            case ExprKind.health:
                health:float = await self.eval(expression.command.data[1]) # type: ignore
                for client in clients:
                    client_health = await client.stats.current_hitpoints()
                    if client_health != health:
                        return False
                return True
            case ExprKind.mana:
                mana:float = await self.eval(expression.command.data[1]) # type: ignore
                for client in clients:
                    client_mana = await client.stats.current_mana()
                    if client_mana != mana:
                        return False
                return True
            case ExprKind.mana_below:
                threshold:float = await self.eval(expression.command.data[1]) # type: ignore
                for client in clients:
                    client_mana = await client.stats.current_mana()
                    max_mana = await client.stats.max_mana()
                    if client_mana/max_mana < threshold:
                        return True
                return False
            case ExprKind.mana_above:
                threshold:float = await self.eval(expression.command.data[1]) # type: ignore
                for client in clients:
                    client_mana = await client.stats.current_mana()
                    max_mana = await client.stats.max_mana()
                    if client_mana/max_mana > threshold:
                        return True
                return False
            case ExprKind.bag_count:
                expected_count:float = await self.eval(expression.command.data[1]) # type: ignore
                for client in clients:
                    try:
                        bag = await client.backpack_space()
                        if expected_count != bag[0]:
                            return False
                    except ValueError:
                        print("You must open your bag, before accessing the count.")
                        return False
                return True
            case ExprKind.bag_count_above:
                threshold:float = await self.eval(expression.command.data[1]) # type: ignore
                for client in clients:
                    try:
                        bag = await client.backpack_space()
                        if threshold > bag[0]/bag[1]:
                            return False
                    except ValueError:
                        print("You must open your bag, before accessing the count.")
                        return False
                return True
            case ExprKind.bag_count_below:
                threshold:float = await self.eval(expression.command.data[1]) # type: ignore
                for client in clients:
                    try:
                        bag = await client.backpack_space()
                        if threshold < bag[0]/bag[1]:
                            return False
                    except ValueError:
                        print("You must open your bag, before accessing the count.")
                        return False
                return True


            case _:
                raise VMError(f"Unimplemented expression: {expression}")

    async def eval(self, expression: Expression, client: Client | None = None):
        match expression:
            case CommandExpression():
                return await self._eval_command_expression(expression)
            case NumberExpression():
                return expression.number
            case XYZExpression():
                return XYZ(
                    await self.eval(expression.x, client), # type: ignore
                    await self.eval(expression.y, client), # type: ignore
                    await self.eval(expression.z, client), # type: ignore
                )
            case UnaryExpression():
                match expression.operator.kind:
                    case TokenKind.minus:
                        return -(await self.eval(expression.expr, client)) # type: ignore
                    case TokenKind.keyword_not:
                        return not (await self.eval(expression.expr, client))
                    case _:
                        raise VMError(f"Unimplemented unary expression: {expression}")
            case StringExpression():
                return expression.string
            case KeyExpression():
                key = expression.key
                if key not in Keycode.__members__:
                    raise VMError(f"Unknown key code: {key}")
                return Keycode[expression.key]
            case _:
                raise VMError(f"Unimplemented expression type: {expression}")

    async def exec_deimos_call(self, instruction: Instruction):
        assert instruction.kind == InstructionKind.deimos_call
        assert type(instruction.data) == list

        selector: PlayerSelector = instruction.data[0]
        clients = self._select_players(selector)
        # TODO: is eval always fast enough to run in order during a TaskGroup
        match instruction.data[1]:
            case "teleport":
                args = instruction.data[2]
                assert type(args) == list
                assert type(args[0]) == TeleportKind
                async with asyncio.TaskGroup() as tg:
                    match args[0]:
                        case TeleportKind.position:
                            for client in clients:
                                pos: XYZ = await self.eval(args[1], client) # type: ignore
                                tg.create_task(client.teleport(pos))
                        case TeleportKind.entity_literal:
                            name = args[-1]
                            for client in clients:
                                tg.create_task(client.tp_to_closest_by_name(name))
                        case TeleportKind.entity_vague:
                            vague = args[-1]
                            for client in clients:
                                tg.create_task(client.tp_to_closest_by_vague_name(vague))
                        case TeleportKind.mob:
                            for client in clients:
                                tg.create_task(client.tp_to_closest_mob())
                        case TeleportKind.quest:
                            # TODO: "quest" could instead be treated as an XYZ expression or something
                            for client in clients:
                                pos = await client.quest_position.position()
                                tg.create_task(client.teleport(pos))
                        case TeleportKind.friend_icon:
                            async def proxy(client: SprintyClient): # type: ignore
                                # probably doesn't need mouseless
                                async with client.mouse_handler:
                                    await teleport_to_friend_from_list(client, icon_list=2, icon_index=0)
                            for client in clients:
                                tg.create_task(proxy(client))
                        case TeleportKind.friend_name:
                            name = args[-1]
                            async def proxy(client: SprintyClient): # type: ignore
                                async with client.mouse_handler:
                                    await teleport_to_friend_from_list(client, name=name)
                            for client in clients:
                                tg.create_task(proxy(client))
                        case TeleportKind.client_num:
                            num = args[-1]
                            target_client = self.player_by_num(num)
                            target_pos = await target_client.body.position()
                            for client in clients:
                                tg.create_task(client.teleport(target_pos))
                        case _:
                            raise VMError(f"Unimplemented teleport kind: {instruction}")
            case "goto":
                args = instruction.data[2]
                assert type(args) == list
                async with asyncio.TaskGroup() as tg:
                    for client in clients:
                        pos: XYZ = await self.eval(args[0], client) # type: ignore
                        tg.create_task(client.goto(pos.x, pos.y))
            case "waitfor":
                args = instruction.data[2]
                completion: bool = args[-1]
                assert type(completion) == bool

                async def waitfor_coro(coro, invert: bool, interval=0.25):
                    while not (invert ^ await coro()):
                        await asyncio.sleep(interval)

                async def waitfor_impl(coro, interval=0.25):
                    nonlocal completion
                    await waitfor_coro(coro, completion, interval)

                method_map = {
                    WaitforKind.dialog: Client.is_in_dialog,
                    WaitforKind.battle: Client.in_battle,
                    WaitforKind.free: is_free,
                }
                if args[0] in method_map:
                    method = method_map[args[0]]
                    async with asyncio.TaskGroup() as tg:
                        for client in clients:
                            async def proxy(): # type: ignore
                                return await method(client)
                            tg.create_task(waitfor_impl(proxy))
                else:
                    match args[0]:
                        case WaitforKind.zonechange:
                            if completion:
                                async with asyncio.TaskGroup() as tg:
                                    for client in clients:
                                        tg.create_task(waitfor_coro(client.is_loading, True))
                            else:
                                async with asyncio.TaskGroup() as tg:
                                    for client in clients:
                                        starting_zone = await client.zone_name()
                                        async def proxy():
                                            return starting_zone != (await client.zone_name())
                                        tg.create_task(waitfor_coro(proxy, False))
                        case WaitforKind.window:
                            window_path = args[1]
                            async with asyncio.TaskGroup() as tg:
                                for client in clients:
                                    async def proxy():
                                        return await is_visible_by_path(client, window_path)
                                    tg.create_task(waitfor_impl(proxy))
                        case _:
                            raise VMError(f"Unimplemented waitfor kind: {instruction}")
            case "sendkey":
                args = instruction.data[2]
                async with asyncio.TaskGroup() as tg:
                    for client in clients:
                        key: Keycode = await self.eval(args[0], client) # type: ignore
                        time: float = 0.1 if args[1] is None else (await self.eval(args[1], client)) # type: ignore
                        tg.create_task(client.send_key(key, time))
            case "usepotion":
                args = instruction.data[2]
                async with asyncio.TaskGroup() as tg:
                    for client in clients:
                        if len(args) > 0:
                            health_num: float = await self.eval(args[0], client) # type: ignore
                            mana_num: float = await self.eval(args[1], client) # type: ignore
                            tg.create_task(client.use_potion_if_needed(int(health_num), int(mana_num)))
                        else:
                            tg.create_task(client.use_potion())
            case "buypotions":
                args = instruction.data[2]
                ifneeded = args[0]
                async with asyncio.TaskGroup() as tg:
                    for client in clients:
                        if ifneeded:
                            tg.create_task(refill_potions_if_needed(client, mark=True, recall=True))
                        else:
                            tg.create_task(refill_potions(client, mark=True, recall=True))
            case "relog":
                async with asyncio.TaskGroup() as tg:
                    for client in clients:
                        tg.create_task(logout_and_in(client))
            case "click":
                args = instruction.data[2]
                async with asyncio.TaskGroup() as tg:
                    for client in clients:
                        match args[0]:
                            case ClickKind.position:
                                async def proxy(client: SprintyClient, x: float, y: float):
                                    async with client.mouse_handler:
                                        await client.mouse_handler.click(int(x), int(y))
                                x: float = args[1] # type: ignore
                                y: float = args[2] # type: ignore
                                tg.create_task(proxy(client, x, y))
                            case ClickKind.window:
                                path = args[1]
                                tg.create_task(click_window_by_path(client, path))
                            case _:
                                raise VMError(f"Unimplemented click kind: {instruction}")
            case "tozone":
                args = instruction.data[2]
                async with asyncio.TaskGroup() as tg:
                    for client in clients:
                        tg.create_task(toZone([client], "/".join(args[0])))
            case _:
                raise VMError(f"Unimplemented deimos call: {instruction}")

    async def _process_untils(self):
        for i in range(len(self._until_stack_sizes) - 1, -1, -1):
            (expr, stack_size) = self._until_stack_sizes[i]
            if await self.eval(expr):
                self._until_stack_sizes = self._until_stack_sizes[:i]
                self._callstack = self._callstack[:stack_size]
                self._ip = self._callstack.pop()
                return

    async def step(self):
        if not self.running:
            return
        await asyncio.sleep(0)
        await self._process_untils() # must run before the next instruction is fetched
        instruction = self.program[self._ip]
        match instruction.kind:
            case InstructionKind.kill:
                self.kill()
                logger.debug("Bot Killed")
            case InstructionKind.sleep:
                assert instruction.data != None
                time = await self.eval(instruction.data)
                assert type(time) is float
                await asyncio.sleep(time)
                self._ip += 1
            case InstructionKind.jump:
                assert type(instruction.data) == int
                self._ip += instruction.data
            case InstructionKind.jump_if:
                assert type(instruction.data) == list
                if await self.eval(instruction.data[0]):
                    self._ip += instruction.data[1]
                else:
                    self._ip += 1
            case InstructionKind.jump_ifn:
                assert type(instruction.data) == list
                if await self.eval(instruction.data[0]):
                    self._ip += 1
                else:
                    self._ip += instruction.data[1]

            case InstructionKind.call:
                self._callstack.append(self._ip + 1)
                jump = instruction.data  
                self._ip += jump # type: ignore

            case InstructionKind.ret:
                self._ip = self._callstack.pop()

            case InstructionKind.enter_until:
                assert type(instruction.data) == list
                exit_dist = instruction.data[1]
                self._callstack.append(self._ip + exit_dist)
                self._until_stack_sizes.append((instruction.data[0], len(self._callstack)))
                self._ip += 1 # simply advance, if the until is finished immediately that's fine because it's checked at the start of each step

            case InstructionKind.log_literal:
                assert type(instruction.data) == list
                strs = []
                for x in instruction.data:
                    match x.kind:
                        case TokenKind.string:
                            strs.append(x.value)
                        case TokenKind.identifier:
                            strs.append(x.literal)
                        case _:
                            raise VMError(f"Unable to log: {x}")
                s = " ".join(strs)
                logger.debug(s)
                self._ip += 1
            case InstructionKind.log_window:
                assert type(instruction.data) == list
                clients = self._select_players(instruction.data[0])
                path = instruction.data[1]
                async with asyncio.TaskGroup() as tg:
                    for client in clients:
                        window = await get_window_from_path(client.root_window, path)
                        if not window:
                            raise VMError(f"Unable to find window at path: {path}")
                        window_str = await window.maybe_text()
                        logger.debug(f"{client.title} - {window_str}")
                self._ip += 1
            case InstructionKind.log_bagcount:
                assert type(instruction.data) == list
                clients: list[SprintyClient] = self._select_players(instruction.data[0])
                try:
                    for client in clients:
                        bag_space = await client.backpack_space()
                        logger.debug(f'{client.title} - {bag_space[0]}/{bag_space[1]}')
                except ValueError:
                    print("You must open your bag, before accessing the count.")
                self._ip += 1
            case InstructionKind.log_health:
                assert type(instruction.data) == list
                clients: list[SprintyClient] = self._select_players(instruction.data[0])
                for client in clients:
                    logger.debug(f'{client.title} - {await client.stats.current_hitpoints()}/{await client.stats.max_hitpoints()}')
                self._ip += 1

            case InstructionKind.log_mana:
                assert type(instruction.data) == list
                clients: list[SprintyClient] = self._select_players(instruction.data[0])
                for client in clients:
                    logger.debug(f'{client.title} - {await client.stats.current_mana()}/{await client.stats.max_mana()}')
                self._ip += 1

            case InstructionKind.log_gold:
                assert type(instruction.data) == list
                clients: list[SprintyClient] = self._select_players(instruction.data[0])
                for client in clients:
                    logger.debug(f'{client.title} - {await client.stats.current_gold()}/{await client.stats.base_gold_pouch()}')
                self._ip += 1

            case InstructionKind.label | InstructionKind.nop:
                self._ip += 1

            case InstructionKind.load_playstyle:
                logger.debug("Loading playstyle")
                delegated = delegate_combat_configs(instruction.data, len(self._clients)) # type: ignore
                logger.debug(delegated)
                for i, client in enumerate(self._clients):
                    client.combat_config = delegated.get(i, default_config)
                self._ip += 1

            case InstructionKind.deimos_call:
                await self.exec_deimos_call(instruction)
                self._ip += 1
            case _:
                raise VMError(f"Unimplemented instruction: {instruction}")
        if self._ip >= len(self.program):
            self.stop()
        else:
            await asyncio.sleep(0)

    async def run(self):
        self.running = True
        while self.running:
            await self.step()
