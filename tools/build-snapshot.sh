VERSION=0.63
DATE=`date +%Y%m%d`
RELEASE=2.69
TARBALL=sugar-$VERSION-$RELEASE.${DATE}git.tar.bz2

rm sugar-$VERSION.tar.bz2

XUL_SDK=/home/marco/sugar-jhbuild/build/lib/xulrunner-1.9a4pre-dev
DISTCHECK_CONFIGURE_FLAGS="--with-libxul-sdk=$XUL_SDK" make distcheck

mv sugar-$VERSION.tar.bz2 $TARBALL
scp $TARBALL mpg@devserv.devel.redhat.com:~
rm $TARBALL
