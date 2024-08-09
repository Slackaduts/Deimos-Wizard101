from enum import Enum, auto
from typing import Any

from .tokenizer import *
from .parser import *


class CompilerError(Exception):
    pass


class DeimosInstruction(Enum):
    sendkey = auto()


class InstructionKind(Enum):
    kill = auto()
    sleep = auto()
    log_literal = auto()
    log_window = auto()

    jump = auto()
    jump_if = auto()
    jump_ifn = auto()

    label = auto()
    ret = auto()
    call = auto()
    deimos_call = auto()

class Instruction:
    def __init__(self, kind: InstructionKind, data: Any | None = None) -> None:
        self.kind = kind
        self.data = data

    def __repr__(self) -> str:
        if self.data:
            return f"{self.kind.name} {self.data}"
        return f"{self.kind.name}"


class Compiler:
    def __init__(self, stmts: list[Stmt]):
        self._stmts = stmts
        self._program: list[Instruction] = []

    @staticmethod
    def from_text(code: str) -> "Compiler":
        parser = Parser(tokenize(code))
        return Compiler(parser.parse())

    def emit(self, kind: InstructionKind, data: Any | None = None):
        self._program.append(Instruction(kind, data))

    def emit_deimos_call(self, com: Command):
        self.emit(InstructionKind.deimos_call, [com.player_selector, com.kind.name, com.data])

    def compile_command(self, com: Command):
        match com.kind:
            case CommandKind.kill:
                self.emit(InstructionKind.kill)
            case CommandKind.sleep:
                self.emit(InstructionKind.sleep, com.data[0])
            case CommandKind.log:
                kind = InstructionKind.log_window if com.data[0] == LogKind.window else InstructionKind.log_literal
                self.emit(kind, com.data[1:len(com.data)])

            case CommandKind.sendkey | CommandKind.click | CommandKind.teleport \
                | CommandKind.goto | CommandKind.waitfor:
                self.emit_deimos_call(com)

            case _:
                raise CompilerError(f"Unimplemented command: {com}")

    def compile(self) -> list[Instruction]:
        for stmt in self._stmts:
            match stmt:
                case CommandStmt():
                    self.compile_command(stmt.command)
                case BlockDefStmt():
                    instrs_body = Compiler(stmt.body.stmts).compile()
                    self.emit(InstructionKind.jump, len(instrs_body) + 3)
                    self.emit(InstructionKind.label, stmt.ident)
                    self._program.extend(instrs_body)
                    self.emit(InstructionKind.ret)
                case IfStmt():
                    instrs_false = Compiler(stmt.branch_false.stmts).compile()
                    instrs_true = Compiler(stmt.branch_true.stmts).compile()
                    self.emit(InstructionKind.jump_if, [stmt.expr, len(instrs_false) + 2]) # account for the jump in false branch
                    self._program.extend(instrs_false)
                    self.emit(InstructionKind.jump, len(instrs_true) + 1)
                    self._program.extend(instrs_true)
                case WhileStmt():
                    body_compiler = Compiler(stmt.body.stmts)
                    body_compiler.compile()
                    body_compiler.emit(InstructionKind.jump_if, [stmt.expr, -len(body_compiler._program)])
                    instrs_body = body_compiler._program
                    self.emit(InstructionKind.jump_ifn, [stmt.expr, len(instrs_body) + 1])
                    self._program.extend(instrs_body)
                case CallStmt():
                    self.emit(InstructionKind.call, stmt.ident)
                case _:
                    raise CompilerError(f"Unknown statement: {stmt}")
        return self._program


if __name__ == "__main__":
    from pathlib import Path
    compiler = Compiler.from_text(Path("testbot.txt").read_text())
    prog = compiler.compile()
    for i in prog:
        print(i)
    #print(prog)
