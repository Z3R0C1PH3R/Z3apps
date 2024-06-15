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
    r.append(f""" \nTitle: {res[i]["snippet"]["title"]}\n \nBy: {res[i]["snippet"]["channelTitle"]}\nOn: {" At: ".join(res[i]["snippet"]["publishedAt"].split("T")).replace("Z","")}\n \n{res[i]["snippet"]["description"]}""")

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
        s.sendall(f"seek {state*10}\n".encode())

    elif button == "DY" and state:
        s.sendall(f"cycle volume {state*10}\n".encode())

    elif button == "A" and state:
        s.sendall("cycle pause\n".encode())

    # elif button == "B" and state:
    
    elif button == "X" and state:
        s.sendall("cycle mute\n".encode())

    elif button == "Y" and state:
        s.sendall("show-progress\n".encode())

    elif button == "L1" and state:
        s.sendall(f"seek -10 relative-percent\n".encode())

    elif button == "R1" and state:
        s.sendall(f"seek 10 relative-percent\n".encode())

    elif button == "START" and state:
        s.sendall(f"seek 100 absolute-percent\n".encode())

    elif button == "SELECT" and state:
        s.sendall(f"seek 0 absolute\n".encode())