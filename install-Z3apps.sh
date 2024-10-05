#!/bin/sh
set -e
progdir=$(cd $(dirname $0); pwd)
exec >Z3apps-logfile.txt 2>&1

if
    apt -y update
    apt install -y git python3-pip
    python3 -m pip install numpy
    mkdir -p /temp
    git clone https://github.com/Z3R0C1PH3R/Z3apps.git /temp
    cd /temp/Z3apps
    python3 -c "import display; display.draw_text('Updating apt...')"
    python3 -c "import display; display.draw_text('Installing apt dependencies...')"
    apt install -y mpv wget

    python3 -c "import display; display.draw_text('Installing apt dependencies...\nDone\nInstalling pip dependencies...')"
    python3 -m pip install pillow

    python3 -c "import display; display.draw_text('Installing apt dependencies...\nDone\nInstalling pip dependencies...\nDone\nInstalling yt-dlp...')"
    wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/bin/yt-dlp
    chmod a+rx /usr/bin/yt-dlp  # Make executable
    ln -fs /usr/bin/yt-dlp /usr/bin/youtube-dl

    python3 -c "import display; display.draw_text('Installing apt dependencies...\nDone\nInstalling pip dependencies...\nDone\nInstalling yt-dlp...\nDone\nInstalling Z3apps...')"
    cp -r /temp/Z3apps /temp/YouTube-Z3.sh $progdir/
then
    set +e
    python3 -c "import display; display.draw_text('Installing apt dependencies...\nDone\nInstalling pip dependencies...\nDone\nInstalling yt-dlp...\nDone\nInstalling Z3apps...\nDone\nInstall Successful\nRebooting...')"
    rm -rf /temp
    sleep 5
    reboot
else
    set +e
    echo "ERROR"
    rm -rf /temp
    python3 -c "import display; display.draw_text('.\n.\n.\n.\n.\n.\n.\n.\n.\n.\n.\nERROR, CHECK LOGS')"
fi
