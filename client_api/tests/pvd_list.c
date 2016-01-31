//for testing with dbus-service.py or main.py from pvdman

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>
#include <pvd_api.h>

/* usage: ./example */

int main ( int argc, char *argv[] )
{
	int i = 0;
	struct pvd **pvd;

	printf ( "Requesting all (*):\n" );
	pvd = pvd_get_by_id ( "*" );

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

	return 0;
}
