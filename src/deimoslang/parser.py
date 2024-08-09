from enum import Enum, auto
from typing import Any

from tokenizer import Token, TokenKind


class XYZ:
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        self.x = x
        self.y = y
        self.z = z
    
    def __repr__(self) -> str:
        return f"XYZ({self.x}, {self.y}, {self.z})"


class ParserError(Exception):
    pass


class CommandKind(Enum):
    invalid = auto()

    expr = auto()

    kill = auto()
    sleep = auto()
    log = auto()
    teleport = auto()
    goto = auto()
    sendkey = auto()
    waitfor = auto()
    usepotion = auto()
    buypotions = auto()
    relog = auto()
    click = auto()
    tozone = auto()

class TeleportKind(Enum):
    position = auto()

class WaitforKind(Enum):
    dialog = auto()
    battle = auto()
    zonechange_any = auto()
    zonechange_from = auto()
    zonechange_to = auto()
    free = auto()
    window = auto()

class ClickKind(Enum):
    window = auto()

class LogKind(Enum):
    window = auto()
    literal = auto()

class ExprKind(Enum):
    window_visible = auto()
    in_zone = auto()


class PlayerSelector:
    def __init__(self):
        self.player_nums: list[int] = []
        self.mass = False
        self.inverted = False
    
    def validate(self):
        assert not (self.mass and self.inverted), "Invalid player selector: mass + except"
        assert not (self.mass and len(self.player_nums) > 0), "Invalid player selector: mass + specified players"
        assert not (self.inverted and len(self.player_nums) == 0), "Invalid palayer selector: inverted + 0 players"

    def __repr__(self) -> str:
        return f"PlayerSelector(nums: {self.player_nums}, mass: {self.mass}, inverted: {self.inverted})"

class Command:
    def __init__(self):
        self.kind = CommandKind.invalid
        self.data: list[Any] = []
        self.player_selector: PlayerSelector | None = None

    def __repr__(self) -> str:
        params_str = ", ".join([str(x) for x in self.data])
        if self.player_selector is None:
            return f"{self.kind.name}({params_str})"
        else:
            return f"{self.kind.name}({params_str}) @ {self.player_selector}"



class Expression:
    def __init__(self):
        pass

class NumberExpression(Expression):
    def __init__(self, number: float):
        self.number = number

    def __repr__(self) -> str:
        return f"Number({self.number})"

class StringExpression(Expression):
    def __init__(self, string: str):
        self.string = string
    
    def __repr__(self) -> str:
        return f"String({self.string})"

class UnaryExpression(Expression):
    def __init__(self, operator: Token, expr: Expression):
        self.operator = operator
        self.expr = expr
    
    def __repr__(self) -> str:
        return f"Unary({self.operator.kind}, {self.expr})"

class KeyExpression(Expression):
    def __init__(self, key: str):
        self.key = key

    def __repr__(self) -> str:
        return f"Key({self.key})"

class CommandExpression(Expression):
    def __init__(self, command: Command):
        self.command = command
    
    def __repr__(self) -> str:
        return f"ComE({self.command})"


class Stmt:
    def __init__(self) -> None:
        pass

class StmtList(Stmt):
    def __init__(self, stmts: list[Stmt]):
        self.stmts = stmts

    def __repr__(self) -> str:
        return "; ".join([str(x) for x in self.stmts])

class CommandStmt(Stmt):
    def __init__(self, command: Command):
        self.command = command

    def __repr__(self) -> str:
        return f"ComS({self.command})"

class IfStmt(Stmt):
    def __init__(self, expr: Expression, branch_true: StmtList, branch_false: StmtList):
        self.expr = expr
        self.branch_true = branch_true
        self.branch_false = branch_false
    
    def __repr__(self) -> str:
        return f"IfS {self.expr} {{ {self.branch_true} }} else {{ {self.branch_false} }}"

class WhileStmt(Stmt):
    def __init__(self, expr: Expression, body: StmtList):
        self.expr = expr
        self.body = body
    
    def __repr__(self) -> str:
        return f"WhileS {self.expr} {{ {self.body} }}"

class BlockDefStmt(Stmt):
    def __init__(self, ident: str, body: StmtList) -> None:
        self.ident = ident
        self.body = body

    def __repr__(self) -> str:
        return f"BlockDefS {self.ident} {{ {self.body} }}"
    
class CallStmt(Stmt):
    def __init__(self, ident: str) -> None:
        self.ident = ident

    def __repr__(self) -> str:
        return f"CallS {self.ident}"


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.i = 0

    def skip_any(self, kinds: list[TokenKind]):
        if self.i < len(self.tokens) and self.tokens[self.i].kind in kinds:
            self.i += 1

    def skip_comma(self):
        self.skip_any([TokenKind.comma])

    def expect_consume_any(self, kinds: list[TokenKind]) -> Token:
        result = self.tokens[self.i]
        if result.kind not in kinds:
            raise ParserError(f"Expected token kinds {kinds} but got {result.kind}\n{self.tokens}")
        self.i += 1
        return result

    def expect_consume(self, kind: TokenKind) -> Token:
        return self.expect_consume_any([kind])

    def parse_atom(self) -> NumberExpression | StringExpression:
        tok = self.expect_consume_any([TokenKind.number, TokenKind.string])
        match tok.kind:
            case TokenKind.number:
                return NumberExpression(tok.value)
            case TokenKind.string:
                return StringExpression(tok.value)
            case _:
                raise ParserError(f"Invalid atom kind: {tok.kind} in {tok}")

    def parse_unary_expression(self) -> UnaryExpression | Expression:
        kinds = [TokenKind.minus]
        if self.tokens[self.i].kind in kinds:
            operator = self.expect_consume_any(kinds)
            return UnaryExpression(operator, self.parse_unary_expression())
        else:
            return self.parse_atom()
    
    def parse_command_expression(self) -> Expression:
        match self.tokens[self.i].kind:
            case TokenKind.player_num | TokenKind.keyword_mass | TokenKind.keyword_except \
                | TokenKind.command_expr_window_visible | TokenKind.command_expr_in_zone:
                return CommandExpression(self.parse_command())
            case _:
                return self.parse_unary_expression()
    
    def parse_expression(self) -> Expression:
        return self.parse_command_expression()

    def parse_player_selector(self) -> PlayerSelector:
        result = PlayerSelector()
        valid_toks = [TokenKind.keyword_mass, TokenKind.keyword_except, TokenKind.player_num, TokenKind.colon]
        expected_toks = [TokenKind.keyword_mass, TokenKind.keyword_except, TokenKind.player_num]
        while self.i < len(self.tokens) and self.tokens[self.i].kind in valid_toks:
            if self.tokens[self.i].kind not in expected_toks:
                raise ParserError(f"Invalid player selector encountered: {self.tokens[self.i]}")
            match self.tokens[self.i].kind:
                case TokenKind.keyword_mass:
                    result.mass = True
                    expected_toks = []
                    self.i += 1
                case TokenKind.keyword_except:
                    result.inverted = True
                    expected_toks = [TokenKind.player_num]
                    self.i += 1
                case TokenKind.player_num:
                    result.player_nums.append(self.tokens[self.i].literal)
                    expected_toks = [TokenKind.colon]
                    self.i += 1
                case TokenKind.colon:
                    expected_toks = [TokenKind.player_num]
                    self.i += 1
                case _:
                    assert False
        result.validate()
        if len(result.player_nums) == 0:
            result.mass = True
        result.validate() # sanity check
        return result

    def parse_key(self) -> KeyExpression:
        # We must accept kill as well here as there is a naming collision for END
        tok = self.expect_consume_any([TokenKind.identifier, TokenKind.command_kill])
        return KeyExpression(tok.literal)

    def parse_xyz(self) -> XYZ:
        self.expect_consume(TokenKind.keyword_xyz)
        vals = []
        valid_toks = [TokenKind.paren_open, TokenKind.paren_close, TokenKind.comma, TokenKind.number, TokenKind.minus]
        expected_toks = [TokenKind.paren_open]
        found_closing = False
        while self.i < len(self.tokens) and self.tokens[self.i].kind in valid_toks:
            if self.tokens[self.i].kind not in expected_toks:
                raise ParserError(f"Invalid xyz encountered: {self.tokens[self.i]}")
            match self.tokens[self.i].kind:
                case TokenKind.paren_open:
                    self.i += 1
                    expected_toks = [TokenKind.comma, TokenKind.number, TokenKind.paren_close, TokenKind.minus]
                case TokenKind.paren_close:
                    self.i += 1
                    expected_toks = []
                    found_closing = True
                case TokenKind.comma | TokenKind.number | TokenKind.minus:
                    if self.tokens[self.i].kind == TokenKind.comma:
                        vals.append(NumberExpression(0.0))
                        self.i += 1
                    else:
                        vals.append(self.parse_expression())
                        if self.tokens[self.i].kind == TokenKind.comma:
                            self.i += 1
                    expected_toks = [TokenKind.comma, TokenKind.paren_close, TokenKind.number, TokenKind.minus]
        if not found_closing:
            raise ParserError("Encountered unclosed XYZ")
        if len(vals) != 3:
            raise ParserError(f"Encountered invalid XYZ: {vals}")
        return XYZ(*vals)
    
    def parse_completion_optional(self) -> bool:
        if self.i < len(self.tokens) and self.tokens[self.i].kind == TokenKind.keyword_completion:
            self.i += 1
            return True
        return False
    
    def parse_zone_path_optional(self) -> list[str] | None:
        if self.i < len(self.tokens) and self.tokens[self.i].kind == TokenKind.path:
            result = self.tokens[self.i]
            self.i += 1
            return result.value
        return None
    
    def parse_zone_path(self) -> list[str] | None:
        res = self.parse_zone_path_optional()
        if res is None:
            raise ParserError("Encountered in_zone without zone path")
        return res
    
    def parse_list(self) -> list[Expression]:
        result = []
        self.expect_consume(TokenKind.square_open)
        while self.i < len(self.tokens) and self.tokens[self.i].kind != TokenKind.square_close:
            if self.tokens[self.i].kind != TokenKind.comma:
                result.append(self.parse_atom())
            else:
                self.i += 1
        self.expect_consume(TokenKind.square_close)
        return result

    def parse_window_path(self) -> list[str]:
        result = []
        for x in self.parse_list():
            if not isinstance(x, StringExpression):
                raise ParserError(f"Invalid path entry: {x}")
            result.append(x.string)
        return result

    def end_line(self):
        self.expect_consume(TokenKind.END_LINE)

    def end_line_optional(self):
        if self.tokens[self.i].kind == TokenKind.END_LINE:
            self.i += 1

    def parse_command(self) -> Command:
        result = Command()
        result.player_selector = self.parse_player_selector()
        
        match self.tokens[self.i].kind:
            case TokenKind.command_kill:
                result.kind = CommandKind.kill
                self.i += 1
                self.end_line()
            case TokenKind.command_log:
                result.kind = CommandKind.log
                self.i += 1
                if self.tokens[self.i] == TokenKind.identifier and self.tokens[self.i].literal == "window":
                    result.data = [LogKind.window, self.parse_window_path()]
                else:
                    result.data = [LogKind.literal]
                    while self.tokens[self.i].kind != TokenKind.END_LINE:
                        result.data.append(self.tokens[self.i])
                        self.i += 1
                self.end_line()
            case TokenKind.command_teleport:
                result.kind = CommandKind.teleport
                self.i += 1
                result.data = [TeleportKind.position, self.parse_xyz()]
                self.end_line()
            case TokenKind.command_sleep:
                result.kind = CommandKind.sleep
                self.i += 1
                result.data = [self.parse_expression()]
                self.end_line()
            case TokenKind.command_sendkey:
                result.kind = CommandKind.sendkey
                self.i += 1
                result.data.append(self.parse_key())
                self.skip_comma()
                result.data.append(self.parse_expression())
                self.end_line()
            case TokenKind.command_waitfor_zonechange:
                result.kind = CommandKind.waitfor
                self.i += 1
                kind = WaitforKind.zonechange_any
                if self.tokens[self.i].kind == TokenKind.keyword_to:
                    kind = WaitforKind.zonechange_to
                    self.i += 1
                elif self.tokens[self.i].kind == TokenKind.keyword_from:
                    kind = WaitforKind.zonechange_from
                    self.i += 1
                result.data = [kind, self.parse_zone_path_optional(), self.parse_completion_optional()]
                self.end_line()
            case TokenKind.command_waitfor_battle:
                result.kind = CommandKind.waitfor
                self.i += 1
                result.data = [WaitforKind.battle, self.parse_completion_optional()]
                self.end_line()
            case TokenKind.command_waitfor_window:
                result.kind = CommandKind.waitfor
                self.i += 1
                result.data = [WaitforKind.window, self.parse_window_path(), self.parse_completion_optional()]
                self.end_line()
            case TokenKind.command_waitfor_free:
                result.kind = CommandKind.waitfor
                self.i += 1
                result.data = [WaitforKind.free, self.parse_completion_optional()]
                self.end_line()
            case TokenKind.command_waitfor_dialog:
                result.kind = CommandKind.waitfor
                self.i += 1
                result.data = [WaitforKind.dialog, self.parse_completion_optional()]
                self.end_line()
            case TokenKind.command_goto:
                result.kind = CommandKind.goto
                self.i += 1
                result.data = [self.parse_xyz()]
                self.end_line()
            case TokenKind.command_clickwindow:
                result.kind = CommandKind.click
                self.i += 1
                result.data = [ClickKind.window, self.parse_window_path()]
                self.end_line()
            
            case TokenKind.command_expr_window_visible:
                result.kind = CommandKind.expr
                self.i += 1
                result.data = [ExprKind.window_visible, self.parse_window_path()]
            case TokenKind.command_expr_in_zone:
                result.kind = CommandKind.expr
                self.i += 1
                result.data = [ExprKind.in_zone, self.parse_zone_path()]
            case _:
                raise ParserError(f"Unhandled command token: {self.tokens[self.i]}")
        return result
    
    def parse_block(self) -> StmtList:
        inner = []
        self.expect_consume(TokenKind.curly_open)
        self.end_line_optional()
        while self.i < len(self.tokens) and self.tokens[self.i].kind != TokenKind.curly_close:
            inner.append(self.parse_stmt())
        self.expect_consume(TokenKind.curly_close)
        self.end_line_optional()
        return StmtList(inner)

    def consume_any_ident(self) -> Token:
        result = self.tokens[self.i]
        if result.kind != TokenKind.identifier and "keyword" not in result.kind.name and "command" not in result.kind.name:
            raise ParserError(f"Unable to consume an identifier. Got: {result}")
        self.i += 1
        return result

    def parse_stmt(self) -> Stmt:
        match self.tokens[self.i].kind:
            case TokenKind.keyword_block:
                self.i += 1
                ident = self.consume_any_ident()
                body = self.parse_block()
                return BlockDefStmt(ident.literal, body)
            case TokenKind.keyword_call:
                self.i += 1
                ident = self.consume_any_ident()
                self.end_line()
                return CallStmt(ident.literal)
            case TokenKind.keyword_while:
                self.i += 1
                expr = self.parse_expression()
                body = self.parse_block()
                return WhileStmt(expr, body)
            case TokenKind.keyword_if:
                self.i += 1
                expr = self.parse_expression()
                true_body = self.parse_block()
                else_body = StmtList([])
                if self.tokens[self.i].kind == TokenKind.keyword_else:
                    self.i += 1
                    else_body = self.parse_block()
                return IfStmt(expr, true_body, else_body)
            case TokenKind.curly_open:
                return self.parse_block()
            case _:
                return CommandStmt(self.parse_command())

    def parse(self) -> list[Stmt]:
        result = []
        while self.i < len(self.tokens):
            stmt = self.parse_stmt()
            result.append(stmt)
        return result


if __name__ == "__main__":
    from tokenizer import tokenize
    from pathlib import Path

    toks = tokenize(Path("testbot.txt").read_text())
    parser = Parser(toks)
    print(parser.parse())
