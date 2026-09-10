#!/bin/bash
progdir=$(cd $(dirname $0); pwd)
exec >"$progdir/Z3rec-logfile.txt" 2>&1
cd $progdir/Z3rec
python3 z3rec.py
