#!/bin/tcsh

setenv PYTHONPATH `pwd`/p2p

# for activity.py
setenv PYTHONPATH "$PYTHONPATH":`pwd`/shell/src/

# for sugar_globals.py
setenv PYTHONPATH "$PYTHONPATH":`pwd`/
