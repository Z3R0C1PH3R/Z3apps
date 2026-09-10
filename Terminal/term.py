import threading
import subprocess
import time
import ui
import kb

LOCK = True
out = []
err = []
list_lock = False
def t(p,l):
    while LOCK:
        line = p.readline()
        while list_lock:
            time.sleep(0.1)
        l.append(line)

process = subprocess.Popen(['/bin/bash'], shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, bufsize=0)
x1 = threading.Thread(target=t, args=(process.stdout,out))
x2 = threading.Thread(target=t, args=(process.stderr,err))

x1.start()
x2.start()

while LOCK:
    kb.reset_buffer()
    i = kb.text_input()
    if i == False or i == "exit":
        LOCK = list_lock = False
        break
    process.stdin.write(i+"\n")
    time.sleep(1)
    list_lock = True
    ol = ["OUTPUT:\n"] + out.copy() + ["ERROR:\n"] + err.copy()
    out.clear()
    err.clear()
    list_lock = False
    ui.text_area("".join(ol))

process.terminate()
x1.join()
x2.join()