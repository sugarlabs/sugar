#!/bin/sh
intltoolize
autoreconf -i
./configure --enable-maintainer-mode "$@"
