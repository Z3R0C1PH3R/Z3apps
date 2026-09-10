# Z3apps

Everything I have made for the RG35xx family, and one installer that puts all of it on the handheld at once.

You do not need this repository to use any of the apps. Each one installs perfectly well on its own, and if you only want the gamepad or only want the recorder, go and get that one. This is for when you want the lot and would rather not run five installers and sit through five restarts.

Output is drawn straight to the Linux framebuffer and input is read straight from the event devices, so nothing here is really tied to Anbernic hardware. It is only tested on the RG35xx Plus and the RG35xx SP.

## The apps

| App | What it does | Lives in |
|-----|--------------|----------|
| **Z3yt** | Search YouTube from the handheld with an on-screen keyboard and watch the results, with the buttons wired up to seeking and volume. | [its own repo](https://github.com/Z3R0C1PH3R/Z3yt) |
| **Z3pad** | Turns the handheld into a USB or Bluetooth gamepad for your PC, using its own buttons. | [its own repo](https://github.com/Z3R0C1PH3R/Z3pad) |
| **Z3capture** | Records the sound and the screen of whatever you are playing, straight onto the card. | [its own repo](https://github.com/Z3R0C1PH3R/Z3capture) |
| **Z3rec** | The same recorder without the video. Cheaper to run and simpler to think about. | here, in `Z3rec/` |
| **Terminal** | A shell, with the on-screen keyboard for typing and the screen for output. | here, in `Terminal/` |

Z3rec and the terminal are small enough that a repository each would be more ceremony than they are worth, so they are carried here. The other three are big enough to want their own, and each brings its own installer that knows what that app needs, which is what this one runs.

### Z3rec and Z3capture together

Both of them record sound the same way, by putting a tap in front of the one ALSA device the handheld has, and only one tap can be in front of it. Installing both is fine and this installer does exactly that. Turning **recording** on in both is not: whichever you switch on last takes the tap, and the other one quietly stops getting anything. Pick one to record with and leave the other's recording switched off.

Both of them are off after an install, so nothing is decided for you.

## Installing

1. Make sure the **WiFi is connected** and the **time is set correctly** in settings. The time matters because a wrong clock breaks HTTPS.
2. Copy [install-Z3apps.sh](https://github.com/Z3R0C1PH3R/Z3apps/releases/latest/download/install-Z3apps.sh) into your `Roms/APPS` folder.
3. Run it from the APPS menu. It reports each app on screen as it goes.
4. The handheld restarts when it is done, which is how the new entries appear in the APPS menu. Then you can delete `install-Z3apps.sh`.

It takes a while, mostly because Z3yt pulls down mpv and yt-dlp. If you already have some of these installed, running this updates them and keeps their settings.

If an app fails, the others still install, the screen says which one went wrong, and each app writes its own log next to the script in `Roms/APPS`. Start with `Z3apps-install-logfile.txt`.

### Doing it without WiFi

Copy the folders and the matching `.sh` files into `Roms/APPS` by hand, from here for `Terminal` and `Z3rec`, and from each app's own repository for the other three. That is all the installer does with the files; the rest of it is fetching them and installing the packages Z3yt needs.

## Notes

Z3yt used to be called Z3apps, back when it was the only app and the name was aspirational. It has been renamed, and this is the Z3apps that actually is what the name says. If you have an old install, this installer clears out the leftover `Z3apps` folder for you.

##### If you like my work and want to say thanks, or encourage me to do more, you can [buy me a coffee](https://buymeacoffee.com/z3r0c1ph3r) or a [ko-fi!](https://ko-fi.com/z3r0c1ph3r)
