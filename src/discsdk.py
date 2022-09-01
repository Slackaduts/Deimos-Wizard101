import json
import struct

from enum import IntEnum

import win32pipe, win32file


discord_base_pipe_path = "\\\\?\\pipe\\discord-ipc-"
app_id = 1000159655357587566
rpc_version = 1


class Opcodes(IntEnum):
	Handshake = 0
	Frame = 1
	Close = 2
	Ping = 3
	Pong = 4


def connect():
	handle = None
	for i in range(10):
		path = discord_base_pipe_path + str(i)

		try:
			handle = win32file.CreateFile(
				path,
				win32file.GENERIC_READ | win32file.GENERIC_WRITE,
				0,
				None,
				win32file.OPEN_EXISTING,
				0,
				None
			)
			win32pipe.SetNamedPipeHandleState(handle, win32pipe.PIPE_READMODE_BYTE, None, None)
			break
		except:
			pass

	return handle

def close(handle):
	win32file.CloseHandle(handle)

def serialize_message(opcode, jsondata) -> bytearray:
	result = bytearray()
	data = json.dumps(jsondata).encode()

	result += struct.pack("<L", int(opcode))
	result += struct.pack("<L", len(data))
	result += data

	return result

def parse_message(msg):
	opcode = Opcodes(struct.unpack("<L", msg[0:4])[0])
	data_len = struct.unpack("<L", msg[4:8])[0]
	data = msg[8:8+data_len].decode()
	return json.loads(data)

def send(handle, data):
	win32file.WriteFile(handle, data)

def recv(handle):
	data = win32file.ReadFile(handle, 65536)
	if data[0] == 0:
		return parse_message(data[1])

shake = serialize_message(
	Opcodes.Handshake,
	{
		"v": rpc_version,
		"client_id": str(app_id)
	}
)
