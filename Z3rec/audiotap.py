"""The ALSA playback tap: how a handheld with no capture device records itself.

Every PCM this kernel exposes is playback only. There is no /dev/snd/pcmC0D0c to
open, and snd-aloop is not built for this kernel, so there is nothing to record
*from* in the usual sense. Z3rec gets around that by tapping the playback side
instead: alsa-lib's "file" plugin sits in front of the real sound card, passes
every sample through untouched so the game still comes out of the speaker, and
writes a second copy to a file.

The tap takes over "default" rather than adding a device under its own name,
because the stock RetroArch reads its audio_device setting and then opens
"default" regardless of what it says. Taking over "default" also means the tap
catches anything else that plays through ALSA, not only RetroArch.

Two things follow from how the plugin works, and the rest of Z3rec is shaped
around them:

  * A program only picks the tap up when it opens the sound card, so turning
    recording on under a running game does nothing until the game is relaunched.
  * The plugin truncates its file every time the card is opened, so the buffer
    always holds the current session and nothing older.
"""

import os
import re
import subprocess

ASOUND = "/etc/asound.conf"
BACKUP = "/etc/asound.conf.z3rec-backup"
MARKER = "z3out"

# The buffer lives on the card rather than the root filesystem. Root has under
# two gigabytes spare on a stock install and filling it breaks the system, while
# the card has room for hours and is only used for content anyway. It is also
# where the saved recordings end up, so nothing has to cross filesystems.
BUFFER_DIR = "/mnt/mmc/.z3rec"
BUFFER = os.path.join(BUFFER_DIR, "buffer.wav")
MUSIC = "/mnt/mmc/Music"

TAP_BLOCK = """
# --- added by Z3rec. To undo by hand: delete this block, and rename the
# --- "pcm.z3out" above back to "pcm.!default".
pcm.!default {
	type file
	slave.pcm "z3out"
	file "%s"
	format wav
}
""" % BUFFER

_DEFAULT_RE = re.compile(r"^pcm\.!default(\s*){", re.M)


def read_conf():
    try:
        with open(ASOUND) as f:
            return f.read()
    except OSError:
        return None


def installed():
    conf = read_conf()
    return bool(conf) and MARKER in conf


def alsa_parses():
    """True if alsa-lib still understands the config and can see both devices.

    aplay only parses the configuration here, it does not open the card, so this
    is safe to call with a game running.
    """
    try:
        out = subprocess.run(["aplay", "-L"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return True  # No aplay to check with; assume the config is fine.
    names = out.stdout.split()
    return out.returncode == 0 and "z3out" in names and "default" in names


def buffer_ready():
    """Make sure the tap has somewhere to write before anything depends on it.

    This matters more than it looks: if the plugin cannot open its file then the
    PCM open fails outright, and the handheld has no sound at all until the tap
    is removed.
    """
    try:
        os.makedirs(BUFFER_DIR, exist_ok=True)
        probe = os.path.join(BUFFER_DIR, ".probe")
        with open(probe, "wb") as f:
            f.write(b"z3")
        os.unlink(probe)
        return True
    except OSError:
        return False


def install():
    """Put the tap in front of the stock default. Returns (ok, message)."""
    conf = read_conf()
    if conf is None:
        return False, "No %s on this handheld." % ASOUND
    if MARKER in conf:
        return True, "Recording was already on."
    if not _DEFAULT_RE.search(conf):
        return False, "No pcm.!default in %s to put the tap in front of." % ASOUND
    if not buffer_ready():
        return False, "Cannot write to %s." % BUFFER_DIR

    if not os.path.exists(BACKUP):
        try:
            with open(BACKUP, "w") as f:
                f.write(conf)
        except OSError as e:
            return False, "Cannot save a backup: %s" % e

    # Rename the stock default out of the way rather than replacing it, so
    # whatever the firmware does on open (this one flips a pile of mixer
    # switches) still happens exactly as before, just behind the tap.
    patched = _DEFAULT_RE.sub(r"pcm.z3out\1{", conf, count=1) + TAP_BLOCK
    try:
        with open(ASOUND, "w") as f:
            f.write(patched)
    except OSError as e:
        return False, "Cannot write %s: %s" % (ASOUND, e)

    if not alsa_parses():
        remove()
        return False, "ALSA rejected the change, so it was put back."
    return True, "Recording is on. Relaunch your game for it to be caught."


def remove():
    """Put the stock configuration back. Returns (ok, message)."""
    conf = read_conf()
    if conf is not None and MARKER not in conf:
        return True, "Recording was already off."

    if os.path.exists(BACKUP):
        try:
            with open(BACKUP) as f:
                stock = f.read()
            with open(ASOUND, "w") as f:
                f.write(stock)
        except OSError as e:
            return False, "Cannot restore %s: %s" % (ASOUND, e)
        return True, "Stock audio is back. Relaunch your game."

    # No backup, so undo the two edits directly.
    if conf is None:
        return False, "No %s to fix." % ASOUND
    undone = conf.split("\n# --- added by Z3rec")[0].rstrip() + "\n"
    undone = re.sub(r"^pcm\.z3out(\s*){", r"pcm.!default\1{", undone, count=1, flags=re.M)
    try:
        with open(ASOUND, "w") as f:
            f.write(undone)
    except OSError as e:
        return False, "Cannot write %s: %s" % (ASOUND, e)
    return True, "Stock audio is back. Relaunch your game."


# ------------------------------------------------------------------ the buffer


def buffer_size():
    try:
        return os.path.getsize(BUFFER)
    except OSError:
        return 0


def buffer_format():
    """(channels, rate, bits) from the header the tap wrote, with a fallback."""
    try:
        with open(BUFFER, "rb") as f:
            head = f.read(44)
        if len(head) == 44 and head[:4] == b"RIFF":
            import struct
            ch = struct.unpack("<H", head[22:24])[0]
            rate = struct.unpack("<I", head[24:28])[0]
            bits = struct.unpack("<H", head[34:36])[0]
            if ch and rate and bits:
                return ch, rate, bits
    except OSError:
        pass
    return 2, 48000, 16


def buffer_seconds():
    ch, rate, bits = buffer_format()
    audio = max(buffer_size() - 44, 0)
    return audio / float(rate * ch * bits // 8)


def buffer_is_live():
    """Whether the buffer is growing, which is the only proof the tap is working.

    Nothing else separates "on, and catching this game" from "switched on after
    the game had already started", which is the mistake that quietly records
    nothing at all.
    """
    import time
    before = buffer_size()
    time.sleep(0.4)
    return buffer_size() > before


def buffer_peak(seconds=3.0):
    """Loudest sample in the last few seconds, 0.0 to 1.0, for a silence check."""
    try:
        import audioop
    except ImportError:
        return None
    ch, rate, bits = buffer_format()
    if bits != 16:
        return None
    want = int(seconds * rate * ch * 2)
    size = buffer_size()
    if size <= 44:
        return None
    try:
        with open(BUFFER, "rb") as f:
            f.seek(max(44, size - want))
            data = f.read(want)
    except OSError:
        return None
    data = data[:len(data) // (2 * ch) * (2 * ch)]
    if not data:
        return None
    return audioop.max(data, 2) / 32768.0


def clear_buffer():
    """Empty the buffer, unless something is playing into it right now."""
    if buffer_is_live():
        return False, "Something is playing. Quit the game first."
    try:
        if os.path.exists(BUFFER):
            os.unlink(BUFFER)
        return True, "Buffer cleared."
    except OSError as e:
        return False, "Could not clear it: %s" % e


def card_free():
    """Free bytes on the card the recordings are saved to."""
    try:
        st = os.statvfs(MUSIC if os.path.isdir(MUSIC) else "/mnt/mmc")
        return st.f_bavail * st.f_frsize
    except OSError:
        return 0
