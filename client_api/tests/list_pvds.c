//for testing with dbus-service.py or main.py from pvdman

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>
#include <pvd_api.h>

/* usage: example [pvd-id [command-to-execute [parameters]]] */

int main ( int argc, char *argv[] )
{
	int i = 0;
	char *pvd_id;

	printf ( "Requesting all (*):\n" );
	struct pvd **pvd = pvd_get_by_id ( "*" );

	for (i = 0; pvd[i] != NULL; i++) {
		printf ("id: %s ns:%s iface:%s\n", pvd[i]->id, pvd[i]->ns, pvd[i]->iface );
		printf ("properties: %s\n\n", pvd[i]->properties );
		free(pvd[i]->id);
		free(pvd[i]->ns);
		free(pvd[i]->iface);
		free(pvd[i]->properties);
		free(pvd[i]);
	}
	free(pvd);

	if ( argc > 1 )
		pvd_id = argv[1];
	else
		pvd_id = "pvd-id-wired-1";

	printf ( "Requesting pvd_id: %s:\n", pvd_id );
	pvd = pvd_get_by_id ( pvd_id );
	for (i = 0; pvd[i] != NULL; i++ ) {
		if ( pvd[i]->id[0] == 0 )
			printf ("No such pvd!\n" );
		else
			printf ("id:%s ns:%s iface:%s\n", pvd[i]->id, pvd[i]->ns, pvd[i]->iface );
			printf ("properties: %s\n\n", pvd[i]->properties );
		free(pvd[i]->id);
		free(pvd[i]->ns);
		free(pvd[i]->iface);
		free(pvd[i]);
	}
	free(pvd);

	printf ( "Activating pvd: %s:\n", pvd_id );
	if ( pvd_activate ( pvd_id, getpid() ) == -1 ) {
		printf ( "pvd %s activation error!\n", pvd_id );
		return -1;
	}
	printf ( "pvd %s activated!\n", pvd_id );

	if ( argc > 2 ) {
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

	return 0;
}
