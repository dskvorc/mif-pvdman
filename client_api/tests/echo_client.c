/*
 * Simple UDP echo client (IP version depend by provided IP address/host name)
 *
 * usage: echo_client <remote-server-ip-address> <remote-server-port>
 *
 * examples:
 * $ ./echo_client localhost 20000
 * $ ./echo_client ::1 20000
 * $ ./echo_client fe80::20c:29ff:fe16:a042%eno16777736 20000
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

#define MAXBUF 32

int main(int argc, char **argv)
{
	struct addrinfo hints, *res, *ressave;
	char *host, *port, in_buf[MAXBUF], out_buf[]=".";
	int sockfd, size, status;
	socklen_t addrlen;
	struct sockaddr *serveraddr;

	if ( argc == 3 ) {
		host=argv[1];
		port=argv[2];
	}
	else {
		printf ( "usage: echo_client <remote-host-name-ip> <remote-port>\n" );
		return -1;
	}

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
		/* each of the returned interfaces */
		sockfd = socket ( res->ai_family, res->ai_socktype, res->ai_protocol );
		if ( sockfd >= 0 )
			break;
		res = res->ai_next;
	}
	if ( sockfd < 0 ) {
		fprintf ( stderr, "Can't create socket for remote: %s %s\n", host, port );
		return -1;
	}
	addrlen = res->ai_addrlen;
	serveraddr = malloc(addrlen);
	memcpy ( serveraddr, res->ai_addr, addrlen );
	freeaddrinfo ( ressave );

	while (1) {
		size = sendto ( sockfd, &out_buf, strlen(out_buf)+1, 0, serveraddr, addrlen );
		if ( size < 0 ) {
			perror ("sendto");
			return -1;
		}
		size = recv ( sockfd, in_buf, MAXBUF, 0 );
		if ( size < 0 ) {
			perror("recvfrom");
			return -1;
		}
		printf ( "%s", in_buf ); fflush(stdout);
		sleep(1);
	}

	return 0;
}
