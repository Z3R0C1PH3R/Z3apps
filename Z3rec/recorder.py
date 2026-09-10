"""Turning the tap's buffer into a file in the Music folder.

The buffer is a WAV that alsa-lib is still writing to, which means its header
claims a length of zero: the plugin only fills the size fields in when the file
is closed, and it is not closed until the game exits. So nothing here trusts
that header for anything except the sample format, and every saved file gets a
header written from the byte count actually copied.

Compressed formats go through ffmpeg, which is on the stock firmware but is
broken out of the box, see FFMPEG_ENV below. WAV is written directly so that
saving still works even if that ever stops being true.
"""

import os
import subprocess
import struct
import tempfile
import time

import audiotap

# The stock ffmpeg fails at startup with
#   undefined symbol: FcWeightFromOpenTypeDouble
# because libpangoft2 wants fontconfig 1.12 while /usr/lib's libfontconfig.so.1
# symlink still points at 1.10, which does not export that symbol. Both versions
# are installed, so preloading the newer one fixes it without touching any
# system symlink.
FONTCONFIG = "/usr/lib/aarch64-linux-gnu/libfontconfig.so.1.12.0"

FORMATS = ["mp3", "wav", "flac", "opus", "ogg"]
CODECS = {"mp3": "libmp3lame", "flac": "flac", "opus": "libopus", "ogg": "libvorbis"}
MUXERS = {"mp3": "mp3", "flac": "flac", "opus": "opus", "ogg": "ogg", "wav": "wav"}
LOSSY = ("mp3", "opus", "ogg")
BITRATES = ["96k", "128k", "192k", "256k", "320k"]

CHUNK = 1 << 18  # 256 KB, about 1.4 seconds of audio


def ffmpeg_env():
    """A clean environment for ffmpeg.

    LD_LIBRARY_PATH has to go. The stock launcher exports
    /usr/lib32:/usr/lib:/mnt/vendor/lib for the emulators, and /usr/lib holds a
    cut-down vendor build of libavformat with no mp3 muxer in it. Inheriting
    that makes ffmpeg load the wrong library and every compressed save die with
    "Invalid argument" as the output file is opened, but only when Z3rec is
    started from the APPS menu, since a shell does not set the variable.
    """
    env = dict(os.environ)
    env.pop("LD_LIBRARY_PATH", None)
    if os.path.exists(FONTCONFIG):
        env["LD_PRELOAD"] = FONTCONFIG
    return env


_muxers = None


def muxers():
    """Container formats this ffmpeg can actually write.

    Asked rather than assumed, because "ffmpeg runs" and "ffmpeg can write an
    mp3" turned out to be different questions on this firmware.
    """
    global _muxers
    if _muxers is None:
        _muxers = set()
        try:
            r = subprocess.run(["ffmpeg", "-hide_banner", "-muxers"], capture_output=True,
                               text=True, env=ffmpeg_env(), timeout=30)
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == "E":
                        _muxers.add(parts[1])
        except (OSError, subprocess.SubprocessError):
            pass
    return _muxers


def have_ffmpeg():
    return bool(muxers())


def available_formats():
    """Only offer what this handheld can actually write. WAV never needs ffmpeg."""
    names = muxers()
    return [f for f in FORMATS if f == "wav" or MUXERS[f] in names] or ["wav"]


# ------------------------------------------------------------------- helpers


def wav_header(nbytes, ch, rate, bits):
    block = ch * bits // 8
    return (b"RIFF" + struct.pack("<I", 36 + nbytes) + b"WAVEfmt " +
            struct.pack("<IHHIIHH", 16, 1, ch, rate, block * rate, block, bits) +
            b"data" + struct.pack("<I", nbytes))


def span(seconds=None):
    """Byte range of the buffer to save, always on a whole-sample boundary."""
    ch, rate, bits = audiotap.buffer_format()
    frame = ch * bits // 8
    size = audiotap.buffer_size()
    end = 44 + max(size - 44, 0) // frame * frame
    start = 44
    if seconds:
        start = max(44, end - int(seconds * rate) * frame)
    start = 44 + (start - 44) // frame * frame
    return start, end


def unique_path(folder, base, ext):
    path = os.path.join(folder, "%s.%s" % (base, ext))
    n = 2
    while os.path.exists(path):
        path = os.path.join(folder, "%s-%d.%s" % (base, n, ext))
        n += 1
    return path


def _pump(dest, start, end, progress):
    """Copy the buffer range into an open file or pipe, reporting progress."""
    total = end - start
    done = 0
    with open(audiotap.BUFFER, "rb") as src:
        src.seek(start)
        while done < total:
            data = src.read(min(CHUNK, total - done))
            if not data:
                break
            dest.write(data)
            done += len(data)
            if progress:
                progress(done / float(total) if total else 1.0)
    return done


# --------------------------------------------------------------------- saving


def save(seconds=None, fmt="mp3", bitrate="192k", mono=False, progress=None):
    """Write part or all of the buffer into the Music folder.

    Returns (ok, path or message).
    """
    ch, rate, bits = audiotap.buffer_format()
    start, end = span(seconds)
    if end - start < rate:  # under a second of audio
        return False, "There is nothing recorded yet."

    if bits != 16:
        return False, "Unexpected %d-bit audio in the buffer." % bits

    folder = audiotap.MUSIC
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError as e:
        return False, "Cannot use %s: %s" % (folder, e)

    # A rough size check, so a save cannot be what fills the card.
    need = (end - start) if fmt == "wav" else (end - start) // 8
    if audiotap.card_free() < need + (16 << 20):
        return False, "Not enough space on the card."

    path = unique_path(folder, time.strftime("Z3rec-%Y-%m-%d-%H%M"), fmt)

    try:
        if fmt == "wav":
            ok, err = _save_wav(path, start, end, ch, rate, bits, mono, progress)
        else:
            ok, err = _save_encoded(path, start, end, ch, rate, fmt, bitrate, mono, progress)
    except OSError as e:
        ok, err = False, str(e)

    if not ok:
        try:
            os.unlink(path)
        except OSError:
            pass
        return False, err
    return True, path


def _save_wav(path, start, end, ch, rate, bits, mono, progress):
    if mono and ch == 2:
        return _save_wav_mono(path, start, end, rate, bits, progress)
    with open(path, "wb") as out:
        out.write(wav_header(end - start, ch, rate, bits))
        copied = _pump(out, start, end, progress)
        if copied != end - start:  # the buffer was truncated under us
            out.seek(0)
            out.write(wav_header(copied, ch, rate, bits))
    return True, None


def _save_wav_mono(path, start, end, rate, bits, progress):
    """Mono WAV without ffmpeg, so the simplest format never needs it."""
    import audioop
    total = end - start
    done = 0
    with open(path, "wb") as out, open(audiotap.BUFFER, "rb") as src:
        out.write(wav_header(0, 1, rate, bits))
        src.seek(start)
        written = 0
        while done < total:
            data = src.read(min(CHUNK, total - done))
            if not data:
                break
            data = data[:len(data) // 4 * 4]
            done += len(data)
            frag = audioop.tomono(data, 2, 0.5, 0.5)
            out.write(frag)
            written += len(frag)
            if progress:
                progress(done / float(total))
        out.seek(0)
        out.write(wav_header(written, 1, rate, bits))
    return True, None


def _save_encoded(path, start, end, ch, rate, fmt, bitrate, mono, progress):
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "s16le", "-ar", str(rate), "-ac", str(ch), "-i", "pipe:0"]
    if mono:
        args += ["-ac", "1"]
    args += ["-c:a", CODECS[fmt]]
    if fmt in LOSSY:
        args += ["-b:a", bitrate]
    args.append(path)

    # stderr goes to a file rather than a pipe: audio is fed in over a minute or
    # more, and a pipe nobody is draining would fill and wedge ffmpeg mid-encode.
    errors = tempfile.TemporaryFile()
    try:
        proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                stderr=errors, env=ffmpeg_env())
    except OSError as e:
        errors.close()
        return False, "ffmpeg would not start: %s" % e

    try:
        _pump(proc.stdin, start, end, progress)
    except (OSError, ValueError):
        pass  # ffmpeg died early; the returncode below explains why
    try:
        proc.stdin.close()
    except (OSError, ValueError):
        pass
    proc.wait()

    errors.seek(0)
    detail = errors.read().decode("utf-8", "replace").strip().splitlines()
    errors.close()
    if proc.returncode != 0:
        return False, detail[-1][:60] if detail else "ffmpeg failed."
    return True, None


# ------------------------------------------------------------------- browsing


def recordings():
    """Saved files, newest first. Only ones Z3rec made, so deleting is safe."""
    try:
        names = os.listdir(audiotap.MUSIC)
    except OSError:
        return []
    found = []
    for name in names:
        if not name.startswith("Z3rec-"):
            continue
        path = os.path.join(audiotap.MUSIC, name)
        try:
            found.append((name, os.path.getsize(path), os.path.getmtime(path)))
        except OSError:
            continue
    found.sort(key=lambda item: item[2], reverse=True)
    return found


def delete(name):
    if not name.startswith("Z3rec-"):
        return False
    try:
        os.unlink(os.path.join(audiotap.MUSIC, name))
        return True
    except OSError:
        return False
