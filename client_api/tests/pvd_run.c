//for testing with dbus-service.py or main.py from pvdman

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>
#include <pvd_api.h>

/* usage: sudo ./example pvd-id command-to-execute [parameters] */

int main ( int argc, char *argv[] )
{
	int i = 0;
	char *pvd_id;

	if ( argc < 3 ) {
		fprintf ( stderr, "Usage: %s <pvd-id> <command> [arguments]\n", argv[0]);
		return -1;
	}

	pvd_id = argv[1];

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
}
