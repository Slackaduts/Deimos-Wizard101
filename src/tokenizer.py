
class TokenizerError(Exception):
    pass


def tokenize(l: str) -> list[str]:
    result = []

    i = 0

    in_brackets = False
    bracket_list = []

    def error(msg):
        raise TokenizerError(msg + f"\nData: {l}")

    def add_token(s: str, literal=False, allow_empty=False):
        nonlocal result
        nonlocal bracket_list
        nonlocal in_brackets
        if not literal:
            s = s.strip()
        if len(s) == 0 and not allow_empty:
            return
        if in_brackets:
            bracket_list.append(s)
        else:
            result.append(s)

    def advance(off = 1):
        nonlocal i
        i += off

    def can_read(off = 0) -> bool:
        nonlocal i
        nonlocal l
        return i + off < len(l)

    def read() -> str:
        nonlocal i
        nonlocal l
        if can_read():
            s = l[i]
            advance()
            return s

    def read_until(c: str, illegal_chars = ['#']):
        assert len(c) == 1
        nonlocal i
        nonlocal l
        res = read()
        while can_read():
            x = read()
            res += x
            if x == c:
                break
        for illegal in illegal_chars:
            if illegal in res:
                error(f"Found {illegal} at illegal position")

        if len(res) < 2 or res[-1] != c:
            error("Could not find closing " + c)

        return res

    word = ""
    while can_read():
        c = l[i]
        
        match c:
            case '#':
                break        
            case '(':
                add_token(word + read_until(')'))
                word = ""
            case ')':
                error("Closing ) without opening (")
            case '[':
                if in_brackets:
                    error("Nested [] are not allowed")
                in_brackets = True
                advance()
            case ']':
                if not in_brackets:
                    error("Found closing ] without opening [")
                add_token(word)
                word = ""
                result.append(bracket_list)
                bracket_list = []
                in_brackets = False
                advance()
            case '"' | "'":
                s = read_until(c, illegal_chars=[])[1:-1]
                add_token(s, literal=True, allow_empty=True)
            case _:
                if c == ',' or c.isspace():
                    add_token(word)
                    word = ""
                    advance()
                else:
                    word += read()
    
    if in_brackets:
        error("Could not find closing ]")
    add_token(word)

    return result


if __name__ == "__main__":
    print(tokenize("\tglideTo	\t X\tYZ\t(0, 0, 0), Or\tient(90, 0, 0)"))
    print(tokenize("p1 walkto XYZ(1,) [a, '2'] 'test'"))
    print(tokenize("p1 waitforwindow ['WorldView', 'windowHUD', 'compassAndTeleporterButtons', 'OpenCantripsButton']"))
    print(tokenize("p1 walkto XYZ(0, 0, 0) ''"))
    print(tokenize("p1 walkto XYZ (0, 0, 0) Orient(0) '\ta\t'"))
    print(tokenize("[]"))
    print(tokenize("''"))
    print(tokenize("aa a"))
