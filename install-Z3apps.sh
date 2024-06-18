#!/bin/sh
set -e
progdir=$(cd $(dirname $0); pwd)
exec >Z3apps-logfile.txt 2>&1

apt install -y mpv wget git imagemagick python3.8

ln -fs /usr/bin/python3.8 /usr/bin/python3

wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/bin/yt-dlp
chmod a+rx /usr/bin/yt-dlp  # Make executable
ln -fs /usr/bin/yt-dlp /usr/bin/youtube-dl

mkdir -p temp
git clone https://github.com/Z3R0C1PH3R/Z3apps.git temp
cp -r temp/Z3apps temp/YouTube-Z3.sh $progdir/
rm -rf temp
reboot
