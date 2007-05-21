sugardir = $(pkgdatadir)/shell/extensions
sugar_PYTHON =		\
	__init__.py

pkgpyexecdir = $(pkgdatadir)/shell/extensions

pkgpyexec_LTLIBRARIES = _extensions.la

_extensions_la_LDFLAGS = -module -avoid-version

_extensions_la_CFLAGS =				\
	$(PYTHON_INCLUDES)			\
	$(SHELL_CFLAGS)				\
	-I$(top_srcdir)/shell/extensions

_extensions_la_LIBADD = 	\
	$(SHELL_LIBS) 		\
	-lgstinterfaces-0.10	\
	-lgstaudio-0.10

_extensions_la_SOURCES =	\
	$(BUILT_SOURCES)	\
	eggaccelerators.h	\
	eggaccelerators.c	\
	sugar-audio-manager.c	\
	sugar-audio-manager.h	\
	sugar-key-grabber.h	\
	sugar-key-grabber.c	\
	_extensionsmodule.c

BUILT_SOURCES = 		\
	_extensions.c		\
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

EXTRA_DIST = sugar-shell-marshal.list _extensions.override _extensions.defs

extensions.c: _extensions.defs _extensions.override

.defs.c:
	(cd $(srcdir)\
	 && $(PYGTK_CODEGEN) \
	    --register $(PYGTK_DEFSDIR)/gdk-types.defs \
	    --register $(PYGTK_DEFSDIR)/gtk-types.defs \
	    --override $*.override \
	    --prefix py$* $*.defs) > gen-$*.c \
	&& cp gen-$*.c $*.c \
	&& rm -f gen-$*.c
