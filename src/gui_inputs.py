import math


def param_input(input: str, default):
	# Logic for interpreting number field inputs in the Deimos gui.
	# Arguments can be chained together, always seperated by spaces.
	# If you want to add 90 degrees, you would do "+ rad 90". This converts the 90 to radians, then adds it to the current value.
	# These arguments can also accept numbers, like "* 2 + 5" would add 5, then multiply by 2.
	# Some arguments can also be used alone, like "pi" and regular numbers or operaters like "+", which would add itself.

	# Insane example: "rad + 5 * 3 / 15 ** 2 deg pi"
	# This ludicrous example would set to pi, convert it to degrees, square it, divide by 15, multiply by 3, add 5, then convert back to radians. You should never do this, but it can be done.

	# Note: Keep in mind what values you're actually setting. Rotational values of yaw, roll, and pitch use radians, while everything else uses distances. 
	# Places where names can be entered are not compatible with this system for obvious reasons.
	adjusted_param = float(default)
	if ' ' in input:
		symbol_params = input.split(' ')
		symbol_params.reverse()
		for i, param in enumerate(symbol_params):
			match param:
				case '+':
					adjusted_param += prev_param

				case '-':
					adjusted_param = prev_param - adjusted_param

				case '*':
					adjusted_param *= prev_param

				case '/':
					adjusted_param = prev_param / adjusted_param

				case '**':
					adjusted_param = adjusted_param ** prev_param

				case 'sqrt':
					adjusted_param = math.sqrt(adjusted_param)

				case 'rad':
					if i == len(symbol_params) - 1:
						adjusted_param = math.radians(prev_param)
					else:
						prev_param = math.radians(prev_param)

				case 'deg':
					if i == len(symbol_params) - 1:
						adjusted_param = math.degrees(prev_param)
					else:
						prev_param = math.degrees(prev_param)

				case 'abs':
					if i == len(symbol_params) - 1:
						adjusted_param = abs(prev_param)
					else:
						prev_param = abs(prev_param)

				case 'sin':
					if i == len(symbol_params) - 1:
						adjusted_param = math.sin(prev_param)
					else:
						prev_param = math.sin(prev_param)

				case 'cos':
					if i == len(symbol_params) - 1:
						adjusted_param = math.cos(prev_param)
					else:
						prev_param = math.cos(prev_param)

				case 'tan':
					if i == len(symbol_params) - 1:
						adjusted_param = math.tan(prev_param)
					else:
						prev_param = math.tan(prev_param)

				case 'pi':
					prev_param = math.pi

				case 'tau':
					prev_param = math.tau

				case 'e':
					prev_param = math.e

				case 'floor':
					if i == len(symbol_params) - 1:
						adjusted_param = math.floor(prev_param)
					else:
						prev_param = math.floor(prev_param)

				case 'ceiling':
					if i == len(symbol_params) - 1:
						adjusted_param = math.ceil(prev_param)
					else:
						prev_param = math.ceil(prev_param)

				case _:
					prev_param = float(param)

	elif input:
		match input:
			case '+':
				return adjusted_param * 2

			case '*':
				return adjusted_param ** 2

			case 'sqrt':
				return math.sqrt(adjusted_param)

			case 'rad':
				return math.radians(adjusted_param)

			case 'deg':
				return math.degrees(adjusted_param)

			case 'abs':
				return abs(adjusted_param)

			case 'sin':
				return math.sin(adjusted_param)

			case 'cos':
				return math.cos(adjusted_param)

			case 'tan':
				return math.tan(adjusted_param)

			case 'pi':
				return math.pi

			case 'tau':
				return math.tau

			case 'e':
				return math.e

			case 'floor':
				return math.floor(adjusted_param)

			case 'ceiling':
				return math.ceil(adjusted_param)

			case _:
				adjusted_param = float(input)

	return adjusted_param