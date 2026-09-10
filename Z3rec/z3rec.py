#!/usr/bin/env python3
"""Record what the handheld is playing, and save it into the Music folder.

Recording is not something you start and stop while a game runs, because the
game owns the screen and Z3rec cannot be in front of it. Instead you turn
recording on once, and from then on whatever plays is captured to a buffer on
the card. Come back here afterwards and save as much of it as you want.

The buffer only ever holds the current session: the ALSA plugin doing the
capture starts its file again every time the sound card is opened, which is
once per game launch. See audiotap.py for what is actually going on underneath.
"""

import json
import os
import sys
import time

import audiotap
import padreader
import recorder

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, "settings.json")

COLS, ROWS = 30, 12       # 640x480 at the 21x38 font display.py uses

LENGTHS = [30, 60, 120, 300, 600]

DEFAULTS = {"format": "mp3", "bitrate": "192k", "mono": False, "last": 60}


def load_settings():
    values = dict(DEFAULTS)
    try:
        with open(SETTINGS) as f:
            saved = json.load(f)
        for key in DEFAULTS:
            if key in saved:
                values[key] = saved[key]
    except (OSError, ValueError):
        pass
    return values


def save_settings(values):
    try:
        with open(SETTINGS, "w") as f:
            json.dump(values, f, indent=2)
            f.write("\n")
    except OSError:
        pass


# ------------------------------------------------------------------ formatting


def clock(seconds):
    seconds = int(seconds)
    if seconds >= 3600:
        return "%d:%02d:%02d" % (seconds // 3600, seconds // 60 % 60, seconds % 60)
    return "%d:%02d" % (seconds // 60, seconds % 60)


def size(n):
    if n >= 1 << 30:
        return "%.1fG" % (n / float(1 << 30))
    if n >= 1 << 20:
        return "%.0fM" % (n / float(1 << 20))
    return "%.0fK" % (n / 1024.0)


# --------------------------------------------------------------------- screen


class Screen:
    """Framebuffer text output, with a plain-text fallback into the logfile."""

    def __init__(self):
        try:
            import display
            self.display = display
        except Exception as e:
            print("framebuffer unavailable (%s)" % e, file=sys.stderr)
            self.display = None

    def draw(self, lines):
        text = "\n".join(lines[:ROWS])
        print(" | ".join(l for l in lines if l), file=sys.stderr)
        if not self.display:
            return
        try:
            self.display.clear()
            self.display.draw_text(text)
        except Exception:
            self.display = None

    def clear(self):
        if self.display:
            try:
                self.display.clear()
            except Exception:
                pass

    def note(self, title, body, buttons=None, wait=True):
        """A full-screen message, optionally waiting for a button."""
        lines = [title, ""] + list(body)
        if wait:
            lines += [""] * max(0, ROWS - 2 - len(body) - 1)
            lines.append("Press any button")
        self.draw(lines)
        if not wait:
            return None
        if buttons is not None:
            return buttons.next(timeout=None)
        with padreader.ButtonEvents(grab=True) as own:
            return own.next(timeout=None)

    def progress(self, title, name):
        """Returns a callback that redraws a bar as a save runs."""
        state = {"shown": -1}

        def update(fraction):
            percent = int(fraction * 100)
            if percent == state["shown"]:
                return
            state["shown"] = percent
            filled = int(fraction * 20)
            self.draw([title, "", name, "",
                       "[" + "#" * filled + " " * (20 - filled) + "]", "",
                       "%d%%" % percent])

        return update


# ----------------------------------------------------------------- the screens


def status_line(on, seconds):
    if not on:
        return "Recording off"
    if seconds < 1:
        # Nothing is captured in the launcher or in here, only inside a game, so
        # an empty buffer is the normal state to find this screen in.
        return "Recording on, play a game"
    return "Recording on   " + clock(seconds)


def main_menu(screen, buttons, values):
    """The top level. Returns when the user exits."""
    selected = 0
    while True:
        on = audiotap.installed()
        seconds = audiotap.buffer_seconds() if on else 0
        saved = len(recorder.recordings())
        quality = values["format"]
        if values["format"] in recorder.LOSSY:
            quality += " " + values["bitrate"]

        items = [
            ("Save all", clock(seconds) + " as " + quality if seconds >= 1
             else "Nothing recorded yet"),
            ("Save last " + clock(values["last"]),
             clock(min(values["last"], seconds)) + " as " + quality if seconds >= 1
             else "Nothing recorded yet"),
            ("Clear buffer", size(audiotap.card_free()) + " free on the card"),
            ("Recording off" if on else "Recording on",
             "Put the stock audio back" if on else "Tap the speaker output"),
            ("Recordings", "%d saved in Music" % saved if saved else "Nothing saved yet"),
            ("Settings", "Format, quality, length"),
            ("Exit", ""),
        ]
        if not on:
            items[0] = (items[0][0], "Turn recording on first")
            items[1] = (items[1][0], "Turn recording on first")

        lines = ["Z3rec", status_line(on, seconds), ""]
        for i, (title, _) in enumerate(items):
            lines.append(("> " if i == selected else "  ") + title)
        lines.append(items[selected][1])
        lines.append("D-pad + A,  MENU quits")
        screen.draw(lines)

        pressed = buttons.next(timeout=None)
        if pressed in ("DOWN", "RIGHT"):
            selected = (selected + 1) % len(items)
        elif pressed in ("UP", "LEFT"):
            selected = (selected - 1) % len(items)
        elif pressed in ("MENU",):
            return
        elif pressed == "B":
            selected = len(items) - 1
        elif pressed == "A":
            if selected == 0 and on:
                do_save(screen, buttons, values, None)
            elif selected == 1 and on:
                do_save(screen, buttons, values, values["last"])
            elif selected == 2:
                ok, message = audiotap.clear_buffer()
                screen.note("Clear buffer", [message], buttons)
            elif selected == 3:
                toggle_recording(screen, buttons, on)
            elif selected == 4:
                recordings_screen(screen, buttons)
            elif selected == 5:
                settings_screen(screen, buttons, values)
            elif selected == 6:
                return


def toggle_recording(screen, buttons, on):
    screen.draw(["Recording", "", "Working..."])
    ok, message = audiotap.remove() if on else audiotap.install()
    body = [message[i:i + COLS] for i in range(0, len(message), COLS)]
    if ok and not on:
        body += ["", "Only sound from inside a", "game is caught. Nothing is", "recorded in the launcher or", "in here."]
    screen.note("Recording off" if on else "Recording on", body, buttons)


def do_save(screen, buttons, values, seconds):
    if audiotap.buffer_is_live():
        answer = screen.note("Still playing", [
            "Something is playing into",
            "the buffer right now, so it",
            "may grow while saving.",
            "", "A to save anyway, B to stop"], buttons)
        if answer != "A":
            return

    peak = audiotap.buffer_peak()
    if peak is not None and peak < 0.002:
        answer = screen.note("Sounds silent", [
            "The last few seconds of the",
            "buffer are silence. Was the",
            "game running with sound?",
            "", "A to save anyway, B to stop"], buttons)
        if answer != "A":
            return

    name = "Z3rec-" + time.strftime("%Y-%m-%d-%H%M") + "." + values["format"]
    ok, result = recorder.save(seconds=seconds, fmt=values["format"],
                               bitrate=values["bitrate"], mono=values["mono"],
                               progress=screen.progress("Saving", name))
    if not ok:
        screen.note("Could not save", [result[i:i + COLS] for i in range(0, len(result), COLS)],
                    buttons)
        return

    try:
        written = os.path.getsize(result)
    except OSError:
        written = 0
    screen.note("Saved", [os.path.basename(result), "", "into Music,  " + size(written), "",
                          "The buffer is untouched, so", "you can save more of it."], buttons)


def settings_screen(screen, buttons, values):
    formats = recorder.available_formats()
    if values["format"] not in formats:
        values["format"] = formats[0]
    selected = 0

    def step(options, current, delta):
        return options[(options.index(current) + delta) % len(options)]

    while True:
        lossy = values["format"] in recorder.LOSSY
        rows = [
            ("Format", values["format"]),
            ("Quality", values["bitrate"] if lossy else "-"),
            ("Channels", "mono" if values["mono"] else "stereo"),
            ("Save last", clock(values["last"])),
            ("Back", ""),
        ]
        lines = ["Settings", ""]
        for i, (label, value) in enumerate(rows):
            prefix = "> " if i == selected else "  "
            lines.append((prefix + "%-10s %s" % (label, value)).rstrip())
        lines += [""] * max(0, ROWS - 4 - len(rows))
        lines.append("Left/Right changes it")
        lines.append("B goes back")
        screen.draw(lines)

        pressed = buttons.next(timeout=None)
        if pressed == "DOWN":
            selected = (selected + 1) % len(rows)
        elif pressed == "UP":
            selected = (selected - 1) % len(rows)
        elif pressed in ("B", "MENU"):
            save_settings(values)
            return
        elif pressed == "A" and selected == 4:
            save_settings(values)
            return
        elif pressed in ("LEFT", "RIGHT", "A"):
            delta = -1 if pressed == "LEFT" else 1
            if selected == 0:
                values["format"] = step(formats, values["format"], delta)
                if len(formats) == 1:
                    screen.note("Format", [
                        "Only WAV is available:",
                        "ffmpeg is missing or will",
                        "not run on this firmware."], buttons)
            elif selected == 1 and lossy:
                values["bitrate"] = step(recorder.BITRATES, values["bitrate"], delta)
            elif selected == 2:
                values["mono"] = not values["mono"]
            elif selected == 3:
                values["last"] = step(LENGTHS, values["last"], delta)
            save_settings(values)


def recordings_screen(screen, buttons):
    selected = 0
    top = 0
    visible = 7
    while True:
        found = recorder.recordings()
        if not found:
            screen.note("Recordings", ["Nothing saved yet.", "",
                                       "Saved files go into the",
                                       "Music folder on the card."], buttons)
            return
        selected = min(selected, len(found) - 1)
        top = min(max(top, selected - visible + 1), max(0, len(found) - visible))
        top = max(0, min(top, selected))

        lines = ["Recordings", ""]
        for i in range(top, min(top + visible, len(found))):
            name = found[i][0]
            lines.append(("> " if i == selected else "  ") + name[:COLS - 2])
        lines += [""] * max(0, ROWS - 4 - (min(top + visible, len(found)) - top))
        lines.append("%d of %d,  %s" % (selected + 1, len(found), size(found[selected][1])))
        lines.append("A deletes,  B goes back")
        screen.draw(lines)

        pressed = buttons.next(timeout=None)
        if pressed == "DOWN":
            selected = (selected + 1) % len(found)
        elif pressed == "UP":
            selected = (selected - 1) % len(found)
        elif pressed in ("B", "MENU"):
            return
        elif pressed == "A":
            name = found[selected][0]
            answer = screen.note("Delete?", [name[:COLS], "", "A deletes it, B keeps it"], buttons)
            if answer == "A":
                recorder.delete(name)


# ----------------------------------------------------------------------- entry


def main():
    if os.geteuid() != 0:
        print("Z3rec must run as root", file=sys.stderr)
        return 1

    screen = Screen()
    values = load_settings()

    # An installed tap with nowhere to write means no sound at all, so say so
    # loudly rather than letting the handheld come up silent.
    if audiotap.installed() and not audiotap.buffer_ready():
        with padreader.ButtonEvents(grab=True) as buttons:
            answer = screen.note("Problem", [
                "Recording is on but the",
                "buffer folder is missing,",
                "which leaves the handheld",
                "with no sound at all.",
                "", "A turns recording off"], buttons)
            if answer == "A":
                audiotap.remove()

    with padreader.ButtonEvents(grab=True) as buttons:
        main_menu(screen, buttons, values)

    save_settings(values)
    screen.clear()
    return 0


if __name__ == "__main__":
    sys.exit(main())
