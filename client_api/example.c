//for testing with dbus-service.py or main.py from pvdman

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>
#include <pvd_api.h>

int main ()
{
	int i = 0;

	printf ( "Requesting all (*):\n" );
	struct pvd **pvd = pvd_get_by_id ( "*" );

	for (i = 0; pvd[i] != NULL; i++ ) {
		printf ("id:%s ns:%s iface:%s\n", pvd[i]->id, pvd[i]->ns, pvd[i]->iface );
		free(pvd[i]->id);
		free(pvd[i]->ns);
		free(pvd[i]->iface);
		free(pvd[i]);
	}
	free(pvd);

	char pvd_id[] = "pvd-id-wired-1";
	printf ( "Requesting pvd_id: %s:\n", pvd_id );
	pvd = pvd_get_by_id ( pvd_id );
	for (i = 0; pvd[i] != NULL; i++ ) {
		if ( pvd[i]->id[0] == 0 )
			printf ("No such pvd!\n" );
		else
			printf ("id:%s ns:%s iface:%s\n", pvd[i]->id, pvd[i]->ns, pvd[i]->iface );
		free(pvd[i]->id);
		free(pvd[i]->ns);
		free(pvd[i]->iface);
		free(pvd[i]);
	}
	free(pvd);

	if ( pvd_activate ( pvd_id, getpid() ) != -1 )
		printf ( "pvd %s activated!\n", pvd_id );
	else
		printf ( "pvd %s activation error!\n", pvd_id );

	return 0;
}
