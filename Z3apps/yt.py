import json
import requests
import subprocess
import buttoninput
import ui
import kb
import socket
from time import sleep

query = kb.text_input()
MAX_RESULTS = 10
with open("youtube-api-v3.key") as file:
    KEY = file.read()
a = requests.get(f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&maxResults={MAX_RESULTS}&key={KEY}")
res = json.loads(a.text)["items"]
r = []
for i in range(MAX_RESULTS):
    r.append(f"""Title: {res[i]["snippet"]["title"]}\nBy: {res[i]["snippet"]["channelTitle"]}\nAt: {res[i]["snippet"]["publishedAt"]}\nDesc: {res[i]["snippet"]["description"]}""")

index = ui.menu(r, "Select Video")
player = subprocess.Popen(f"""mpv --no-terminal --input-ipc-server=/tmp/mpv.socket https://www.youtube.com/watch?v={res[index]["id"]["videoId"]}""", shell=True)

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
while True:
    try:
        s.connect("/tmp/mpv.socket")
    except Exception as e:
        sleep(1)
    else:
        break

while True:
    button, state = buttoninput.take_input().split()
    state = int(state)

    if button == "MENU" and state:
        s.sendall("quit\n".encode())
        break

    elif button == "DX" and state:
        s.sendall(f"seek {state}0\n".encode())

    # elif button == "DY" and state:


    elif button == "A" and state:
        s.sendall("cycle pause\n".encode())
