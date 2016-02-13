//for testing with dbus-service.py or main.py from pvdman

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>
#include <pvd_api.h>

/*
 * usage: ./pvd_prop_run properties command-to-execute [parameters]
 * - propertis must be json string
 * - example: {"type":"internet", "pricing":"free", "name":"default", "id"=...}
 * - use escape sequences on ", eg.:
 *   ../pvd_prop_run {\"type\":\"internet\"} firefox http://www.s1.org/swtrailer.mp4
 */

int main ( int argc, char *argv[] )
{
	int i = 0;
	char *props;
	struct pvd **pvd;
	char *pvd_id;

	if ( argc < 2 ) {
		fprintf ( stderr, "Usage: %s <properties> <command> [arguments]\n",
				argv[0]);
		return -1;
	}

	props = argv[1];

	printf ( "Requesting by properties: %s:\n", props );
	pvd = pvd_get_by_properties ( props );
	if (!pvd)
		return -1; //error connecting to dbus service
	if ( !pvd[0] || pvd[0]->id[0] == 0 ) {
		printf ("No such pvd!\n" );
		return -1;
	}

	pvd_id = pvd[0]->id;

	printf ( "Activating pvd: %s:\n", pvd_id );
	if ( pvd_activate ( pvd_id, getpid() ) == -1 ) {
		printf ( "pvd %s activation error!\n", pvd_id );
		return -1;
	}
	printf ( "pvd %s activated!\n", pvd_id );

	char *args[argc-1];
	printf ( "Executing: " );
	for ( i = 0; i < argc-1; i++ ) {
		args[i] = argv[i+2];
		if ( args[i] )
			printf ( "%s ", args[i] );
	}
	printf ( "\n" );
	args[argc-1] = NULL;
	execvp ( args[0], args );
	perror ( "Error executing execvp" );
	return -1;
	return 0;
}
