import json
import requests
import subprocess
import buttoninput
import ui
import kb
import socket
from time import sleep
from PIL import Image
from io import BytesIO
import numpy as np

MAX_RESULTS = 10
IMGPOS = (318,2)
KEY_FILE = "youtube-api-v3.key"
SPINNER_STATES = ["-", "/", "|", "\\"]
SPINNER_STATES.reverse()
query = ""

def spinner(spinner_string, state):
    if state>=0:
        spinner_string += SPINNER_STATES[state%len(SPINNER_STATES)]
    ui.display.draw_text(spinner_string, ((640-len(spinner_string)*21)//2, 221))


def get_urls():
    global query
    query = kb.text_input(query)
    if query == False:
        return False
    with open(KEY_FILE) as file:
        KEY = file.read()
    a = requests.get(f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&maxResults={MAX_RESULTS}&key={KEY}")
    res = json.loads(a.text)["items"]
    return res


def format_results(res):
    r = []
    for i in range(MAX_RESULTS):
        spinner("Searching ", i)
        time = res[i]["snippet"]["publishedAt"].replace("Z","").split("T")
        r.append(f""" \nOn: {time[0]}\nAt: {time[1]}\n \nTitle: {res[i]["snippet"]["title"]}\n \nBy: {res[i]["snippet"]["channelTitle"]}\n \n{res[i]["snippet"]["description"]}""")

    return r


def load_thumbnails(res):
    imgs = []
    for i in range(MAX_RESULTS):
        spinner("Searching ", i)
        url = res[i]["snippet"]["thumbnails"]["medium"]["url"]
        dim = (res[i]["snippet"]["thumbnails"]["medium"]["width"], res[i]["snippet"]["thumbnails"]["medium"]["height"])
       
        b = np.array(Image.open(BytesIO(requests.get(url).content))).astype(np.uint32)
        imgs.append([np.uint32(0xFF000000) | b[:,:,0] << 16 | b[:,:,1] << 8 | b[:,:,2], dim, IMGPOS])
    
    return imgs


def play_video(url:str):
    spinner("Loading...", -1)
    player = subprocess.Popen(f"""mpv --fs --no-terminal --keep-open --input-ipc-server=/tmp/mpv.socket --ytdl-format="(bestvideo[height<=?480][width<=?640]+bestaudio/best)[vcodec~='^((he|a)vc|h26[45])'] / (bv*+ba/b)" {url}""", shell=True)

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
            player.wait()
            return False

        elif button == "DX" and state:
            s.sendall(f"seek {state*10}\n".encode())

        elif button == "DY" and state:
            s.sendall(f"cycle volume {state*10}\n".encode())

        elif button == "A" and state:
            s.sendall("cycle pause\n".encode())

        elif button == "B" and state:
            s.sendall("quit\n".encode())
            player.wait()
            return True
        
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

page = 0
while True:
    if page < 1:
        res = get_urls()

    if res:
        if page < 1:
            text = format_results(res)
            imgs = load_thumbnails(res)
            index = 0

        page = 1
        index = ui.menu(text, "Result", cur_option=index, images=imgs)
        if index >= 0:
            page = 2
            if not play_video(f"""https://www.youtube.com/watch?v={res[index]["id"]["videoId"]}"""):
                break
            else:
                kb.reset_buffer()
                ui.display.reset_screen()
                page = 1
        
        elif index == -2:
            kb.reset_buffer()
            page = 0

        elif index == -1:
            break
    
    else:
        break
