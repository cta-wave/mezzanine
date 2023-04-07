#!/usr/bin/env python

import argparse
import json
import os
import sys

from pathlib import Path

WAVE_MEZZ_RELEASES_URL = 'https://dash-large-files.akamaized.net/WAVE/Mezzanine/releases/'
FILE_WAV = '.wav'
FILE_JSON = '.json'

adb_json_filename = 'audio_mezzanine_database.json'
adb_json = {'audio':{}}

# Basic argument handling
parser = argparse.ArgumentParser(description="WAVE Audio Mezzanine JSON DB Creator.")
parser.add_argument('path', help="Path to folder containing audio mezzanine files.")

args = parser.parse_args()
	
if os.path.isdir(str(Path(args.path))):
	mezz_path = Path(args.path)
else:
	sys.exit('Invalid path to audio mezzanine files: ' + str(args.path))

print('Searching for all audio mezzanine files...')
wav_files = os.listdir(str(mezz_path))
for wav in wav_files:
	if wav.startswith('PN') and wav.endswith(FILE_WAV):
		print('Audio mezzanine found: ' + wav)
		wav_json_file_path = Path(str(mezz_path) + '/' + wav[:-4]+FILE_JSON)
		if os.path.isfile(str(wav_json_file_path)):
			wav_json_file = open(wav_json_file_path)
			wav_json = (json.load(wav_json_file))
			wav_json_file.close()
			print('Corresponding metadata found: ' + str(wav_json_file_path))
			mezz_version = wav_json['Mezzanine']['version']
			print('Mezzanine release version: ' + str(mezz_version))
		else:
			sys.exit('JSON metadata missing for ' + wav + '. Ensure JSON metadata files are in the same folder as their correponding audio mezzanine files.' )

		adb_json['audio'][wav[:-4]] = {'path': WAVE_MEZZ_RELEASES_URL+str(mezz_version)+'/'+wav, 'json_path': WAVE_MEZZ_RELEASES_URL+str(mezz_version)+'/'+wav[:-4]+FILE_JSON}
			
# Save metadata to JSON file
adb_json_filepath = str(mezz_path) + '/' + adb_json_filename
adb_json_file = open(adb_json_filepath, "w")
json.dump(adb_json, adb_json_file, indent=4)
adb_json_file.write('\n')
adb_json_file.close()

print("Audio mezzanine JSON database saved: "+str(adb_json_filepath))
print()
