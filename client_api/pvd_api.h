/* PvD API interface */

struct pvd {
	char *id;
	char *ns;
	char *iface;
};

struct pvd **pvd_get_by_id ( const char *pvd_id );
int pvd_activate ( const char *pvd_id, pid_t pid );
