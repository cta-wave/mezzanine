#!/usr/bin/env python

"""
This program takes an existing WAVE video mezzanine file (MP4) and an existing WAVE audio mezzanine file (WAV).
It loops the audio mezzanine and replaces the video mezzanine file's audio track with the looped audio.
"""

import argparse
import json
import os
import subprocess
import sys

from pathlib import Path

# Basic argument handling
parser = argparse.ArgumentParser(description="WAVE Mezzanine Audio: looping white noise.")
parser.add_argument('input1', help="Source mezzanine file.")
parser.add_argument('input2', help="Source audio file to loop.")

args = parser.parse_args()

# Check that source files are present
if not os.path.isfile(args.input1):
	sys.exit("Source file \""+args.input1+"\" does not exist.")
if not os.path.isfile(args.input2):
	sys.exit("Source file \""+args.input2+"\" does not exist.")
	
mezzanine = Path(args.input1)
second_audio = Path(args.input2)
mezzanine_out = Path(str(mezzanine.stem)+'_'+str(second_audio.stem)+str(mezzanine.suffix))

print("Creating new mezzanine file using video from "+str(mezzanine)+" and (looped) audio from "+str(second_audio))

# Detect video mezzanine duration
source_videoproperties = subprocess.check_output(
	['ffprobe', '-i', str(mezzanine), '-show_streams', '-select_streams', 'v', '-loglevel', '0', '-print_format', 'json'])
source_videoproperties_json = json.loads(source_videoproperties)
duration = int(source_videoproperties_json['streams'][0]['duration'].split('.')[0])

# Create audio track with the same duration as the video mezzanine by looping audio mezzanine
subprocess.run(['ffmpeg', 
	'-stream_loop', '-1', '-i', str(second_audio), '-t', str(duration),
	'-y',
	str(second_audio.stem)+'_looped.wav'])

# Encode and mux new audio track with video mezzanine 
# ffmpeg -i <mezzanine_file> -i second_audio_looped.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -ac 2 <mezzanine_file_with_new_audio>
subprocess.run(['ffmpeg', 
	'-i', str(mezzanine),
	'-i', str(second_audio.stem)+'_looped.wav',
	'-map', '0:v',
	'-map', '1:a',
	'-c:v','copy',
	'-c:a','aac',
	'-b:a', '320k', '-ac', '2',
	'-y',
	str(mezzanine_out)])
	
os.remove(str(second_audio.stem)+'_looped.wav')
print("Done")
