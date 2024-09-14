from enum import Enum, auto
from typing import Any


class TokenizerError(Exception):
    pass

class Percent(float):
    pass


class TokenKind(Enum):
    player_num = auto()
    string = auto()
    number = auto()
    percent = auto()
    path = auto() # A/B/C

    keyword_block = auto()
    keyword_call = auto()
    keyword_while = auto()
    keyword_until = auto()
    keyword_if = auto()
    keyword_elif = auto()
    keyword_else = auto()
    keyword_except = auto()
    keyword_mass = auto()
    keyword_mob = auto()
    keyword_quest = auto()
    keyword_icon = auto()
    keyword_ifneeded = auto()
    keyword_completion = auto()
    keyword_from = auto()
    keyword_to = auto()
    keyword_xyz = auto()
    keyword_orient = auto()
    keyword_not = auto()

    command_kill = auto()
    command_sleep = auto()
    command_log = auto()
    command_goto = auto()
    command_sendkey = auto()
    command_waitfor_dialog = auto()
    command_waitfor_battle = auto()
    command_waitfor_zonechange = auto()
    command_waitfor_free = auto()
    command_waitfor_window = auto()
    command_usepotion = auto()
    command_buypotions = auto()
    command_relog = auto()
    command_click = auto()
    command_clickwindow = auto()
    command_teleport = auto()
    command_friendtp = auto()
    command_entitytp = auto()
    command_tozone = auto()
    command_load_playstyle = auto()

    # command expressions
    command_expr_window_visible = auto()
    command_expr_in_zone = auto()
    command_expr_same_zone = auto()
    command_expr_playercount = auto()
    command_expr_tracking_quest = auto()
    command_expr_tracking_goal = auto()
    command_expr_loading = auto()
    command_expr_in_combat = auto()
    command_expr_has_dialogue = auto()
    command_expr_has_xyz = auto()
    command_expr_health_below = auto()
    command_expr_health_above = auto()
    command_expr_health = auto()
    command_expr_bagcount = auto()
    command_expr_bagcount_above = auto()
    command_expr_bagcount_below = auto()
    command_expr_mana = auto()
    command_expr_mana_above = auto()
    command_expr_mana_below = auto()
    command_expr_in_range = auto()
    command_expr_gold = auto()
    command_expr_gold_above = auto()
    command_expr_gold_below = auto()
    command_expr_window_disabled = auto()
    command_expr_same_place = auto()

    colon = auto() # :
    comma = auto()

    plus = auto()
    minus = auto()
    star = auto()
    slash = auto()

    slash_slash = auto()
    star_star = auto()

    paren_open = auto() # (
    paren_close = auto() # )
    square_open = auto() # [
    square_close = auto() # ]
    curly_open = auto() # {
    curly_close = auto() # }

    identifier = auto()

    END_LINE = auto()
    END_FILE = auto()

class LineInfo:
    def __init__(self, line: int, column: int, last_column: int, last_line: int | None = None, filename: str | None = None):
        self.line = line
        self.column = column
        self.last_column = last_column
        self.filename = filename
        self.last_line = last_line if last_line is not None else line

    def __repr__(self) -> str:
        if self.filename != None:
            return f"{self.filename}:{self.line}:{self.column}-{self.last_column}"
        return f"{self.line}:{self.column}-{self.last_column}"

class Token:
    def __init__(self, kind: TokenKind, literal: str, line_info: LineInfo, value: Any | None = None):
        self.kind = kind
        self.literal = literal
        self.value = value
        self.line_info = line_info

    def __repr__(self) -> str:
        return f"{self.line_info} {self.kind.name}`{self.literal}`({self.value})"


def render_tokens(toks: list[Token]) -> str:
    lines_strs: dict[int, str] = {}
    for tok in toks:
        if tok.line_info.line not in lines_strs:
            lines_strs[tok.line_info.line] = ""
        spaces = " " * (tok.line_info.column - 1 - len(lines_strs[tok.line_info.line]))
        lines_strs[tok.line_info.line] += spaces + tok.literal
    return "\n".join(lines_strs.values())


def normalize_ident(dirty: str) -> str:
    return dirty.lower().replace("_", "")


class Tokenizer:
    def __init__(self):
        self._in_multiline_string = False
        self._multiline_buffer = ""
        self._multiline_start_line_info = LineInfo(0, 0, 0, 0)

    def tokenize_line(self, l: str, line_num: int, filename: str | None = None) -> list[str]:
        result = []
        i = 0

        def put_simple(kind: TokenKind, literal: str, value: Any = None):
            nonlocal result, line_num, i, filename
            line_info = LineInfo(line=line_num, column=i+1, last_column=i+len(literal)+1, filename=filename)
            result.append(Token(kind, literal, line_info, value))

        def err(message: str, column_start: int):
            indent_start = " " * column_start
            raise TokenizerError(f"{message}\n{l}\n{indent_start}^\nLine: {line_num} | Column: {column_start+1}")

        while i < len(l):
            c = l[i]

            if self._in_multiline_string:
                self._multiline_buffer += c
                if c == "`":
                    self._multiline_start_line_info.last_column = i + 1
                    self._multiline_start_line_info.last_line = line_num + 1
                    result.append(Token(TokenKind.string, self._multiline_buffer, self._multiline_start_line_info, self._multiline_buffer[1:-1]))
                    self._in_multiline_string = False
                    self._multiline_buffer = ""
                i += 1
            else:
                match c:
                    case ":":
                        put_simple(TokenKind.colon, c)
                        i += 1
                    case ",":
                        put_simple(TokenKind.comma, c)
                        i += 1
                    case "+":
                        put_simple(TokenKind.plus, c)
                        i += 1
                    case "-":
                        put_simple(TokenKind.minus, c)
                        i += 1
                    case "*":
                        if i + 1 < len(l) and l[i + 1] == "*":
                            put_simple(TokenKind.star_star, "**")
                            i += 2
                        else:
                            put_simple(TokenKind.star, c)
                            i += 1
                    case "/":
                        if i + 1 < len(l) and l[i + 1] == "/":
                            put_simple(TokenKind.slash_slash, "//")
                            i += 2
                        else:
                            put_simple(TokenKind.slash, c)
                            i += 1
                    case "(":
                        put_simple(TokenKind.paren_open, c)
                        i += 1
                    case ")":
                        put_simple(TokenKind.paren_close, c)
                        i += 1
                    case "[":
                        put_simple(TokenKind.square_open, c)
                        i += 1
                    case "]":
                        put_simple(TokenKind.square_close, c)
                        i += 1
                    case "{":
                        put_simple(TokenKind.curly_open, c)
                        i += 1
                    case "}":
                        put_simple(TokenKind.curly_close, c)
                        i += 1

                    case '"' | "'":
                        quote_kind = c
                        str_lit = c
                        j = i + 1
                        while j < len(l) and l[j] != quote_kind:
                            str_lit += l[j]
                            j += 1
                        if j >= len(l):
                            err(f"Unclosed string encountered", i)
                        str_lit += l[j]
                        j += 1
                        put_simple(TokenKind.string, str_lit, str_lit[1:-1])
                        i = j
                    case "`":
                        self._multiline_buffer = c
                        self._in_multiline_string = True
                        self._multiline_start_line_info = LineInfo(line=line_num, column=i+1, last_column=i+1, filename=filename)
                        i += 1
                    case "#":
                        break

                    case _:
                        if c.isspace():
                            i += 1
                        else:
                            full = ""
                            j = i
                            while j < len(l) and not (l[j].isspace() or l[j] in "():[],`"):
                                full += l[j]
                                j += 1

                            if len(full) == 0:
                                pass
                            elif all([x.isnumeric() or x in ".e-%" for x in full]):
                                if '%' in full:
                                    try:
                                        put_simple(TokenKind.percent, full, Percent(float(full[:-1])/100))
                                    except ValueError:
                                        err("Unable to convert to percent", i)
                                else:
                                    try:
                                        put_simple(TokenKind.number, full, float(full))
                                    except ValueError:
                                        err("Unable to convert to number", i)
                            elif "/" in full:
                                if full.endswith("/"):
                                    err("Invalid path", i)
                                put_simple(TokenKind.path, full, full.split("/"))
                            elif full[0].lower() == "p" and full[1:len(full)].isnumeric():
                                put_simple(TokenKind.player_num, full, int(full[1:len(full)]))
                            else:
                                match normalize_ident(full):
                                    case "block":
                                        put_simple(TokenKind.keyword_block, full)
                                    case "call":
                                        put_simple(TokenKind.keyword_call, full)
                                    case "while":
                                        put_simple(TokenKind.keyword_while, full)
                                    case "until":
                                        put_simple(TokenKind.keyword_until, full)
                                    case "if":
                                        put_simple(TokenKind.keyword_if, full)
                                    case "else":
                                        put_simple(TokenKind.keyword_else, full)
                                    case "elif":
                                        put_simple(TokenKind.keyword_elif, full)
                                    case "except":
                                        put_simple(TokenKind.keyword_except, full)
                                    case "mass":
                                        put_simple(TokenKind.keyword_mass, full)
                                    case "closestmob" | "mob":
                                        put_simple(TokenKind.keyword_mob, full)
                                    case "quest" | "questpos" | "questposition":
                                        put_simple(TokenKind.keyword_quest, full)
                                    case "icon":
                                        put_simple(TokenKind.keyword_icon, full)
                                    case "ifneeded":
                                        put_simple(TokenKind.keyword_ifneeded, full)
                                    case "completion":
                                        put_simple(TokenKind.keyword_completion, full)
                                    case "xyz":
                                        put_simple(TokenKind.keyword_xyz, full)
                                    case "orient":
                                        put_simple(TokenKind.keyword_orient, full)
                                    case "not":
                                        put_simple(TokenKind.keyword_not, full)

                                    case "kill" | "killbot" | "stop" | "stopbot" | "end" | "exit":
                                        put_simple(TokenKind.command_kill, full)
                                    case "sleep" | "wait" | "delay":
                                        put_simple(TokenKind.command_sleep, full)
                                    case "log" | "debug" | "print":
                                        put_simple(TokenKind.command_log, full)
                                    case "teleport" | "tp" | "setpos":
                                        put_simple(TokenKind.command_teleport, full)
                                    case "goto" | "walkto":
                                        put_simple(TokenKind.command_goto, full)
                                    case "sendkey" | "press" | "presskey":
                                        put_simple(TokenKind.command_sendkey, full)
                                    case "waitfordialog" | "waitfordialogue":
                                        put_simple(TokenKind.command_waitfor_dialog, full)
                                    case "waitforbattle" | "waitforcombat":
                                        put_simple(TokenKind.command_waitfor_battle, full)
                                    case "waitforzonechange":
                                        put_simple(TokenKind.command_waitfor_zonechange, full)
                                    case "waitforfree":
                                        put_simple(TokenKind.command_waitfor_free, full)
                                    case "waitforwindow" | "waitforpath":
                                        put_simple(TokenKind.command_waitfor_window, full)
                                    case "usepotion":
                                        put_simple(TokenKind.command_usepotion, full)
                                    case "buypotions" | "refillpotions" | "buypots" | "refillpots":
                                        put_simple(TokenKind.command_buypotions, full)
                                    case "relog" | "logoutandin":
                                        put_simple(TokenKind.command_relog, full)
                                    case "click":
                                        put_simple(TokenKind.command_click, full)
                                    case "clickwindow":
                                        put_simple(TokenKind.command_clickwindow, full)
                                    case "friendtp" | "friendteleport":
                                        put_simple(TokenKind.command_friendtp, full)
                                    case "entitytp" | "entityteleport":
                                        put_simple(TokenKind.command_entitytp, full)
                                    case "tozone":
                                        put_simple(TokenKind.command_tozone, full)
                                    case "loadplaystyle":
                                        put_simple(TokenKind.command_load_playstyle, full)

                                    # expression commands
                                    case "windowvisible":
                                        put_simple(TokenKind.command_expr_window_visible, full)
                                    case "inzone":
                                        put_simple(TokenKind.command_expr_in_zone, full)
                                    case "samezone":
                                        put_simple(TokenKind.command_expr_same_zone, full)
                                    case "playercount" | "clientcount":
                                        put_simple(TokenKind.command_expr_playercount, full)
                                    case "trackingquest":
                                        put_simple(TokenKind.command_expr_tracking_quest, full)
                                    case "trackinggoal":
                                        put_simple(TokenKind.command_expr_tracking_goal, full)
                                    case "loading":
                                        put_simple(TokenKind.command_expr_loading, full)
                                    case "incombat":
                                        put_simple(TokenKind.command_expr_in_combat, full)
                                    case "hasdialogue":
                                        put_simple(TokenKind.command_expr_has_dialogue, full)
                                    case "hasxyz":
                                        put_simple(TokenKind.command_expr_has_xyz, full)
                                    case "healthbelow":
                                        put_simple(TokenKind.command_expr_health_below, full)
                                    case "healthabove":
                                        put_simple(TokenKind.command_expr_health_above, full)
                                    case "health":
                                        put_simple(TokenKind.command_expr_health, full)
                                    case "manabelow":
                                        put_simple(TokenKind.command_expr_mana_below, full)
                                    case "manaabove":
                                        put_simple(TokenKind.command_expr_mana_above, full)
                                    case "mana":
                                        put_simple(TokenKind.command_expr_mana, full)
                                    case "bagcount":
                                        put_simple(TokenKind.command_expr_bagcount, full)
                                    case "bagcountbelow":
                                        put_simple(TokenKind.command_expr_bagcount_below, full)
                                    case "bagcountabove":
                                        put_simple(TokenKind.command_expr_bagcount_above, full)
                                    case "gold":
                                        put_simple(TokenKind.command_expr_gold, full)
                                    case "goldabove":
                                        put_simple(TokenKind.command_expr_gold_above, full)
                                    case "goldbelow":
                                        put_simple(TokenKind.command_expr_gold_below, full)
                                    case "windowdisabled":
                                        put_simple(TokenKind.command_expr_window_disabled, full)
                                    case "sameplace":
                                        put_simple(TokenKind.command_expr_same_place, full)
                                    case _:
                                        put_simple(TokenKind.identifier, full)
                            i = j
        if not self._in_multiline_string:
            put_simple(TokenKind.END_LINE, "")
        return result

    def tokenize(self, contents: str, filename: str | None = None) -> list[Token]:
        result = []
        for line_num, line in enumerate(contents.splitlines()):
            toks = self.tokenize_line(line, line_num+1, filename=filename)
            if self._in_multiline_string:
                self._multiline_buffer += "\n"
            elif len(toks) == 1:
                # only end line
                continue
            result.extend(toks)
        if self._in_multiline_string:
            raise TokenizerError(f"Unclosed multiline string: {self._multiline_buffer} {self._multiline_start_line_info}")
        return result


if __name__ == "__main__":
    from pathlib import Path
    tokenizer = Tokenizer()
    toks = tokenizer.tokenize(Path("testbot.txt").read_text(), filename="testbot.txt")
    for i in toks:
        print(i)
