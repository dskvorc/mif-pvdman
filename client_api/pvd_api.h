/* PvD API interface */

struct pvd {
	char *id;
	char *ns;
	char *iface;
	char *properties;
};

struct pvd **pvd_get_by_id ( const char *pvd_id );
struct pvd **pvd_get_by_properties ( const char *props );
int pvd_activate ( const char *pvd_id, pid_t pid );
