#!/bin/sh
set -e
progdir=$(cd $(dirname $0); pwd)
exec >Z3apps-logfile.txt 2>&1

apt install -y mpv
wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/bin/yt-dlp
chmod a+rx /usr/bin/yt-dlp  # Make executable
ln -s /usr/bin/yt-dlp /usr/bin/youtube-dl
echo ytdl-format=bestvideo[height<=?480][width<=?640]+bestaudio/best >> /etc/mpv/mpv.conf 
apt install -y python3.8
ln -s /usr/bin/python3.8 /usr/bin/python3
mkdir temp
git clone https://github.com/Z3R0C1PH3R/Z3apps.git temp
cp -r temp/Z3apps temp/yt.sh temp/term.sh $progdir/
rm -rf temp
