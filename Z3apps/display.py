from fcntl import ioctl
from mmap import mmap
import numpy as np

FB_DEVICE="/dev/fb0"
RES = (640,480) #w,h
RES2 = (RES[0]-1, RES[1]-1)
WHITE = np.uint32(0xFFFFFFFF)
BLACK = np.uint32(0xFF000000)
FULL = RES[0]*RES[1]

fb = open(FB_DEVICE, "r+b")
a = np.frombuffer(mmap(fb.fileno(), 4*FULL), dtype=np.uint32).reshape(RES[::-1])

fs = (21, 3610)
w,h = 21,38
with open("font32.bin", "rb") as f:
    font = np.frombuffer(f.read(), dtype=np.uint32).reshape(-1, h, w)

fonts = {chr(32+i):font[i] for i in range(127-32)}

def reset_screen():
    # NEXT LINE IS RESOLUTION SPECIFIC
    ioctl(fb, 0x4601, b'\x80\x02\x00\x00\xe0\x01\x00\x00\x80\x02\x00\x00\xc0\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x18\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x00\x00\x00^\x00\x00\x00\x96\x00\x00\x00\x00\x00\x00\x00\xc2\xa2\x00\x00\x1a\x00\x00\x00T\x00\x00\x00\x0c\x00\x00\x00\x1e\x00\x00\x00\x14\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    ioctl(fb, 0x4611, 0)


def draw_screen(b, pos=(0,0)):
    a.ravel()[pos[0]+pos[1]*RES[0]:len(b)+pos[0]+pos[1]*RES[0]] = b 


def draw_part(b, dim=RES2, pos=(0,0)):
    """pos: (x,y) top left of part, dim: (w,h) width and height of part"""
    a[pos[1]:pos[1]+dim[1], pos[0]:pos[0]+dim[0]] = b[:dim[0]*dim[1]].reshape(dim[::-1])


def inv_part(dim=RES2, pos=(0,0)):
    """pos: (x,y) top left of part, dim: (w,h) width and height of part"""
    a[pos[1]:pos[1]+dim[1], pos[0]:pos[0]+dim[0]] = ~a[pos[1]:pos[1]+dim[1], pos[0]:pos[0]+dim[0]] | BLACK


def draw_line(p1, p2, c):
    """Draws a line from p1(x,y) to p2(x,y) of color c(4)"""
    x0, y0 = p1
    x1, y1 = p2
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    error = dx + dy
    if dy == 0:
        draw_screen(c*dx, (min(p1[0],p2[0]) ,p1[1]))
    if dx == 0:
        draw_part(c*-dy, (1,-dy), (p1[0] ,min(p1[1],p2[1])))
    while True:
        a[y0, x0] = c
        if x0 == x1 and y0 == y1: break
        e2 = 2 * error
        if e2 >= dy:
            if x0 == x1: break
            error = error + dy
            x0 = x0 + sx
        if e2 <= dx:
            if y0 == y1: break
            error = error + dx
            y0 = y0 + sy


def draw_rect(c=WHITE, dim=RES2, pos=(0,0)):
    """Draws a line, pos:(x,y) top left, p2:(x,y) top right of color c(4)"""
    a[pos[1]:pos[1]+dim[1]+1, pos[0]] = c
    a[pos[1]:pos[1]+dim[1]+1, pos[0]+dim[0]] = c
    a[pos[1], pos[0]:pos[0]+dim[0]+1] = c
    a[pos[1]+dim[1], pos[0]:pos[0]+dim[0]+1] = c

def draw_text(text, pos=(0,0)):
    max_chars = (RES[0]-pos[0])//w
    lines = [line[i:i+max_chars] for line in text.split("\n") for i in range(0, len(line), max_chars)]
    for i, line in enumerate(lines):
        t = np.hstack([fonts.get(char, np.full((h, w), WHITE)) for char in line])
        draw_part(t, (w*len(line), h), (pos[0], pos[1]+i*h))

reset_screen()