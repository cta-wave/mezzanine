#!/usr/bin/python

import argparse
import numpy as np
import os
from pathlib import Path
import scipy.io.wavfile as wav
from scipy import signal

def check_channels(ch):
	int_ch = int(ch)
	if int_ch < 1:
		raise argparse.ArgumentTypeError("%s is an invalid number of channels, must be 1 or greater" % ch)
	return int_ch

"""
Generate an audio stream containing random noise that is band limited to 7 kHz
"""

# Default parameters
channels = 2
max_channels = 2
duration = 60		# [s]
samplerate = 48000	# [Hz]
bw = 7000			# [Hz]

# Basic argument handling
parser = argparse.ArgumentParser(description="WAVE Audio Mezzanine Content Creator.")
	
parser.add_argument(
	'-d', '--duration', 
	required=False, 
	type=int, 
	help="The duration, in seconds, of the audio file generated. Default: "+str(duration))
	
parser.add_argument(
	'-f', '--samplerate', 
	required=False, 
	help="The sample rate, in Hz, of the audio file generated. Default: "+str(samplerate))
	
parser.add_argument(
	'-s', '--seed', 
	required=False, 
	help="A seed for the PRNG used to generate the audio signal. The string provided will be converted into Unicode code values that are concatenated, then converted to int. Default: output filename")

parser.add_argument(
	'-c', '--channels', 
	required=False, 
	type=check_channels,
	help="The number of channels, may be 1 or more. Only the first 2 channels FL/FR will contain audio, others will contain digital silence. Default: "+str(channels))

	
parser.add_argument('output', help="Output file.")
args = parser.parse_args()

# Create output file directory if it does not exist
output = Path(args.output)
if not os.path.isdir(output.parent):
	try:
		Path.mkdir(output.parent, parents=True)
	except OSError:
		print ("Failed to create the directory for output mezzanine stream.")

# Set parameters to values provided in arguments
if args.seed is not None:
	seed = int(''.join(str(ord(c)) for c in args.seed))
else:
	seed = int(''.join(str(ord(c)) for c in output.name))

if args.duration is not None:
	duration = args.duration
	
if args.samplerate is not None:
	samplerate = args.samplerate

if args.channels is not None:
	channels = args.channels

print("channels = "+str(channels))
print("samplerate = "+str(samplerate))
print("duration = "+str(duration))

# Configure random number generator
ss = np.random.SeedSequence(seed)
print('seed = {}'.format(ss.entropy))
bg = np.random.PCG64(ss)
gen = np.random.Generator(bg)

# Generate samples from a uniform distribution
data = gen.uniform(-1,1,duration * samplerate)

# Define filter to band limit the signal; put more emphasis on flatness of passband than on stopband suppression
fc = signal.remez(numtaps = 151, bands = [0,bw,bw+1000,samplerate/2], desired = [1, 0], weight = [4,1], Hz=samplerate)

# Apply filtering
data = signal.lfilter(fc, 1, data)

# Normalize the signal to be within the bounds usable by 16-bit audio
data *= np.iinfo(np.int16).max/max(abs(data))

# Create the output audio data for the chosen number of channels
# Only the first 2 channels FL/FR will contain audio data, all additional channels will contain digital silence
if channels == 1:
	mc_data = np.array(data)
else:
	mc_data_arrays = [data,data]
	if channels > 2:
		silence = [0] * duration * samplerate
		for ch in range(3,channels+1):
			mc_data_arrays.append(silence)
	mc_data_tuples = tuple(mc_data_arrays)
	mc_data = np.vstack(mc_data_tuples)
	mc_data = mc_data.transpose()

# Write audio generated to wave file
wav.write(output, samplerate, mc_data.astype(np.int16))
