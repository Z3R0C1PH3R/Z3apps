# Z3rec
Records your handheld's own sound into its Music folder

Turn recording on, play something, then come back and save it. Whatever came out of the speaker becomes an mp3 (or wav, flac, opus, ogg) in `Music`, ready to play back on the device or copy off the card.

Tested on the RG35XX Plus on the stock Anbernic firmware. Other H700 handhelds should work, since the only thing Z3rec needs from the firmware is a `pcm.!default` in `/etc/asound.conf`, and it checks for that before changing anything. It needs no packages: the recording itself is done by a plugin already inside alsa-lib, the menu is drawn with nothing but the Python standard library, and the compressed formats use the ffmpeg already on the image.

There is nothing to start and stop while you play, because a game owns the screen and Z3rec cannot be in front of it. Recording is a switch you leave on instead, and the last session is always waiting for you when you come back.

**Only sound from inside a game is recorded.** Nothing is captured while you are in the launcher or in Z3rec itself, so with recording on and no game played yet, the app correctly says there is nothing there. The stock launcher talks to the sound card directly instead of going through the device Z3rec taps, so its menu sounds and its music player go past untouched.

## Installation/Updating The App

Z3rec is part of [Z3apps](https://github.com/Z3R0C1PH3R/Z3apps), and the installer there puts it in your APPS menu along with everything else. Run that same installer again any time to update. Your format and quality settings are kept.

If you want only this one app, copy it across by hand. No WiFi needed, and nothing is installed outside the APPS folder.

1. Download the Z3apps repository ([zip](https://github.com/Z3R0C1PH3R/Z3apps/archive/refs/heads/main.zip)) and unpack it on your computer.
2. Copy the `Z3rec` folder and the `Z3rec.sh` file into your Roms/APPS folder, so that you end up with `Roms/APPS/Z3rec.sh` and `Roms/APPS/Z3rec/`.
3. Put the card back in and restart the device.

To update by hand later, replace the `Z3rec` folder with a newer one, keeping your `Z3rec/settings.json` if you have changed the format.

Recording the screen as well as the sound is what [Z3capture](https://github.com/Z3R0C1PH3R/Z3capture) is for. Install both if you like, but only turn recording on in one of them: they both want the same ALSA device, and whichever you switch on last takes it.

## Usage

1. Start Z3rec from the APPS menu and choose **Recording on**.
2. **Go and launch your game.** This part matters: a program only picks up the tap when it starts, so anything already running when you switched recording on is not captured. If you were mid-game, quit and start it again.
3. Play. Everything that comes out of the speaker is being written to the card.
4. Quit back to the menu and open Z3rec again. The top of the screen tells you how much it caught.
5. **Save all**, or **Save last** for just the end of it. The file lands in `Music`.

| Menu entry    | What it does                                                        |
|---------------|---------------------------------------------------------------------|
| Save all      | Everything captured since the game started                          |
| Save last     | Only the final 30s/1m/2m/5m/10m, set in Settings                    |
| Clear buffer  | Throws away what has been captured, freeing the space               |
| Recording on/off | Adds or removes the tap. Off puts the stock audio config back    |
| Recordings    | What Z3rec has saved, with the size. A deletes one                  |
| Settings      | Format, quality, mono or stereo, and the "Save last" length         |

Saving does not consume the buffer, so you can save the last minute, decide you want all of it, and save that too.

### Settings

| Setting   | Choices                          | Notes                                          |
|-----------|----------------------------------|------------------------------------------------|
| Format    | mp3, wav, flac, opus, ogg        | Only wav is offered if ffmpeg will not run     |
| Quality   | 96k to 320k                      | mp3, opus and ogg only                         |
| Channels  | stereo or mono                   | Mono halves the size, and most of these games are close to mono anyway |
| Save last | 30s, 1m, 2m, 5m, 10m             | What the "Save last" entry saves               |

Recordings are named `Z3rec-YYYY-MM-DD-HHMM`, so **set the clock** in system settings or they will all be dated 1970.

## Space

Audio is captured as 48kHz 16-bit stereo, which is about **11 MB per minute** while something is playing. The main screen shows how much room is left on the card.

The buffer starts over every time a game launches, so an ordinary session cleans up after itself and you never have to think about it. The one case to watch is leaving a game running untouched for many hours, which will slowly fill the card. Turn recording off when you are not using it, or use **Clear buffer**.

## How It Works

1. These handhelds have **no ALSA capture device at all**. Every PCM the kernel exposes is playback only, there is no `/dev/snd/pcmC0D0c`, and `snd-aloop` is not built for this kernel, so there is nothing to record from in the usual sense.
2. So Z3rec records the *output* instead. `audiotap.py` puts alsa-lib's **`file` plugin** in front of the sound card: audio still reaches the speaker untouched, and a second copy is written to `/mnt/mmc/.z3rec/buffer.wav`. The plugin is part of alsa-lib itself, so nothing has to be installed or built.
3. The tap takes over **`default`** rather than adding a device under its own name. The stock RetroArch reads its `audio_device` setting and then opens `default` regardless of what it says, so a named device is simply never used. Taking over `default` also means Z3rec catches anything else that plays through ALSA.
4. The stock `pcm.!default` is **renamed to `pcm.z3out`** and the tap is pointed at it, rather than being replaced. That way whatever the firmware does when the card is opened (on the Plus, flipping a row of mixer switches and setting the volume) still happens exactly as before, just behind the tap. After writing the change Z3rec asks alsa-lib to parse it and puts the original back if it will not.
5. alsa-lib only fills in the length fields of a WAV header when the file is **closed**, and the buffer is not closed until the game exits, so its header claims zero bytes. Nothing reads that header except to learn the sample format; every saved file gets a header written from the bytes actually copied.
6. Compressed formats are encoded on the device, at around **12x realtime** for stereo mp3 and 27x for mono, so a long session is a short wait with a progress bar rather than something you have to do on a computer.
7. The screen is drawn by `display.py` and the buttons read by `padreader.py`, both taken from [Z3pad](https://github.com/Z3R0C1PH3R/Z3pad).

### The ffmpeg on these devices is broken twice over, and Z3rec fixes both

**It will not start.** Running `ffmpeg` on the stock image fails immediately with:

```
symbol lookup error: libpangoft2-1.0.so.0: undefined symbol: FcWeightFromOpenTypeDouble
```

Both fontconfig 1.10 and 1.12 are installed, but the `libfontconfig.so.1` symlink points at 1.10, which does not export that symbol, while pango needs it. Z3rec preloads the newer library for its own ffmpeg calls, so no system file or symlink is touched.

**And under the APPS launcher it cannot write an mp3.** The launcher exports `LD_LIBRARY_PATH=/usr/lib32:/usr/lib:/mnt/vendor/lib` for the emulators, and `/usr/lib` holds a cut-down vendor build of `libavformat.so.58` with no mp3 muxer in it. That build gets loaded ahead of the real one, and every compressed save dies as the output file is opened:

```
Unable to find a suitable output format for '/mnt/mmc/Music/....mp3'
/mnt/mmc/Music/....mp3: Invalid argument
```

It only happens when Z3rec is launched from APPS, never from a shell, because a shell does not set that variable. Z3rec drops `LD_LIBRARY_PATH` when it runs ffmpeg, and asks ffmpeg which muxers it really has rather than assuming, so the Settings screen can only offer formats that will actually save.

Both fixes together, if you want a working ffmpeg on the shell for anything else:

```sh
unset LD_LIBRARY_PATH
LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libfontconfig.so.1.12.0 ffmpeg ...
```

## Known Issues

1. Recording has to be on **before** the game starts. There is no way around this: ALSA settles which device a program is using at the moment it opens the sound card.
2. The stock launcher's own menu sounds are not captured, because it opens the sound card directly rather than going through `default`.
3. The buffer holds one session. Launching another game throws away the previous one, so save before you move on.
4. If recording is on and the buffer folder is somehow missing, the tap has nowhere to write and the handheld comes up with **no sound at all**. Z3rec checks for this when it starts and offers to switch recording off. To fix it by hand, edit `/etc/asound.conf`: delete the block at the bottom marked `added by Z3rec` and rename `pcm.z3out` back to `pcm.!default`. A copy of the original is kept at `/etc/asound.conf.z3rec-backup`.

## Credits

`display.py`, `padreader.py` and `font32.bin` come from [Z3pad](https://github.com/Z3R0C1PH3R/Z3pad), whose framebuffer code in turn comes from [Z3yt](https://github.com/Z3R0C1PH3R/Z3yt). Licensed GPL-3.0.

##### If you like my work and want to say thanks, or encourage me to do more, you can [buy me a coffee](https://buymeacoffee.com/z3r0c1ph3r) or a [ko-fi!](https://ko-fi.com/z3r0c1ph3r)
