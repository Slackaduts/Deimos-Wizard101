import requests
import os
import sys
import subprocess
import time

tool_name = 'Deimos'
repo_name = tool_name + '-Wizard101'
branch = 'master'


def remove_if_exists(file_name : str, sleep_after : float = 0.1):
	if os.path.exists(file_name):
		os.remove(file_name)
		time.sleep(sleep_after)


def download_file(url: str, file_name : str, delete_previous: bool = False, debug : str = True):
	if delete_previous:
		remove_if_exists(file_name)
	if debug:
		print(f'Downloading {file_name}...')
	with requests.get(url, stream=True) as r:
		with open(file_name, 'wb') as f:
			for chunk in r.iter_content(chunk_size=128000):
				f.write(chunk)


remove_if_exists(f'{tool_name}.exe')
download_file(url=f"https://raw.githubusercontent.com/Slackaduts/{repo_name}/{branch}/{tool_name}.exe", file_name=f'{tool_name}.exe', delete_previous=True)
time.sleep(0.1)
subprocess.Popen(f'{tool_name}.exe')
sys.exit()