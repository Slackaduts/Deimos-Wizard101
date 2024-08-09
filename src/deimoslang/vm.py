import asyncio

#from wizwalker import Client

from tokenizer import *
from parser import *
from ir import *


class VMError(Exception):
    pass


class VM:
    def __init__(self, clients: list):
        self.clients = clients
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

    async def _eval_command_expression(self, expression: CommandExpression):
        assert expression.command.kind == CommandKind.expr
        assert type(expression.command.data) is list
        assert type(expression.command.data[0]) is ExprKind

        selector = expression.command.player_selector
        match expression.command.data[0]:
            case ExprKind.window_visible:
                return False
            case _:
                pass

    async def eval(self, expression: Expression):
        match expression:
            case CommandExpression():
                return await self._eval_command_expression(expression)
            case NumberExpression():
                return expression.number
            case _:
                raise VMError(f"Unimplemented expression type: {expression}")

    async def step(self):
        if not self.running:
            return
        instruction = self.program[self._ip]
        match instruction.kind:
            case InstructionKind.kill:
                self.running = False
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
                print(s)
                self._ip += 1
            case InstructionKind.label:
                self._ip += 1
            case _:
                raise VMError(f"Unimplemented instruction: {instruction}")
        if self._ip >= len(self.program):
            self._ip = 0

    async def run(self):
        self.running = True
        while self.running:
            await self.step()


async def main():
    import pathlib
    vm = VM([])
    vm.load_from_text(pathlib.Path("testbot.txt").read_text())
    await vm.run()

asyncio.run(main())