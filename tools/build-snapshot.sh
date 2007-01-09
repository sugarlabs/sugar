VERSION=0.63
DATE=`date +%Y%m%d`
RELEASE=2.6
TARBALL=sugar-$VERSION-$RELEASE.${DATE}git.tar.bz2

rm sugar-$VERSION.tar.bz2
make distcheck

mv sugar-$VERSION.tar.bz2 $TARBALL
scp $TARBALL mpg@devserv.devel.redhat.com:~
rm $TARBALL
