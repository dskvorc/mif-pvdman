/*
 * Simple UDP echo server (IP version depend by provided IP address/host name)
 *
 * usage: echo_server <local-ip-to-bind-to> <local-port-to-bind-to>
 *
 * examples:
 * $ ./echo_server localhost 20000
 * $ ./echo_server ::1 20000
 * $ ./echo_server fe80::20c:29ff:fe16:a042%eno16777736 20000
 *
 * Check bind address e.g. with: netstat -anpu
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

#define MAXBUF 256

int main(int argc, char **argv)
{
	struct addrinfo hints, *res, *ressave;
	char *host, *port, buf[MAXBUF];
	int sockfd, size, status;
	socklen_t addrlen;
	struct sockaddr *cliaddr;

	if ( argc == 3 ) {
		host=argv[1];
		port=argv[2];
	}
	else {
		printf ( "usage: echo_server <local-host-name-ip> <local-port>\n" );
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
		/* each of the returned IP address is tried */
		sockfd = socket ( res->ai_family, res->ai_socktype, res->ai_protocol );
		if ( sockfd >= 0 && !bind ( sockfd, res->ai_addr, res->ai_addrlen ) )
			break;
		if ( sockfd >= 0 )
			close(sockfd);
		res = res->ai_next;
	}
	if (!res) {
		fprintf ( stderr, "Can't bind to: %s %s\n", host, port );
		return -1;
	}
	addrlen = res->ai_addrlen;
	freeaddrinfo ( ressave );
	cliaddr = malloc(addrlen);

	while (1) {
		size = recvfrom ( sockfd, buf, MAXBUF, 0, cliaddr, &addrlen );
		if ( size < 0 ) {
			perror("recvfrom");
			return -1;
		}
		printf ( "%s", buf ); fflush(stdout);
		if ( sendto ( sockfd, &buf, size, 0, cliaddr, addrlen ) < 0 ) {
			perror("sendto");
			return -1;
		}
	}

	return 0;
}
