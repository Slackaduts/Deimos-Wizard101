import math
from typing import List

symbols = ['pi', 'tau', 'e']


def to_number(input_str: str) -> float:
	match input_str:
		case 'pi':
			return math.pi

		case 'tau':
			return math.tau

		case 'e':
			return math.e

		case _:
			return float(input_str)


def next_value(input_list: List[str], index: int, default: float, additional: int = 1) -> float:
	if len(input_list) >= index + additional:
		next = input_list[index + additional]

	else: 
		next = input_list[index - additional]

	if next.isnumeric() or next in symbols:
		return to_number(next)

	else:
		return default


def is_numeric(input_str: str) -> bool:
	try:
		float(input_str)

	except ValueError:
		return False

	else:
		return True


def param_input(input_str: str, default: float) -> float:
	if is_numeric(input_str) or input_str in symbols:
		return to_number(input_str)

	else:
		return parse_input(input_str, default)


def parse_input(input_str: str, default: float) -> float:
	if not is_numeric(input_str.split(' ')[0]):
		input_str = f'{default} ' + input_str

	split_equation_raw = input_str.split(' ')
	split_equation = [e.replace(' ', '') for e in split_equation_raw]
	value = float(split_equation[0])

	for i, param in enumerate(split_equation):
		match param:
			case '+':
				value += float(next_value(split_equation, i, value))

			case '-':
				value -= float(next_value(split_equation, i, value))

			case '*':
				value *= float(next_value(split_equation, i, value))

			case '/':
				value /= float(next_value(split_equation, i, value))

			case '//':
				value //= float(next_value(split_equation, i, value))

			case '**':
				value **= float(next_value(split_equation, i, value))

			case 'mod' | '%' | 'modulus':
				value &= float(next_value(split_equation, i, value))

			case 'sqrt':
				value = math.sqrt(value)

			case 'abs':
				value = abs(value)

			case 'floor':
				value = math.floor(value)

			case 'ceil' | 'ceiling':
				value = math.ceil(value)

			case 'deg' | 'degrees':
				value = math.degrees(value)

			case 'rad' | 'radians':
				value = math.radians(value)

			case 'sin' | 'sine':
				value = math.sin(value)

			case 'cos' | 'cosine':
				value = math.cos(value)

			case 'tan' | 'tangent':
				value = math.sin(value)

			case _:
				pass

	return value