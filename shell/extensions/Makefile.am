sugardir = $(pkgdatadir)/shell
sugar_PYTHON =		\
	__init__.py

pkgpyexecdir = $(pkgdatadir)/shell

pkgpyexec_LTLIBRARIES = extensions.la

extensions_la_LDFLAGS = -module -avoid-version

extensions_la_CFLAGS =			\
	$(WARN_CFLAGS)			\
	$(PYTHON_INCLUDES)		\
	$(PYGTK_CFLAGS)			\
	$(SHELL_CFLAGS)			\
	$(top_srcdir)/shell/extensions

extensions_la_LIBADD = 		\
	$(SHELL_LIBS) 		\
	$(PYCAIRO_LIBS)		\
	-lgstinterfaces-0.10	\
	-lgstaudio-0.10

extensions_la_SOURCES =		\
	$(BUILT_SOURCES)	\
	eggaccelerators.h	\
	eggaccelerators.c	\
	sugar-audio-manager.c	\
	sugar-audio-manager.h	\
	sugar-key-grabber.h	\
	sugar-key-grabber.c	\
	extensionsmodule.c

BUILT_SOURCES = 		\
	extensions.c		\
	sugar-shell-marshal.c	\
	sugar-shell-marshal.h

stamp_files = \
	stamp-sugar-shell-marshal.c	\
	stamp-sugar-shell-marshal.h

sugar-shell-marshal.c: stamp-sugar-shell-marshal.c
	@true
stamp-sugar-shell-marshal.c: sugar-shell-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_shell_marshal \
		$(srcdir)/sugar-shell-marshal.list --header --body > \
		sugar-shell-marshal.c && echo timestamp > $(@F)

sugar-shell-marshal.h: stamp-sugar-shell-marshal.h
	@true
stamp-sugar-shell-marshal.h: sugar-shell-marshal.list
	$(GLIB_GENMARSHAL) --prefix=sugar_shell_marshal \
		$(srcdir)/sugar-shell-marshal.list --header > \
		sugar-shell-marshal.h && echo timestamp > $(@F)

CLEANFILES = $(stamp_files) $(BUILT_SOURCES)
DISTCLEANFILES = $(stamp_files) $(BUILT_SOURCES)
MAINTAINERCLEANFILES = $(stamp_files) $(BUILT_SOURCES)

EXTRA_DIST = sugar-marshal.list extensions.override extensions.defs

extensions.c: extensions.defs extensions.override

.defs.c:
	(cd $(srcdir)\
	 && $(PYGTK_CODEGEN) \
	    --register $(PYGTK_DEFSDIR)/gdk-types.defs \
	    --register $(PYGTK_DEFSDIR)/gtk-types.defs \
	    --override $*.override \
	    --prefix py$* $*.defs) > gen-$*.c \
	&& cp gen-$*.c $*.c \
	&& rm -f gen-$*.c
