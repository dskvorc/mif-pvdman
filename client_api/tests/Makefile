INCLUDE = -I../
LIBPATH = -L../
LIB = pvd
GFLAGS = `pkg-config --cflags --libs gobject-2.0 glib-2.0 gio-2.0`
CFLAGS = -Wall $(INCLUDE)
LDFLAGS = $(LIBPATH) -l$(LIB) $(GFLAGS)

PVDLIB = ../libpvd.a

SOURCES := $(wildcard *.c)
TARGETS := $(SOURCES:.c=)

all: $(PVDLIB) $(TARGETS)

define COMPILE
$(2): $(1)
	gcc $$< -o $$@ $(CFLAGS) $(LDFLAGS) $(GFLAGS)
endef
$(foreach var,$(SOURCES),$(eval $(call COMPILE,$(var),$(var:.c=))))

clean_local:
	@-rm -f $(TARGETS) *.o *.a

clean: clean_local
	@cd .. && $(MAKE) clean_local

$(PVDLIB):
	@cd .. && $(MAKE)