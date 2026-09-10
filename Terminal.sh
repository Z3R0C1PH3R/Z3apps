#!/bin/bash
progdir=$(cd $(dirname $0); pwd)
exec >"$progdir/Terminal-logfile.txt" 2>&1
cd $progdir/Terminal
python3 term.py
