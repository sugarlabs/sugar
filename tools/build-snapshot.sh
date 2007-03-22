VERSION=0.63
DATE=`date +%Y%m%d`
RELEASE=2.58
TARBALL=sugar-$VERSION-$RELEASE.${DATE}git.tar.bz2

rm sugar-$VERSION.tar.bz2

XUL_SDK=/home/marco/sugar-jhbuil/build/lib/xulrunner-1.9a2
DISTCHECK_CONFIGURE_FLAGS="--with-xul-sdk=$XUL_SDK" make distcheck

mv sugar-$VERSION.tar.bz2 $TARBALL
scp $TARBALL mpg@devserv.devel.redhat.com:~
rm $TARBALL
