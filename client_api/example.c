//for testing with dbus-service.py or main.py from pvdman

#include <stdio.h>
#include <stdlib.h>
#include <pvd_api.h>

int main ()
{
	int i = 0;

	printf ( "Requesting all (*):\n" );
	struct pvd **pvd = pvd_get_by_id ( "*" );

	for (i = 0; pvd[i] != NULL; i++ ) {
		printf ("id:%s policy:%s data:%s\n", pvd[i]->id, pvd[i]->policy, pvd[i]->data );
		free(pvd[i]->id);
		free(pvd[i]->policy);
		free(pvd[i]->data);
		free(pvd[i]);
	}
	free(pvd);

	printf ( "Requesting pvd_id pvd-id-wired-1:\n" );
	pvd = pvd_get_by_id ( "pvd-id-wired-11" );
	for (i = 0; pvd[i] != NULL; i++ ) {
		if ( pvd[i]->id[0] == 0 )
			printf ("No such pvd!\n" );
		else
			printf ("id:%s policy:%s data:%s\n", pvd[i]->id, pvd[i]->policy, pvd[i]->data );
		free(pvd[i]->id);
		free(pvd[i]->policy);
		free(pvd[i]->data);
		free(pvd[i]);
	}
	free(pvd);

	return 0;
}
