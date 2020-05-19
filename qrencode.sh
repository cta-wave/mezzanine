#!/bin/bash
mkdir -p qr_codes
filename='images-frametimes.txt'
n=1
while IFS=$'\t' read -r -a qrArray ; do
       qrencode -l H -s 6 -o qr_codes/${qrArray[0]} "123456,${qrArray[1]}"
n=$((n+1))
done < $filename