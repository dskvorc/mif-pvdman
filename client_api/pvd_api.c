//for testing with dbus-service.py or main.py from pvdman

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <gio/gio.h>

#include <pvd_api.h>

#define  BUS_NAME			"org.freedesktop.PvDManager"
#define  OBJECT_PATH		"/org/freedesktop/PvDManager"
#define  INTERFACE_NAME		"org.freedesktop.PvDManager"

static GDBusConnection *pvd_dbus_connect ()
{
	GDBusConnection *connection;
	GError *error;

	error = NULL;
	connection = g_bus_get_sync ( G_BUS_TYPE_SYSTEM, NULL, &error );
	if (connection == NULL)
	{
		g_printerr ("Error connecting to D-Bus: %s\n", error->message);
		g_error_free (error);
		return NULL;
	}
	return connection;
}

struct pvd **pvd_get_by_id ( const char *pvd_id )
{
	GDBusConnection *connection;
	GError *error;
	GVariant *value;
	GVariantIter *iter;
	const gchar *id, *policy, *data;
	struct pvd **list = NULL;
	int pvds = 0;

	connection = pvd_dbus_connect ();
	if (!connection)
		return NULL;

	error = NULL;
	value = g_dbus_connection_call_sync (
		connection, BUS_NAME, OBJECT_PATH, INTERFACE_NAME,
		"get_by_id",
		g_variant_new ("(s)", pvd_id),
		G_VARIANT_TYPE ("(a(sss))"),
		G_DBUS_CALL_FLAGS_NONE, -1, NULL, &error
	);

	if (value == NULL)
	{
		g_printerr ("Error invoking pvd_get_by_id(): %s\n", error->message);
		g_error_free (error);
		return NULL;
	}

	g_variant_get ( value, "(a(sss))", &iter);
	while ( g_variant_iter_loop ( iter, "(&s&s&s)", &id, &policy, &data ) ) {
		//g_print ("id:%s policy:%s data:%s\n", id, policy, data );
		list = realloc ( list, sizeof(struct pvd *)*(pvds+1) );
		list[pvds] = malloc ( sizeof(struct pvd) );
		list[pvds]->id = strdup ( id );
		list[pvds]->policy = strdup ( policy );
		list[pvds]->data = strdup ( data );
		pvds++;
	}
	g_variant_iter_free (iter);
	g_variant_unref (value);
	g_object_unref(connection);

	list = realloc ( list, sizeof(struct pvd *)*(pvds+1) );
	list[pvds] = NULL;

	return list;
}
