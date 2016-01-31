INCLUDE = -I./
LIB = pvd
GFLAGS = `pkg-config --cflags --libs gobject-2.0 glib-2.0 gio-2.0`

CFLAGS = -Wall $(INCLUDE)
LDFLAGS = $(LIBPATH) -l$(LIB)

# Build library
PVDLIB = libpvd.a
OBJLIB = pvd_api.o

all: $(PVDLIB) tests

$(PVDLIB): $(OBJLIB)
	ar rcs $@ $^

pvd_api.o: pvd_api.c pvd_api.h
	gcc -c $< -o $@ -I./ -static $(GFLAGS)

.PHONY: tests
tests:
	@cd tests && $(MAKE)

clean:
	@-rm -f $(TARGET) *.o *.a
	@cd tests && $(MAKE) clean
