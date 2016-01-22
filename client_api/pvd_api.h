/* PvD API interface */

struct pvd {
	char *id;
	char *policy;
	char *data;
};

struct pvd **pvd_get_by_id ( const char *pvd_id );
