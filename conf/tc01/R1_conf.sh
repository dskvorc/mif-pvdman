#!/bin/bash

# Update values here!

# assuming: DEV0 - general internet access - not to be used during test
#           DEV1, DEV2 - for tests, have assigned link-local IPv6 addresses
DEV0=eno16777736 # device that should be turned off during tests
DEV1=eno33554984 # first device used in tests
DEV2=eno50332208 # second device usen in tests (empty if not used)

# IP addresses
IP1="2001:db8:1::1/48"   # for DEV1
IP2="2001:db8:10::1/64"  # for DEV2

# radvd configuration
PVD_1_ID="implicit"
PVD_1_PREFIX="2001:db8:1:1::/64"
PVD_1_ROUTE="2001:db8:1:1::/64"
PVD_1_DNSSL="www.example-1.hr example-1.hr"
PVD_1_RDNSS="2001:db8:1::1 2001:db8:10::2"
PVD_2_ID="f037ea62-ee4f-44e4-825c-16f2f5cc9b3f"
PVD_2_PREFIX="2001:db8:1:2::/64"
PVD_2_ROUTE="2001:db8:1:2::/64"
PVD_2_DNSSL="www.example-10.hr example-10.hr"
PVD_2_RDNSS="2001:db8:1::1 2001:db8:10::2"

# pvd properties
PVD_1_TYPE="[\"internet\", \"wired\"]"
PVD_1_NAME="Home internet access"
PVD_1_BANDWITH="10 Mbps"
PVD_1_PRICING="free"

PVD_2_TYPE="[\"iptv\", \"wired\"]"
PVD_2_NAME="TV"
PVD_2_BANDWITH="10 Mbps"
PVD_2_PRICING="free"
