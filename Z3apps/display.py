from fcntl import ioctl
from mmap import mmap

FB_DEVICE="/dev/fb0"
RES = (640,480) #w,h
RES2 = (RES[0]-1, RES[1]-1)
WHITE = b"\xff"*4
BLACK = b"\x00\x00\x00\xff"
FULL = RES[0]*RES[1]

fb = open(FB_DEVICE, "r+b")
a = mmap(fb.fileno(), 4*RES[0]*RES[1])

fs = (21, 3610)
w,h = 21,38
with open("font32.bin", "rb") as f:
    font = f.read()

fonts = {chr(32+i):font[4*w*h*i:4*w*h*(i+1)] for i in range(127-32)}

def reset_screen():
    # NEXT LINE IS RESOLUTION SPECIFIC
    ioctl(fb, 0x4601, b'\x80\x02\x00\x00\xe0\x01\x00\x00\x80\x02\x00\x00\xc0\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x18\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x00\x00\x00^\x00\x00\x00\x96\x00\x00\x00\x00\x00\x00\x00\xc2\xa2\x00\x00\x1a\x00\x00\x00T\x00\x00\x00\x0c\x00\x00\x00\x1e\x00\x00\x00\x14\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    ioctl(fb, 0x4611, 0)


def draw_screen(b, pos=(0,0)):
    a.seek((pos[0]+pos[1]*RES[0])*4)
    a.write(b)


def draw_part(b, dim=RES2, pos=(0,0)):
    """pos: (x,y) top left of part, dim: (w,h) width and height of part"""
    for i in range(dim[1]):
        a.seek((pos[0]+(pos[1]+i)*RES[0])*4)
        a.write(b[i*dim[0]*4:(i+1)*dim[0]*4])


def inv_part(dim=RES2, pos=(0,0)):
    """pos: (x,y) top left of part, dim: (w,h) width and height of part"""
    for i in range(dim[1]):
        for j in range(dim[0]*4):
            if ((pos[0]+(pos[1]+i)*RES[0])*4 + j+1)%4:
                a[(pos[0]+(pos[1]+i)*RES[0])*4 + j] = 255 - a[(pos[0]+(pos[1]+i)*RES[0])*4 + j]


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
        draw_screen(c, (x0, y0))
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
    dx = dim[0]
    dy = dim[1]
    draw_line(pos, (pos[0],pos[1]+dy), c)
    draw_line(pos, (pos[0]+dx,pos[1]), c)
    draw_line((pos[0]+dx,pos[1]), (pos[0]+dx,pos[1]+dy), c)    
    draw_line((pos[0],pos[1]+dy), (pos[0]+dx,pos[1]+dy), c)

def draw_text(text, pos=(0,0)):
    max_chars = (RES[0]-pos[0])//w
    text = [i[j:j+max_chars] for i in text.split("\n") for j in range(0, len(i), max_chars)]
    for i in range(len(text)):
        t = b""
        for col in range(h):
            for char in text[i]:
                if char in fonts:
                    t+= fonts[char][col*w*4:(col+1)*w*4]
                else:
                    t+= WHITE*w
                # t+=fonts.get(char, WHITE*w*4)[col*w*4:(col+1)*w*4]
        draw_part(t, (w*len(text[i]), h), (pos[0], pos[1]+i*h))


reset_screen()