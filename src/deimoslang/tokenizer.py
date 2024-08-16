from enum import Enum, auto
from typing import Any


class TokenizerError(Exception):
    pass


class TokenKind(Enum):
    player_num = auto()
    string = auto()
    number = auto()
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

    # command expressions
    command_expr_window_visible = auto()
    command_expr_in_zone = auto()
    command_expr_same_zone = auto()
    command_expr_playercount = auto()

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

class Token:
    def __init__(self, kind: TokenKind, literal: str, value: Any | None = None):
        self.kind = kind
        self.literal = literal
        self.value = value

    def __repr__(self) -> str:
        return f"{self.kind.name}`{self.literal}`({self.value})"


def normalize_ident(dirty: str) -> str:
    return dirty.lower().replace("_", "")

def tokenize_line(l: str) -> list[str]:
    result = []

    i = 0

    while i < len(l):
        c = l[i]
        match c:
            case ":":
                result.append(Token(TokenKind.colon, c))
                i += 1
            case ",":
                result.append(Token(TokenKind.comma, c))
                i += 1
            case "+":
                result.append(Token(TokenKind.plus, c))
                i += 1
            case "-":
                result.append(Token(TokenKind.minus, c))
                i += 1
            case "*":
                i += 1
                if i < len(l) and l[i] == "*":
                    result.append(Token(TokenKind.star_star, "**"))
                else:
                    result.append(Token(TokenKind.star, c))
            case "/":
                i += 1
                if i < len(l) and l[i] == "/":
                    result.append(Token(TokenKind.slash_slash, "//"))
                else:
                    result.append(Token(TokenKind.slash, c))
            case "(":
                result.append(Token(TokenKind.paren_open, c))
                i += 1
            case ")":
                result.append(Token(TokenKind.paren_close, c))
                i += 1
            case "[":
                result.append(Token(TokenKind.square_open, c))
                i += 1
            case "]":
                result.append(Token(TokenKind.square_close, c))
                i += 1
            case "{":
                result.append(Token(TokenKind.curly_open, c))
                i += 1
            case "}":
                result.append(Token(TokenKind.curly_close, c))
                i += 1

            case '"' | "'":
                quote_kind = c
                str_lit = c
                i += 1
                while i < len(l) and l[i] != quote_kind:
                    str_lit += l[i]
                    i += 1
                if i >= len(l):
                    raise TokenizerError("Unclosed string encountered")
                str_lit += l[i]
                i += 1
                result.append(Token(TokenKind.string, str_lit, str_lit[1:-1]))

            case "#":
                break

            case _:
                if c.isspace():
                    i += 1
                else:
                    full = ""
                    while i < len(l) and not (l[i].isspace() or l[i] in "():[],"):
                        full += l[i]
                        i += 1

                    if len(full) == 0:
                        pass
                    elif all([x.isnumeric() or x == "." or x == "e" or x == "-" for x in full]):
                        result.append(Token(TokenKind.number, full, float(full)))
                    elif "/" in full:
                        result.append(Token(TokenKind.path, full, full.split("/")))
                    elif full[0].lower() == "p" and full[1:len(full)].isnumeric():
                        result.append(Token(TokenKind.player_num, full, int(full[1:len(full)])))
                    else:
                        match normalize_ident(full):
                            case "block":
                                result.append(Token(TokenKind.keyword_block, full))
                            case "call":
                                result.append(Token(TokenKind.keyword_call, full))
                            case "while":
                                result.append(Token(TokenKind.keyword_while, full))
                            case "until":
                                result.append(Token(TokenKind.keyword_until, full))
                            case "if":
                                result.append(Token(TokenKind.keyword_if, full))
                            case "else":
                                result.append(Token(TokenKind.keyword_else, full))
                            case "elif":
                                result.append(Token(TokenKind.keyword_elif, full))
                            case "except":
                                result.append(Token(TokenKind.keyword_except, full))
                            case "mass":
                                result.append(Token(TokenKind.keyword_mass, full))
                            case "closestmob" | "mob":
                                result.append(Token(TokenKind.keyword_mob, full))
                            case "quest" | "questpos" | "questposition":
                                result.append(Token(TokenKind.keyword_quest, full))
                            case "icon":
                                result.append(Token(TokenKind.keyword_icon, full))
                            case "ifneeded":
                                result.append(Token(TokenKind.keyword_ifneeded, full))
                            case "completion":
                                result.append(Token(TokenKind.keyword_completion, full))
                            case "xyz":
                                result.append(Token(TokenKind.keyword_xyz, full))
                            case "orient":
                                result.append(Token(TokenKind.keyword_orient, full))
                            case "not":
                                result.append(Token(TokenKind.keyword_not, full))

                            case "kill" | "killbot" | "stop" | "stopbot" | "end" | "exit":
                                result.append(Token(TokenKind.command_kill, full))
                            case "sleep" | "wait" | "delay":
                                result.append(Token(TokenKind.command_sleep, full))
                            case "log" | "debug" | "print":
                                result.append(Token(TokenKind.command_log, full))
                            case "teleport" | "tp" | "setpos":
                                result.append(Token(TokenKind.command_teleport, full))
                            case "goto" | "walkto":
                                result.append(Token(TokenKind.command_goto, full))
                            case "sendkey" | "press" | "presskey":
                                result.append(Token(TokenKind.command_sendkey, full))
                            case "waitfordialog" | "waitfordialogue":
                                result.append(Token(TokenKind.command_waitfor_dialog, full))
                            case "waitforbattle" | "waitforcombat":
                                result.append(Token(TokenKind.command_waitfor_battle, full))
                            case "waitforzonechange":
                                result.append(Token(TokenKind.command_waitfor_zonechange, full))
                            case "waitforfree":
                                result.append(Token(TokenKind.command_waitfor_free, full))
                            case "waitforwindow" | "waitforpath":
                                result.append(Token(TokenKind.command_waitfor_window, full))
                            case "usepotion":
                                result.append(Token(TokenKind.command_usepotion, full))
                            case "buypotions" | "refillpotions" | "buypots" | "refillpots":
                                result.append(Token(TokenKind.command_buypotions, full))
                            case "relog" | "logoutandin":
                                result.append(Token(TokenKind.command_relog, full))
                            case "click":
                                result.append(Token(TokenKind.command_click, full))
                            case "clickwindow":
                                result.append(Token(TokenKind.command_clickwindow, full))
                            case "friendtp" | "friendteleport":
                                result.append(Token(TokenKind.command_friendtp, full))
                            case "entitytp" | "entityteleport":
                                result.append(Token(TokenKind.command_entitytp, full))
                            case "tozone":
                                result.append(Token(TokenKind.command_tozone, full))

                            # expression commands
                            case "windowvisible":
                                result.append(Token(TokenKind.command_expr_window_visible, full))
                            case "inzone":
                                result.append(Token(TokenKind.command_expr_in_zone, full))
                            case "samezone":
                                result.append(Token(TokenKind.command_expr_same_zone, full))
                            case "playercount" | "clientcount":
                                result.append(Token(TokenKind.command_expr_playercount, full))

                            case _:
                                result.append(Token(TokenKind.identifier, full))
    result.append(Token(TokenKind.END_LINE, ""))
    return result

def tokenize(contents: str) -> list[Token]:
    result = []
    for line in contents.splitlines():
        toks = tokenize_line(line)
        if len(toks) == 1:
            # only end line
            continue
        result.extend(toks)
    return result


if __name__ == "__main__":
    print(tokenize_line("\tglideTo	\t X\tYZ\t(0, 0, 0), Or\tient(90, 0, 0)"))
    print(tokenize_line("p1 walkto XYZ(1,) [a, '2'] 'test'"))
    print(tokenize_line("p1 waitforwindow ['WorldView', 'windowHUD', 'compassAndTeleporterButtons', 'OpenCantripsButton']"))
    print(tokenize_line("p1 walkto XYZ(0, 0, 0) ''"))
    print(tokenize_line("p1 walkto XYZ (0.1, 0, 0) Orient(0) '\ta\t'"))
    print(tokenize_line("[]"))
    print(tokenize_line("''"))
    print(tokenize_line("aa a"))
    print(tokenize_line("mass tozone WizardCity/WC_Ravenwood"))
    print(tokenize_line("except p1:p2 teleport XYZ(0, 0, 0)"))
    print(tokenize_line("except p1:p2 teleport XYZ(, , 0)"))
