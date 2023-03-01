#!/usr/bin/env python

"""
This program accepts a seed parameter and duration and generates binary files of 1/0 PN sequences as used/required
by the CTA WAVE Project.
"""
import argparse
import numpy as np
import os
import scipy.io.wavfile as wav
import time

from pathlib import Path
from scipy import signal


def check_channels(ch):
    int_ch = int(ch)
    if int_ch < 1:
        raise argparse.ArgumentTypeError("%s is an invalid number of channels, must be 1 or greater" % ch)
    return int_ch


print("\n    Begin PNFiles at "+str(time.asctime(time.gmtime()))+'\n')

# Default parameters
channels = 2
duration = 60        # [s]
samplerate = 48000   # [Hz]
bw = 7000            # [Hz]
silentstart = 0

# Basic argument handling for the following: -d -f -s -c output
parser = argparse.ArgumentParser(description="Test of audio PN noise and correlation methods")
parser.add_argument(
    '-d', '--duration', required=False, type=int,
    help="The duration, in seconds, of the audio file generated. Default: "+str(duration))
parser.add_argument(
    '-f', '--samplerate', required=False, type=int,
    help="The sample rate, in Hz, of the audio file generated. Default: "+str(samplerate))
parser.add_argument(
    '-s', '--seed', required=False,
    help="A seed for the PRNG used to generate the audio signal. The string provided will be converted into "
         "Unicode code values that are concatenated, then converted to int. Default: output filename")
parser.add_argument(
    '-c', '--channels', required=False, type=check_channels,
    help="The number of channels, may be 1 or more. Only the first 2 channels FL/FR will contain audio, "
         "others will contain digital silence. Default: "+str(channels))
parser.add_argument(
    '--silentstart', required=False, choices=['0', '1'],
    help="Determines whether the audio file generated has initial silence (=1) or not (=0). "
         "Default: "+str(silentstart))
parser.add_argument('output', help="Output file (fname.ftp).")
args = parser.parse_args()

# Create output file directory if it does not exist
output = Path(args.output)
if not os.path.isdir(output.parent):
    try:
        Path.mkdir(output.parent, parents=True)
    except OSError:
        print("Failed to create the directory for output mezzanine stream.")

# Set parameters to values provided in arguments
if args.seed is not None:
    seed = int(''.join('{0:03n}'.format(ord(c)) for c in args.seed))
else:
    seed = int(''.join('{0:03n}'.format(ord(c)) for c in output.name))
if args.duration is not None:
    duration = args.duration
if args.samplerate is not None:
    samplerate = args.samplerate
if args.channels is not None:
    channels = args.channels
if args.silentstart is not None:
    silentstart = int(args.silentstart)

# Generate a binary noise array from a uniform distribution.  The array ndata is of type ndarray (1-D)
ss = np.random.SeedSequence(seed)
print('seed base = '+args.seed)
print('seed = {}'.format(ss.entropy))
bg = np.random.PCG64(ss)                # bg == Bit Generator
gen = np.random.Generator(bg)           # gen == instance of generator class
ndata = gen.uniform(-1, 1, duration*samplerate)     # duration 60 s, sample rate 48kHz, 2.88M values in a 1-D array

# Filter to band limit the signal; put more emphasis on flatness of passband than on stopband suppression
fc = signal.remez(numtaps=151, bands=[0, bw, bw+1000, samplerate/2], desired=[1, 0], weight=[4, 1], fs=samplerate)
if silentstart >= 1:
    fdata = signal.lfilter(fc, 1, ndata)
else:
    fdata = signal.filtfilt(fc, 1, ndata)

# Normalize the signal to be within the bounds usable by 16-bit audio and convert to int16
fdata *= np.iinfo(np.int16).max/max(abs(fdata))     # scale to int16 range

# Create the output audio data for the chosen number of channels
# Only the first 2 channels FL/FR will contain audio data, all additional channels will contain digital silence
silence = [0] * duration * samplerate
if channels == 1:
    mc_data = np.array(fdata)
else:
    # mc_data_arrays = [fdata, fdata]
    mc_data_arrays = [fdata, silence]
    if channels > 2:
        # silence = [0] * duration * samplerate
        for ch in range(3, channels+1):
            mc_data_arrays.append(silence)
    mc_data_tuples = tuple(mc_data_arrays)
    mc_data = np.vstack(mc_data_tuples)
    mc_data = mc_data.transpose()

# Write audio generated to wave file
wav.write(output, samplerate, mc_data.astype(np.int16))

print("\n    End PNFiles at "+str(time.asctime(time.gmtime())))
