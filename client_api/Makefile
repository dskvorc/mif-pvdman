TARGET = example
INCLUDE = -I./
LIBPATH = -L./
LIB = pvd
FIXME = `pkg-config --cflags --libs gobject-2.0 glib-2.0 gio-2.0`

CFLAGS = -Wall $(INCLUDE)
LDFLAGS = $(LIBPATH) -l$(LIB)

# Required library
REQLIB = libpvd.a

$(TARGET): $(TARGET).c $(REQLIB)
	gcc $< -o $@ $(CFLAGS) $(LDFLAGS) $(FIXME)

# Build library
PVDLIB = libpvd.a
OBJLIB = pvd_api.o

$(PVDLIB): $(OBJLIB)
	ar rcs $@ $^

pvd_api.o: pvd_api.c pvd_api.h
	gcc -c $< -o $@ -I./ -static `pkg-config --cflags --libs gobject-2.0 glib-2.0 gio-2.0`

clean:
	@-rm -f $(TARGET) *.o *.a
