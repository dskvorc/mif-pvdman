#!/bin/bash

# if free internet available: stream video, else just audio

# test for "internet" and "free"
./pvd_get_by_properties "{\"type\":\"internet\",\"pricing\":\"free\"}" > /dev/null
if [ $? == 0 ]; then
  # such pvd exists; run test in it
  ./pvd_prop_run "{\"type\":\"internet\",\"pricing\":\"free\"}" \
  firefox http://[2001:db8:10::2]/swtrailer.mp4  > /dev/null
else
  # no free internet! is at least internet available?
  ./pvd_get_by_properties "{\"type\":\"internet\"}" > /dev/null
  if [ $? == 0 ]; then
    # pvd with internet exist; run something else in it
    ./pvd_prop_run {\"type\":\"internet\"} \
    firefox http://[2001:db8:20::2]/swtheme.mp3  > /dev/null
  else
    echo "No internet connection available"
    exit 1
  fi
fi

