#!/usr/bin/env python

"""
This program accepts a seed parameter and duration and generates binary files of 1/0 PN sequences as used/required
by the CTA WAVE Project.
"""
import argparse
import hashlib
import json
import numpy as np
import os
import re
import scipy.io.wavfile as wav
import sys
import time

from datetime import date
from json import JSONEncoder
from pathlib import Path
from scipy import signal


class MezzanineProperties:
    channel_count = 0
    bits_per_sample = 0
    sample_rate = 0
    duration = 0
    codec = ''
    
    def __init__(self, channel_count=None, bits_per_sample=None, sample_rate=None, duration=None, codec=None):
        if channel_count is not None:
            self.channel_count = channel_count
        if bits_per_sample is not None:
            self.bits_per_sample = bits_per_sample
        if sample_rate is not None:
            self.sample_rate = sample_rate
        if duration is not None:
            self.duration = duration
        if codec is not None:
            self.codec = codec
    
    def json(self):
        return {
            'channel_count': self.channel_count,
            'bits_per_sample': self.bits_per_sample,
            'sample_rate': self.sample_rate,
            'duration': self.duration,
            'codec': self.codec
        }


class Mezzanine:
    name = ''
    URI = ''
    version = 0
    specification_version = 0
    creation_date = 'YYYY-MM-DD'
    seed = ''
    license = ''
    command_line = ''
    md5 = ''
    properties = MezzanineProperties()
    
    def __init__(self, name=None, uri=None, version=None, specification_version=None,
                 creation_date=None, seed=None, license=None, cl=None,
                 md5=None, properties=None):
        if name is not None:
            self.name = name
        if uri is not None:
            self.URI = uri
        if version is not None:
            self.version = version
        if specification_version is not None:
            self.specification_version = specification_version
        if creation_date is not None:
            self.creation_date = creation_date
        if seed is not None:
            self.seed = seed
        if license is not None:
            self.license = license
        if cl is not None:
            self.command_line = cl
        if md5 is not None:
            self.md5 = md5
        if properties is not None:
            self.properties = properties
    
    def json(self):
        properties = self.properties.json()
        return {
            'Mezzanine': {
                'name': self.name,
                'URI': self.URI,
                'version': self.version,
                'specification_version': self.specification_version,
                'creation_date': self.creation_date,
                'seed': self.seed,
                'license': re.sub(' +', ' ', self.license.replace('\n', ' ')),
                'command_line': self.command_line,
                'md5': self.md5,
                'properties': properties
            }
        }


class MezzanineEncoder(JSONEncoder):
    def default(self, o):
        if "json" in dir(o):
            return o.json()
        return JSONEncoder.default(self, o)


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
mezz_version = 0
mezz_specification_version = 0

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
parser.add_argument(
    '--spec-version',
    required=False,
    type=int,
    help="The version of the mezzanine annotation specification that the mezzanine generated will be compliant with. "
         "Default: "+str(mezz_specification_version))
parser.add_argument(
    '-v', '--version',
    required=False,
    type=int,
    help="The official mezzanine release version that the mezzanine generated are intended for. "
         "Default: "+str(mezz_version))

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
    seed_base = args.seed
    seed = int(''.join('{0:03n}'.format(ord(c)) for c in args.seed))
else:
    seed_base = output.name
    seed = int(''.join('{0:03n}'.format(ord(c)) for c in output.name))
if args.duration is not None:
    duration = args.duration
if args.samplerate is not None:
    samplerate = args.samplerate
if args.channels is not None:
    channels = args.channels
if args.silentstart is not None:
    silentstart = int(args.silentstart)
if args.spec_version is not None:
    mezz_specification_version = args.spec_version
if args.version is not None:
    mezz_version = args.version

# Initialise mezzanine properties metadata
mezz_properties = MezzanineProperties(channels, 16, samplerate, duration, 'Signed Linear PCM')

# Generate a binary noise array from a uniform distribution.  The array ndata is of type ndarray (1-D)
ss = np.random.SeedSequence(seed)
print('seed base = '+seed_base)
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

# Output metadata
# Import CTA mezzanine license if available
mezz_license = ""
try:
    mezz_license_file = open(str(Path('audiomezz_CTA_LICENSE.txt')), encoding="utf-8")
    mezz_license = mezz_license_file.read()
    mezz_license_file.close()
except OSError:
    print("Failed to load mezzanine CTA LICENSE file. Ensure the file is located in the same folder as this script "
        "with the name audiomezz_CTA_LICENSE.txt.")

# Calculate MD5 hash
BLOCK_SIZE = 65536
mezz_file_hash = hashlib.md5()
with open(output, 'rb') as mezz_file:
    mezz_file_block = mezz_file.read(BLOCK_SIZE)
    while len(mezz_file_block) > 0: 					# Until all data has been read from mezzanine file
        mezz_file_hash.update(mezz_file_block) 			# Update hash
        mezz_file_block = mezz_file.read(BLOCK_SIZE) 	# Read the next block from mezzanine file

mezz_metadata = Mezzanine(output.stem, './'+output.name, mezz_version, mezz_specification_version, date.today().isoformat(),
                          seed_base, mezz_license, str(Path(__file__).resolve().name)+' '+' '.join(sys.argv[1:]), mezz_file_hash.hexdigest(), mezz_properties)

print()
print("Name: "+mezz_metadata.name)
print("URI: "+mezz_metadata.URI)
print("Version: "+str(mezz_metadata.version))
print("Spec version: "+str(mezz_metadata.specification_version))
print("Creation date: "+mezz_metadata.creation_date)
print("Seed: "+str(mezz_metadata.seed))
print("License: "+mezz_metadata.license)
print("CL used: "+mezz_metadata.command_line)
print("MD5: "+mezz_metadata.md5)
print()
print("Channel count: "+str(mezz_metadata.properties.channel_count))
print("Bits per sample: "+str(mezz_metadata.properties.bits_per_sample))
print("Sample rate: "+str(mezz_metadata.properties.sample_rate))
print("Duration: "+str(mezz_metadata.properties.duration))
print("Codec: "+mezz_metadata.properties.codec)
print()

# Save metadata to JSON file
mezz_metadata_filepath = Path(str(output.parent)+'\\'+str(output.stem)+'.json')
mezz_metadata_file = open(str(mezz_metadata_filepath), "w")
json.dump(mezz_metadata, mezz_metadata_file, indent=4, cls=MezzanineEncoder)
mezz_metadata_file.write('\n')
mezz_metadata_file.close()

print("Mezzanine metadata stored in: "+str(mezz_metadata_filepath))

print("\n    End PNFiles at "+str(time.asctime(time.gmtime())))
