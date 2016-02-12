//for testing with dbus-service.py or main.py from pvdman

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>
#include <pvd_api.h>

/* usage: sudo ./example pvd-id */

int main ( int argc, char *argv[] )
{
	int i = 0;
	char *pvd_id;
	struct pvd **pvd;

	if ( argc < 2 ) {
		fprintf ( stderr, "Usage: %s <pvd-id>", argv[0]);
		return -1;
	}

	pvd_id = argv[1];

	printf ( "Requesting pvd_id: %s:\n", pvd_id );
	pvd = pvd_get_by_id ( pvd_id );

	if (!pvd)
		return -1; //error connecting to dbus service

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

	return 0;
}
