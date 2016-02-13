/*
 * MIF application that use two PvDs simultaneously
 *
 * Two echo servers should be running, accessible from different PvDs
 *
 * usage: multi_pvd_echo_client pvd1 server1 port1 pvd2 server2 port2
 *
 * example:
 * $ ./multi_pvd_echo_client \
     f037ea62-ee4f-44e4-825c-16f2f5cc9b3f 2001:db8:10::2 20000 \
     f037ea62-ee4f-44e4-825c-16f2f5cc9b3e 2001:db8:20::2 20000
 */

#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <sys/time.h>
#include <sys/times.h>
#include <signal.h>
#include <pvd_api.h>

#define MAXBUF 32

int open_socket (char *host, char *port, struct sockaddr **addr, socklen_t *len)
{
	struct addrinfo hints, *res, *ressave;
	int sockfd, status;

	bzero ( &hints, sizeof(struct addrinfo) );
	hints.ai_flags = AI_PASSIVE;
	hints.ai_family = AF_UNSPEC; //AF_INET6;
	hints.ai_socktype = SOCK_DGRAM;
	hints.ai_protocol = IPPROTO_UDP;

	if ( ( status = getaddrinfo ( host, port, &hints, &res ) ) != 0 ) {
		perror ("getaddrinfo");
		return -1;
	}
	ressave = res;
	while (res) {
		sockfd = socket ( res->ai_family, res->ai_socktype, res->ai_protocol );
		if ( sockfd >= 0 )
			break;
		res = res->ai_next;
	}
	if ( sockfd < 0 ) {
		fprintf ( stderr, "Can't create socket for remote: %s %s\n", host, port );
		return -1;
	}
	*len = res->ai_addrlen;
	*addr = malloc(res->ai_addrlen);
	memcpy ( *addr, res->ai_addr, res->ai_addrlen );
	freeaddrinfo ( ressave );

	return sockfd;
}

int main ( int argc, char **argv )
{
	char in_buf[MAXBUF], out_buf1[]="1", out_buf2[]="2";
	int sock1, sock2, size;
	socklen_t len1, len2;
	struct sockaddr *server1, *server2;
	char *pvd1, *host1, *port1, *pvd2, *host2, *port2;

	if ( argc != 7 ) {
		printf ( "usage: multi_pvd_echo_client "
				"pvd1 server1 port1 pvd2 server2 port2\n" );
		return -1;
	}
	pvd1 = argv[1]; host1 = argv[2]; port1 = argv[3];
	pvd2 = argv[4]; host2 = argv[5]; port2 = argv[6];

	/* activate first PvD; create socket in it */
	if ( pvd_activate ( pvd1, getpid() ) == -1 ) {
		printf ( "pvd %s activation error!\n", pvd1 );
		return -1;
	}
	sock1 = open_socket ( host1, port1, &server1, &len1 );
	if ( sock1 == -1 )
		return -1;

	/* activate second PvD; create socket in it */
	if ( pvd_activate ( pvd2, getpid() ) == -1 ) {
		printf ( "pvd %s activation error!\n", pvd2 );
		return -1;
	}
	sock2 = open_socket ( host2, port2, &server2, &len2 );
	if ( sock2 == -1 )
		return -1;

	/* send to both */
	while (1) {
		size = sendto ( sock1, &out_buf1, strlen(out_buf1)+1, 0, server1, len1 );
		if ( size < 0 ) { perror ("sendto"); return -1; }
		size = sendto ( sock2, &out_buf2, strlen(out_buf2)+1, 0, server2, len2 );
		if ( size < 0 ) { perror ("sendto"); return -1; }

		size = recv ( sock1, in_buf, MAXBUF, 0 );
		if ( size < 0 ) { perror("recvfrom"); return -1; }
		printf ( "%s", in_buf ); fflush(stdout);

		size = recv ( sock2, in_buf, MAXBUF, 0 );
		if ( size < 0 ) { perror("recvfrom"); return -1; }
		printf ( "%s", in_buf ); fflush(stdout);

		sleep(1);
	}

	return 0;
}
