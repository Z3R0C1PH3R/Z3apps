import display
import buttoninput

def menu():
    pass

def text_area(text, dim=display.RES2, pos=(0,0), padding=(1,1)):
    max_chars = (dim[0]-2*padding[0])//display.w
    text = [i[j:j+max_chars] for i in text.split("\n") for j in range(0, len(i), max_chars)]
    max_lines = (dim[1]-2*padding[1])//display.h
    pages = [text[i:i+max_lines] for i in range(0,len(text), max_lines)]
    num_pages = len(pages)
    cur_page = 0

    display.draw_screen(display.BLACK*display.FULL)
    display.draw_rect(display.WHITE, dim, pos)
    if cur_page < num_pages-1:
        display.draw_screen((display.WHITE*8+display.BLACK*10)*(dim[0]//18), (pos[0], pos[1]+dim[1]))
    display.draw_text("\n".join(pages[cur_page]), (pos[0]+padding[0], pos[1]+padding[1]))

    while True:
        button, state = buttoninput.take_input().split()
        state = int(state)
        if button == "DY" and state:
            cur_page = (cur_page - state) % num_pages
            display.draw_screen(display.BLACK*display.FULL)
            display.draw_rect(display.WHITE, dim, pos)
            if cur_page > 0:
                display.draw_screen((display.WHITE*8+display.BLACK*10)*(dim[0]//18), pos)
            if cur_page < num_pages-1:
                display.draw_screen((display.WHITE*8+display.BLACK*10)*(dim[0]//18), (pos[0], pos[1]+dim[1]))
            display.draw_text("\n".join(pages[cur_page]), (pos[0]+padding[0], pos[1]+padding[1]))

        if (button == "B" or button == "MENU") and state:
            break

    display.draw_screen(display.BLACK*display.FULL)
    return cur_page
