#!/bin/sh
cd ../astron

while true
do    
    # This assumes that your astrond build is located in the
    # "astron" directory, and is named "astrond-linux".
    ./astrond-linux --loglevel info config/astrond.yml
    sleep 5
done
