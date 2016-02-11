#!/bin/bash

# Update values here!

# assuming: DEV0 - general internet access - not to be used during test
#           DEV1, DEV2 - for tests, have assigned link-local IPv6 addresses
DEV0=eno16777736 # device that should be turned off during tests
DEV1=eno33554984 # first device used in tests

# IP addresses
IP1="2001:db8:10::2/64"   # for DEV1
ROUTE1="/sbin/ip -6 route add 2001:db8::/32 via 2001:db8:10::1"

# pvd properties
PVD_1_ID="implicit"
PVD_1_TYPE="[\"internet\", \"wired\"]"
PVD_1_NAME="Home internet access"
PVD_1_BANDWITH="10 Mbps"
PVD_1_PRICING="free"

PVD_2_ID="f037ea62-ee4f-44e4-825c-16f2f5cc9b3f"
PVD_2_TYPE="[\"iptv\", \"wired\"]"
PVD_2_NAME="TV"
PVD_2_BANDWITH="10 Mbps"
PVD_2_PRICING="free"
