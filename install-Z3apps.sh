#!/bin/sh
# Copy this file into Roms/APPS and run it from the APPS menu, with WiFi on.
# It installs every Z3 app in one go.
#
# The terminal and Z3rec are small and live in this repository, so they are
# copied straight across. Z3yt, Z3pad and Z3capture are each big enough to have
# their own repository and their own installer, which knows about that app's
# dependencies, so those installers are downloaded and run in turn rather than
# having their contents copied out here and slowly drift.
set -e
progdir=$(cd "$(dirname "$0")" && pwd)
exec >"$progdir/Z3apps-install-logfile.txt" 2>&1

export DEBIAN_FRONTEND=noninteractive
export GIT_TERMINAL_PROMPT=0
export GIT_HTTP_LOW_SPEED_LIMIT=1000
export GIT_HTTP_LOW_SPEED_TIME=60

REPO=Z3R0C1PH3R/Z3apps
BRANCH=main

# app:repo. The installer inside each one is named install-<app>.sh.
FETCHED="Z3yt Z3pad Z3capture"

ok=0
fail() {
    if [ "$ok" -eq 1 ]; then
        return 0
    fi
    echo "ERROR"
    # Try to say so on screen, from whichever copy of display.py exists. The cd
    # has to reach the python, so the two are grouped with braces rather than
    # brackets: a bracket makes the cd its own subshell, the python then runs
    # back in the original directory, finds no display module, and the failure
    # goes unreported on screen. Which is the one moment it matters.
    ( { cd /temp/Terminal 2>/dev/null || cd "$progdir/Terminal" 2>/dev/null; } && \
        python3 -c "import display; display.draw_text('ERROR, CHECK LOGS')" ) || true
    cd / || true
    rm -rf /temp
    exit 1
}
trap fail EXIT

retry() {
    tries=$1
    shift
    n=1
    while [ "$n" -le "$tries" ]; do
        if "$@"; then
            return 0
        fi
        echo "attempt $n/$tries failed: $*"
        n=$((n + 1))
        sleep 5
    done
    return 1
}

msg() {
    # Same two-copy fallback as fail(). The copy under $progdir is the one that
    # does the work for most of this script, because the app installers below
    # each clear /temp out for their own download.
    ( { cd /temp/Terminal 2>/dev/null || cd "$progdir/Terminal" 2>/dev/null; } && \
        python3 -c "import display; display.draw_text('''$1''')" ) || true
}

# One line per app, kept and redrawn so the screen shows the whole run rather
# than only whichever app is going now. Installing all five takes a while and a
# still screen looks like a hang.
report=""
note() {
    report="$report$(printf '%-11s %s' "$1" "$2")
"
    msg "Installing Z3apps

$report"
}

echo "Z3apps install started $(date)"
echo "kernel $(uname -r), installing into $progdir"

echo "-- requirements --"
python3 -c "import sys; assert sys.version_info >= (3, 6), sys.version" || \
    { echo "python3 is too old or missing"; exit 1; }
test -c /dev/fb0 || echo "WARNING: no /dev/fb0, the on-screen menus will not draw"

# Prefer IPv4: these handhelds often have AAAA records but no working IPv6.
if [ -f /etc/gai.conf ]; then
    grep -q '^precedence ::ffff:0:0/96' /etc/gai.conf 2>/dev/null || \
        echo 'precedence ::ffff:0:0/96  100' >> /etc/gai.conf
else
    echo 'precedence ::ffff:0:0/96  100' > /etc/gai.conf
fi

# If GitHub does not resolve (common on busy/captive WiFi), try public DNS.
if ! getent hosts github.com >/dev/null 2>&1; then
    echo "github.com did not resolve, trying public DNS"
    iface=$(ip route 2>/dev/null | awk '/default/ {print $5; exit}')
    if command -v resolvectl >/dev/null 2>&1 && [ -n "$iface" ]; then
        resolvectl dns "$iface" 1.1.1.1 8.8.8.8 9.9.9.9 || true
    fi
fi

if ! command -v git >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    apt-get -y -o Acquire::Retries=5 update
    apt-get -y -o Acquire::Retries=5 install git wget
fi

clone_github() {
    rm -rf /temp
    git clone --depth 1 --branch "$BRANCH" "https://github.com/$REPO.git" /temp
}

fetch_tarball() {
    rm -rf /temp /tmp/z3apps.tgz /tmp/z3apps-extract
    mkdir -p /tmp/z3apps-extract
    wget --timeout=60 --tries=8 --retry-connrefused \
        -O /tmp/z3apps.tgz \
        "https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH"
    tar -xzf /tmp/z3apps.tgz -C /tmp/z3apps-extract
    mv "/tmp/z3apps-extract/$(basename "$REPO")-$BRANCH" /temp
    rm -rf /tmp/z3apps.tgz /tmp/z3apps-extract
}

echo "-- downloading Z3apps --"
if ! (command -v git >/dev/null 2>&1 && retry 3 clone_github); then
    echo "git clone unavailable or failed, trying GitHub tarball"
    retry 3 fetch_tarball
fi
test -f /temp/Terminal/term.py
test -f /temp/Terminal/font32.bin
test -f /temp/Z3rec/z3rec.py

# The apps carried in this repo go in first, so that $progdir/Terminal exists
# and every message from here on can still be drawn once /temp is gone.
echo "-- the apps in this repo --"
cp -r /temp/Terminal /temp/Terminal.sh "$progdir/"
chmod a+x "$progdir/Terminal.sh"
note Terminal done

# Keep the format and length the user already chose.
if [ -f "$progdir/Z3rec/settings.json" ]; then
    cp "$progdir/Z3rec/settings.json" /temp/Z3rec/settings.json
    echo "kept Z3rec's existing settings.json"
fi
cp -r /temp/Z3rec /temp/Z3rec.sh "$progdir/"
chmod a+x "$progdir/Z3rec.sh"
note Z3rec done
mkdir -p /mnt/mmc/Music || echo "WARNING: cannot create /mnt/mmc/Music"

# The YouTube app used to be called Z3apps and installed itself under that name.
# Its installer now writes to $progdir/Z3yt, so the old folder would sit there
# unreferenced. The terminal used to be a loose term.sh beside it.
rm -rf "$progdir/Z3apps" "$progdir/term.sh"

install_one() {
    app=$1
    script="$progdir/.install-$app.sh"
    note "$app" "..."
    # Downloaded beside the app rather than into /tmp because each installer
    # puts the app next to itself, and a dot in front so that it does not show
    # up as an entry of its own in the APPS menu while it runs.
    if ! retry 3 wget --timeout=60 --tries=4 --retry-connrefused -q -O "$script" \
        "https://raw.githubusercontent.com/Z3R0C1PH3R/$app/$BRANCH/install-$app.sh"; then
        rm -f "$script"
        echo "could not download $app's installer"
        note "$app" "NO NET"
        return 1
    fi
    # Z3APPS_NO_REBOOT keeps each installer from restarting the handheld out
    # from under the ones after it. This script restarts once at the end.
    if Z3APPS_NO_REBOOT=1 sh "$script"; then
        rm -f "$script"
        note "$app" done
        return 0
    fi
    rm -f "$script"
    echo "$app's installer failed, see $app's own log next to this one"
    note "$app" FAILED
    return 1
}

echo "-- the apps with their own repos --"
failed=""
for app in $FETCHED; do
    echo "-- $app --"
    install_one "$app" || failed="$failed $app"
done

echo "-- state after install --"
if grep -q 'z3out' /etc/asound.conf 2>/dev/null; then
    echo "a sound tap is installed, so recording is ON in Z3rec or Z3capture"
else
    echo "sound recording is off, turn it on from Z3rec or Z3capture"
fi

ok=1
if [ -n "$failed" ]; then
    echo "these did not install:$failed"
    msg "Installing Z3apps

$report
Some apps failed,
check the logs.
Restarting..."
else
    echo "all apps installed"
    msg "Installing Z3apps

$report
Install Successful
Restarting..."
fi
cd /
rm -rf /temp
sleep 5
reboot
