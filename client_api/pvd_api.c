//for testing with dbus-service.py or main.py from pvdman

#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <gio/gio.h>

#include <unistd.h>
#include <sched.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

#include <pvd_api.h>

#define  BUS_NAME       "org.freedesktop.PvDManager"
#define  OBJECT_PATH    "/org/freedesktop/PvDManager"
#define  INTERFACE_NAME "org.freedesktop.PvDManager"
#define  NSFILEBASEDIR  "/var/run/netns/"

static GDBusConnection *connect ()
{
	GDBusConnection *connection;
	GError *error = NULL;
	connection = g_bus_get_sync ( G_BUS_TYPE_SYSTEM, NULL, &error );
	if ( connection == NULL )
	{
		g_printerr ("Error connecting to D-Bus: %s\n", error->message);
		g_error_free (error);
	}
	return connection;
}

GVariant *pvd_call_method ( char *method_name, GVariant *params, const GVariantType *ret_type )
{
	GDBusConnection *connection;
	GError *error;
	GVariant *value;

	connection = connect ();
	if ( connection == NULL )
		return NULL;

	error = NULL;
	value = g_dbus_connection_call_sync (
		connection, BUS_NAME, OBJECT_PATH, INTERFACE_NAME,
		method_name, params, ret_type,
		G_DBUS_CALL_FLAGS_NONE, -1, NULL, &error
	);

	if (value == NULL)
	{
		g_printerr ("Error invoking %s(): %s\n", method_name, error->message);
		g_error_free (error);
	}

	g_object_unref(connection);
	return value;
}

struct pvd **pvd_get_by_id ( const char *pvd_id )
{
	GVariant *value;
	GVariantIter *iter;
	const gchar *id, *ns, *iface, *properties;
	struct pvd **list = NULL;
	int pvds = 0;

	value = pvd_call_method ( "get_by_id", g_variant_new ("(s)", pvd_id),
		G_VARIANT_TYPE ("(a(ssss))") );
	if (!value)
		return NULL;

	g_variant_get ( value, "(a(ssss))", &iter);
	while ( g_variant_iter_loop ( iter, "(&s&s&s&s)", &id, &ns, &iface, &properties ) ) {
		//g_print ("id:%s ns:%s if:%s\n", id, ns, iface );
		list = realloc ( list, sizeof(struct pvd *)*(pvds+1) );
		list[pvds] = malloc ( sizeof(struct pvd) );
		list[pvds]->id = strdup ( id );
		list[pvds]->ns = strdup ( ns );
		list[pvds]->iface = strdup ( iface );
		list[pvds]->properties = strdup ( properties );
		pvds++;
	}
	g_variant_iter_free (iter);
	g_variant_unref (value);

	list = realloc ( list, sizeof(struct pvd *)*(pvds+1) );
	list[pvds] = NULL;

	return list;
}

struct pvd **pvd_get_by_properties ( const char *props )
{
	GVariant *value;
	GVariantIter *iter;
	const gchar *id, *ns, *iface, *properties;
	struct pvd **list = NULL;
	int pvds = 0;

	value = pvd_call_method ( "get_by_id", g_variant_new ("(s)", props),
		G_VARIANT_TYPE ("(a(ssss))") );
	if (!value)
		return NULL;

	g_variant_get ( value, "(a(ssss))", &iter);
	while ( g_variant_iter_loop ( iter, "(&s&s&s&s)", &id, &ns, &iface, &properties ) ) {
		//g_print ("id:%s ns:%s if:%s\n", id, ns, iface );
		list = realloc ( list, sizeof(struct pvd *)*(pvds+1) );
		list[pvds] = malloc ( sizeof(struct pvd) );
		list[pvds]->id = strdup ( id );
		list[pvds]->ns = strdup ( ns );
		list[pvds]->iface = strdup ( iface );
		list[pvds]->properties = strdup ( properties );
		pvds++;
	}
	g_variant_iter_free (iter);
	g_variant_unref (value);

	list = realloc ( list, sizeof(struct pvd *)*(pvds+1) );
	list[pvds] = NULL;

	return list;
}

int pvd_activate ( const char *pvd_id, pid_t pid )
{
	GVariant *value;
	const gchar *id, *ns, *iface, *properties;
	int retval = -1;


	/* 1. retrieve given pvd */
	value = pvd_call_method ( "activate",
		g_variant_new ("(si)", pvd_id, (gint) pid ),
		G_VARIANT_TYPE ("(ssss)") );
	if (!value)
		return retval;

	g_variant_get ( value, "(&s&s&s&s)", &id, &ns, &iface, &properties );
	//g_print ("id:%s ns:%s if:%s\n", id, ns, iface );

	/* 2. if exist, activate it: switch to that namespace */
	if ( id[0] != 0 ){
		char *nsname = malloc ( strlen(NSFILEBASEDIR) + strlen(ns) + 1);
		strcpy ( nsname, NSFILEBASEDIR );
		strcat ( nsname, ns );
		int fd = open ( nsname, O_RDONLY );
		if ( fd != -1 ) {
			retval = setns ( fd, CLONE_NEWNET );
			if ( retval == -1 )
				perror("setns");
		}
		printf ( "nsname=%s fd=%d setns=%d\n", nsname, fd, retval );
		printf ( "properties=%s\n", properties );
	}

	g_variant_unref (value);

	return retval;
}

/* not tested! */
static void _callback ( GDBusConnection *connection,
	const gchar *sender_name, const gchar *object_path,
	const gchar *interface_name, const gchar *signal_name,
	GVariant *parameters, gpointer callback )
{
	GVariant *value;
	const gchar *id;
	void (*cb)(char *);

	cb = callback;
	g_variant_get ( value, "(&s)", &id );

	if ( cb )
		cb ( (char*) id );
}

int pvd_register_signal ( void (*callback) ( char *pvd_id ) )
{
	GDBusConnection *connection;
	guint si;

	connection = connect ();
	if ( connection == NULL )
		return -1;

	si = g_dbus_connection_signal_subscribe ( connection, NULL, INTERFACE_NAME,
		NULL, OBJECT_PATH, NULL, G_DBUS_CALL_FLAGS_NONE, _callback, callback, NULL );
	return si;
}


