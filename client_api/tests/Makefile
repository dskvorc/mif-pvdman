INCLUDE = -I../
LIBPATH = -L../
LIB = pvd
GFLAGS = `pkg-config --cflags --libs gobject-2.0 glib-2.0 gio-2.0`
CFLAGS = -Wall $(INCLUDE)
LDFLAGS = $(LIBPATH) -l$(LIB) $(GFLAGS)

#TARGETS = pvd_list pvd_run pvd_get_by_id pvd_get_by_properties
SOURCES := $(wildcard *.c)
TARGETS := $(SOURCES:.c=)
all: $(TARGETS)

$(TARGETS):
	gcc $@.c -o $@ $(CFLAGS) $(LDFLAGS) $(GFLAGS)

clean:
	@-rm -f $(TARGETS) *.o *.a
