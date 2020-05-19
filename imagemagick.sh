#!/bin/bash
maxPngs=$(wc -l < images-frametimes.txt)
for i in $(seq ${maxPngs}); do 
       if [ $(($i % 2)) == 0 ]
       then
              composite -geometry +130+550 qr_codes/${i}.png frames/${i}.png composited/${i}.png; 
       else
              composite -geometry +130+320 qr_codes/${i}.png frames/${i}.png composited/${i}.png;
       fi
done