# These mappings are for RG35XX+

mappings = {"0003001100ffffffff":"DY 1",
            "000300110001000000":"DY -1",
            "000300110000000000":"DY 0",
            "0003001000ffffffff":"DX -1",
            "000300100001000000":"DX 1",
            "000300100000000000":"DX 0",
            "000100300101000000":"A 1",
            "000100300100000000":"A 0",
            "000100310101000000":"B 1",
            "000100310100000000":"B 0",
            "000100320101000000":"Y 1",
            "000100320100000000":"Y 0",
            "000100330101000000":"X 1",
            "000100330100000000":"X 0",
            "000100340101000000":"L1 1",
            "000100340100000000":"L1 0",
            "0001003a0101000000":"L2 1",
            "0001003a0100000000":"L2 0",
            "000100350101000000":"R1 1",
            "000100350100000000":"R1 0",
            "0001003b0101000000":"R2 1",
            "0001003b0100000000":"R2 0",
            "000100370101000000":"START 1",
            "000100370100000000":"START 0",
            "000100360101000000":"SELECT 1",
            "000100360100000000":"SELECT 0",
            "000100730001000000":"V+ 1",
            "000100730000000000":"V+ 0",
            "000100720001000000":"V- 1",
            "000100720000000000":"V- 0",
            "000100380101000000":"MENU 1",
            "000100380100000000":"MENU 0",
            "000100620101000000":"MENUF 1",
            "000100620100000000":"MENUF 0"}

def take_input(a=open("/dev/input/event1", "rb")):
    """Returns the key pressed according to above table, Blocks until keypress"""
    r = "000000000000000000"
    while r == "000000000000000000":
        r = a.read(16).hex()[14:32]
    return mappings.get(r, "UNKNOWN")


if __name__ == "__main__":
    import os
    while True:
        m = take_input()
        print(m)
        os.system(f'./display.sh "{m}"')
