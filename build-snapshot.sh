VERSION=0.64
ALPHATAG=`git-show-ref --hash=10 refs/heads/master`
TARBALL=sugar-$VERSION-git$ALPHATAG.tar.bz2

rm sugar-$VERSION.tar.bz2

make distcheck

mv sugar-$VERSION.tar.bz2 $TARBALL
scp $TARBALL mpg@devserv.devel.redhat.com:~
rm $TARBALL
