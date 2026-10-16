#!/bin/sh

test -n "${srcdir}" || srcdir=`dirname "$0"`
test -n "${srcdir}" || srcdir="$(pwd)"

olddir="$(pwd)"
cd "$srcdir"

mkdir -p m4

intltoolize --force
autoreconf -i

cd "$olddir"
"$srcdir/configure" --enable-maintainer-mode "$@"
