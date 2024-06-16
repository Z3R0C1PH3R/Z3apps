import json
import requests
import subprocess
import buttoninput
import ui
import kb
import socket
from time import sleep

MAX_RESULTS = 10
IMGPOS = (318,2)

query = kb.text_input()
if query == False:
    exit()
with open("youtube-api-v3.key") as file:
    KEY = file.read()
a = requests.get(f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&maxResults={MAX_RESULTS}&key={KEY}")
res = json.loads(a.text)["items"]
r = []
imgs = []
for i in range(MAX_RESULTS):
    searching_string = "Searching" + "." * i
    ui.display.draw_text(searching_string, ((640-len(searching_string)*21)//2, 221))
    time = res[i]["snippet"]["publishedAt"].replace("Z","").split("T")
    r.append(f""" \nOn: {time[0]}\nAt: {time[1]}\n \nTitle: {res[i]["snippet"]["title"]}\n \nBy: {res[i]["snippet"]["channelTitle"]}\n \n{res[i]["snippet"]["description"]}""")

    url = res[i]["snippet"]["thumbnails"]["medium"]["url"]
    dim = (res[i]["snippet"]["thumbnails"]["medium"]["width"], res[i]["snippet"]["thumbnails"]["medium"]["height"])
    with open("/tmp/ytthumb.jpg", "wb") as f:
        f.write(requests.get(url).content)
    
    converter = subprocess.Popen(f"convert /tmp/ytthumb.jpg -format BGRA /tmp/ytthumb.bgra", shell=True)
    converter.wait()

    with open("/tmp/ytthumb.bgra", "rb") as f:
        imgs.append([f.read(), dim, IMGPOS])

index = ui.menu(r, "Result", images=imgs)
if index == -1:
    quit()
ui.display.draw_text("Loading...", (215, 221))
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