import asyncio

from wizwalker import Client, XYZ

from .tokenizer import *
from .parser import *
from .ir import *

from src.utils import is_visible_by_path

from loguru import logger


class VMError(Exception):
    pass


class VM:
    def __init__(self, clients: list[Client]):
        self._clients = clients
        self.program: list[Instruction] = []
        self.running = False
        self._ip = 0 # instruction pointer
        self._callstack = []

    def reset(self):
        self.program = []
        self._ip = 0
        self._callstack = []

    def load_from_text(self, code: str):
        compiler = Compiler.from_text(code)
        self.program = compiler.compile()

    def player_by_num(self, num: int) -> Client:
        i = num - 1
        if i >= len(self._clients):
            tail = "client is open" if len(self._clients) == 1 else "clients are open"
            raise VMError(f"Attempted to get client {num}, but only {len(self._clients)} {tail}")
        return self._clients[i]

    def _select_players(self, selector: PlayerSelector) -> list[Client]:
        if selector.mass:
            return self._clients
        else:
            result: list[Client] = []
            if selector.inverted:
                for i, c in enumerate(self._clients):
                    if i in selector.player_nums:
                        continue
                    result.append(c)
            else:
                for i, c in enumerate(self._clients):
                    if i in selector.player_nums:
                        result.append(c)
            return result

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
                a = self.player_by_num(expression.command.data[1].value)
                b = self.player_by_num(expression.command.data[2].value)
                return (await a.zone_name()) == (await b.zone_name())
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
                    case _:
                        raise VMError(f"Unimplemented unary expression: {expression}")
            case StringExpression():
                return expression.string
            case KeyExpression():
                return expression.key
            case _:
                raise VMError(f"Unimplemented expression type: {expression}")

    async def exec_deimos_call(self, instruction: Instruction):
        assert instruction.kind == InstructionKind.deimos_call
        assert type(instruction.data) == list

        selector: PlayerSelector = instruction.data[0]
        clients = self._select_players(selector)
        match instruction.data[1]:
            case "teleport":
                args = instruction.data[2]
                assert type(args) == list
                assert type(args[0]) == TeleportKind
                match args[0]:
                    case TeleportKind.position:
                        for client in clients:
                            pos: XYZ = await self.eval(args[1], client) # type: ignore
                            await client.teleport(pos)
                    case _:
                        raise VMError(f"Unimplemented teleport kind: {instruction}")
            case _:
                raise VMError(f"Unimplemented deimos call: {instruction}")

    async def step(self):
        if not self.running:
            return
        instruction = self.program[self._ip]
        match instruction.kind:
            case InstructionKind.kill:
                self.running = False
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
                j = self._ip
                label = instruction.data
                # TODO: Less hacky solution. This scans upwards looking for labels
                while True:
                    j -= 1
                    if j < 0:
                        raise VMError(f"Unable to find label: {label}")
                    x = self.program[j]
                    if x.kind != InstructionKind.label or x.data != label:
                        continue
                    break
                self._ip = j
            case InstructionKind.ret:
                self._ip = self._callstack.pop()

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
            case InstructionKind.label:
                self._ip += 1

            case InstructionKind.deimos_call:
                await self.exec_deimos_call(instruction)
                self._ip += 1
            case _:
                raise VMError(f"Unimplemented instruction: {instruction}")
        if self._ip >= len(self.program):
            self.running = False

    async def run(self):
        self.running = True
        while self.running:
            await self.step()
