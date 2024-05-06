#!/bin/bash
progdir=$(cd $(dirname $0); pwd)
cd $progdir/Z3apps
python3 term.py
