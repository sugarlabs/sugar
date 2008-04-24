#!/bin/sh
intltoolize
autoreconf -i
./configure "$@"
