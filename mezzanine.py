#!/usr/bin/env python

import argparse
import errno
import hashlib
import json
import math
import os
import re
import subprocess
import sys

import qrcode

from bp_gen.bitpattern import bp_create
from datetime import date
from decimal import *
from json import JSONEncoder
from pathlib import Path
from shutil import which


class MezzanineProperties:
	width = 0
	height = 0
	frame_rate = 0
	scan = ''
	pixel_format = ''
	bit_depth = 8
	color_primaries = ''
	transfer_characteristics = ''
	matrix_coefficients = ''
	range = ''
	duration = 0
	frame_count = 0
	start_frame = 0
	start_indicator = False
	end_indicator = False
	qr_positions = 0
	label = ''
	codec = ''
	
	def __init__(self, width=None, height=None, frame_rate=None, scan=None, pixel_format=None, bit_depth=None, 
				color_primaries=None, transfer_characteristics=None, matrix_coefficients=None, range=None,
				duration=None, frame_count=None, start_frame=None, start_indicator=None, end_indicator=None, 
				qr_positions=None, label=None, codec=None):
		if width is not None:
			self.width = width
		if height is not None:
			self.height = height
		if frame_rate is not None:
			self.frame_rate = frame_rate
		if scan is not None:
			self.scan = scan
		if pixel_format is not None:
			self.pixel_format = pixel_format
		if bit_depth is not None:
			self.bit_depth = bit_depth
		if color_primaries is not None:
			self.color_primaries = color_primaries
		if transfer_characteristics is not None:
			self.transfer_characteristics = transfer_characteristics
		if matrix_coefficients is not None:
			self.matrix_coefficients = matrix_coefficients
		if range is not None:
			self.range = range
		if duration is not None:
			self.duration = duration
		if frame_count is not None:
			self.frame_count = frame_count
		if start_frame is not None:
			self.start_frame = start_frame
		if start_indicator is not None:
			self.start_indicator = start_indicator
		if end_indicator is not None:
			self.end_indicator = end_indicator
		if qr_positions is not None:
			self.qr_positions = qr_positions
		if label is not None:
			self.label = label
		if codec is not None:
			self.codec = codec

	def json(self):
		return {
			'width': self.width,
			'height': self.height,
			'frame_rate': self.frame_rate,
			'scan': self.scan,
			'pixel_format': self.pixel_format,
			'bit_depth': self.bit_depth,
			'color_primaries': self.color_primaries,
			'transfer_characteristics': self.transfer_characteristics,
			'matrix_coefficients': self.matrix_coefficients,
			'range': self.range,
			'duration': self.duration,
			'frame_count': self.frame_count,
			'start_frame': self.start_frame,
			'start_indicator': self.start_indicator,
			'end_indicator': self.end_indicator,
			'qr_positions': self.qr_positions,
			'label': self.label,
			'codec': self.codec
		}


class MezzanineSource:
	name = ''
	URI = ''
	license = ''

	def __init__(self, name=None, uri=None, license=None):
		if name is not None:
			self.name = name
		if uri is not None:
			self.URI = uri
		if license is not None:
			self.license = license
			
	def json(self):
		return {
			'name': self.name,
			'URI': self.URI,
			'license': re.sub(' +', ' ', self.license.replace('\n', ' '))
		}


class Mezzanine:
	name = ''
	URI = ''
	version = 0
	specification_version = 0
	creation_date = 'YYYY-MM-DD'
	license = ''
	command_line = ''
	ffmpeg_command_line = ''
	md5 = ''
	properties = MezzanineProperties()
	source = MezzanineSource()
	
	def __init__(self, name=None, version=None, specification_version=None, 
				creation_date=None, license=None, uri=None, cl=None, ffmpeg_cl=None,
				md5=None, properties=None, source=None):
		if name is not None:
			self.name = name
		if version is not None:
			self.version = version
		if specification_version is not None:
			self.specification_version = specification_version
		if creation_date is not None:
			self.creation_date = creation_date
		if license is not None:
			self.license = license
		if uri is not None:
			self.URI = uri
		if cl is not None:
			self.command_line = cl
		if ffmpeg_cl is not None:
			self.ffmpeg_command_line = ffmpeg_cl
		if md5 is not None:
			self.md5 = md5
		if properties is not None:
			self.properties = properties
		if source is not None:
			self.source = source
			
	def json(self):
		properties = self.properties.json()
		source = self.source.json()
		return {
			'Mezzanine': {
				'name': self.name,
				'URI': self.URI,
				'version': self.version,
				'specification_version': self.specification_version,
				'creation_date': self.creation_date,
				'license': re.sub(' +', ' ', self.license.replace('\n', ' ')),
				'command_line': self.command_line,
				'ffmpeg_command_line': self.ffmpeg_command_line,
				'md5': self.md5,
				'properties': properties,
				'source': source
			}
		}


class MezzanineEncoder(JSONEncoder):
	def default(self, o):
		if "json" in dir(o):
			return o.json()
		return JSONEncoder.default(self, o)


# Video output encoding presets
H264 = ['libx264', '-preset', 'slower', '-crf', '5']
H265 = ['libx265', '-preset', 'slower', '-crf', '5']


# Check FFMPEG and FFPROBE are installed
if which('ffmpeg') is None:
	sys.exit("FFMPEG was not found, ensure FFMPEG is added to the system PATH or is in the same folder as this script.")
if which('ffprobe') is None:
	sys.exit("FFMPEG was not found, ensure FFPROBE is added to the system PATH or is in the same folder as this script.")


# Default parameters
# General mezzanine defaults
duration = 60
font = 'monospace'
frame_number_padding = 7
framerate = '30'
label = 'mezz'
resolution = '1920x1080'
seek = '00:00:00.000'
start_frame = 1 	# Set to 0 or 1. Determines starting point for annotations,
					# i.e. frame 0 00:00:00 or frame 1 00:00:<frame duration>
width = '' 		# Extracted from resolution string, see below
height = '' 	# Extracted from resolution string, see below

# Audio defaults
audio_samplerate = 48000 	# Fixed audio sample rate in Hz (set to 0 to use source audio sample rate)

# AV-sync flashes
avsync_pattern_window_len = '5'
avsync_metadata_filepath = Path('avsyncmetadata.json')
beep_file = 'beeps.wav'
beep_audio_samplerate = '48000'
flash_file_dir = Path('_tmp_flash')
test_sequence_gen_script = Path('test_sequence_gen/src/generate.py')  # Script used to generate AV-sync flashes & beeps

# Bit pattern
bitpat_file_dir = Path('_tmp_bp')

# Boundary indicators
boundaries = Path('assets/boundaries.png')

# Metadata
metadata_gen_only = False 	# Flag to disable content generation and only (re)generate the JSON metadata.
							# The source and output mezzanine files must both be present.
mezz_version = 0
mezz_specification_version = 0
metadata_properties_range = {
	'unknown': "unknown", 'unspecified': "unknown",
	'limited': "limited", 'tv': "limited", 'mpeg': "limited",
	'full': "full", 'pc': "full", 'jpeg': "full"} 	# Mapping source range terminology to unknown/limited/full
mezz_source_cdn_path = 'https://dash-large-files.akamaized.net/WAVE/Original/' 	# Mezzanine source file URI prefix
output_video_codec_name = {
	'libx264': "H.264",
	'libx265': "H.265",
	'prores': "ProRes",
	'prores-aw': "ProRes", 'prores-ks': "ProRes"} 	# Mapping between encoder and codec for metadata output

# Output video encoding command line
output_video_encoding_cl = H265		# Defined based on original source content colorspace, default H.265/HEVC
output_video_encoding_selection = {
	'bt2020nc': H265, 'bt709': H264,
	'bt470bg': H264, 'smpte170m': H264} 	# Mapping between source content colorspace and output video codec

# QR codes
qr_file_dir = Path('_tmp_qr')
qr_positions = 4

# Start/end indicator frame configuration
start_indicator_nb_frames = 0		# Number of frames used for the start indicator,
									# default 0, value is calculated based on start/end indicator argument
end_indicator_nb_frames = 0			# Number of frames used for the end indicator,
									# default 0, value is calculated based on start/end indicator argument
start_end_indicators = 'disabled'
start_end_indicator_nb_frames = 1 	# Number of indicator frames to insert at the start and/or end
start_end_indicators_cl = [] 		# Input content ffmpeg parameters,
									# depends on whether start_end_indicators are included or not
start_end_indicators_vmix_cl = '[content_video] concat=n=1:v=1:a=0 [video_with_start_indicator]; ' \
								'[bg_video][video_with_start_indicator] overlay=[main_video];'
								# Video mixing ffmpeg parameters,
								# depends on whether start_end_indicators are included or not
start_end_indicators_amix_cl = '[audio_with_avsync] concat=n=1:v=0:a=1 [aout]'
								# Audio mixing ffmpeg parameters,
								# depends on whether start_end_indicators are included or not
start_indicator_offset = 0			# Defines the time offset for the start of the content
									# when showing a start indicator, else 0
start_indicator_color = '0x006400' 	# Color in hexadecimal 0xRRGGBB
end_indicator_color = '0x8B0000' 	# Color in hexadecimal 0xRRGGBB

# Tone-mapping
tonemap = 'disabled'
tonemap_cl = ''
tonemap_cl_hdr2sdr = 'zscale=transfer=linear,tonemap=hable:desat=0,zscale=transfer=709,'
					# Rudimentary tone mapping to BT.709 SDR from BT.2020 HDR
tonemap_cl_non709 = 'zscale=primaries=709,zscale=matrix=709,zscale=transfer=709,' 	# Rudimentary conversion to BT.709


# Basic argument handling
parser = argparse.ArgumentParser(description="WAVE Mezzanine Content Creator.")

parser.add_argument(
	'-b', '--boundaries', 
	required=False, 
	help="Specifies a file that contains boundary markers. Default: "+str(boundaries))
	
parser.add_argument(
	'-d', '--duration', 
	required=False, 
	type=float, 
	help="The duration, in seconds, of the source file to process from the seek position in. Default: "+str(duration))
	
parser.add_argument(
	'-f', '--framerate', 
	required=False, 
	help="The target framerate of the output file. "
		 "Fractional rates must be specified as division operations \"30000/1001\". Default: "+framerate)
	
parser.add_argument(
	'--frame-number-padding', 
	required=False, 
	type=int, 
	help="The amount of zero padding to use when displaying the current frame number. Default: "+str(frame_number_padding))
	
parser.add_argument(
	'-l', '--label', 
	required=False, 
	help="Provide a label for this mezzanine, will exist in qrcodes and on-screen. Default: "+label)

parser.add_argument(
	'-m', '--metadata-only', 
	required=False, 
	choices=['enabled', 'disabled'],
	help="Disables mezzanine generation and only (re)generates JSON metadata using an existing mezzanine file. "
		 "The source and output mezzanine files must both be present at the paths provided. "
		 "May be \"enabled\" or \"disabled\". Default: disabled")

parser.add_argument(
	'-q', '--qr-positions', 
	required=False, 
	type=int, choices=[2, 4],
	help="The number of on-screen QR code positions to use, may be 2 or 4. Default: "+str(qr_positions))
	
parser.add_argument(
	'-r', '--resolution', 
	required=False, 
	help="The target resolution of the output, video will be scaled and padded to fit resolution. "
		 "Should be specified as \"<width>x<height>\". Default: "+resolution)

parser.add_argument(
	'-s', '--seek', 
	required=False, 
	help="Seeks the source file to a starting position. Format must follow ffmpeg -ss parameter. Default: "+seek)

parser.add_argument(
	'--spec-version', 
	required=False, 
	type=int, 
	help="The version of the mezzanine annotation specification that the mezzanine generated will be compliant with. "
		 "Default: "+str(mezz_specification_version))

parser.add_argument(
	'--start-end-indicators', 
	required=False, 
	choices=['enabled', 'disabled', 'start', 'end'],
	help="Append a single frame before and after the source content, to signal the start and end of the test sequence. "
		 "May be \"enabled\", \"disabled\", \"start\" (only) or \"end\" (only). Default: disabled")
	
parser.add_argument(
	'-t', '--font', 
	required=False, 
	help="The font to utilize for drawing timecodes on frames, must be full path to file. Default: "+font)

parser.add_argument(
	'--tonemap', 
	required=False, 
	choices=['enabled', 'disabled'],
	help="Enables rudimentary tone mapping of BT.2020nc HDR content to BT.709 SDR. Forces output in H.264/AVC. "
		 "May be \"enabled\" or \"disabled\". Default: disabled")

parser.add_argument(
	'-v', '--version', 
	required=False, 
	type=int, 
	help="The official mezzanine release version that the mezzanine generated are intended for. "
		 "Default: "+str(mezz_version))

parser.add_argument(
	'-w', '--window-len', 
	required=False, 
	help="Unique pattern window length (in seconds). Beep/flash sequence will repeat after 2^n -1 seconds. "
		 "Default is "+avsync_pattern_window_len+", meaning the sequence repeats after "
		 + str(2**int(avsync_pattern_window_len)-1)+" seconds.")

parser.add_argument('input', help="Source file.")
parser.add_argument('output', help="Output file.")

args = parser.parse_args()


# Set parameters to values provided in arguments
if args.window_len is not None:
	avsync_pattern_window_len = args.window_len

if args.boundaries is not None:
	boundaries = Path(args.boundaries)

if args.duration is not None:
	duration = args.duration

if args.font is not None:
	font = Path(args.font)

if args.frame_number_padding is not None:
	frame_number_padding = args.frame_number_padding

if args.framerate is not None:
	framerate = args.framerate

if args.label is not None:
	label = args.label

if args.metadata_only is not None:
	if args.metadata_only == 'enabled':
		metadata_gen_only = True

if args.qr_positions is not None:
	qr_positions = args.qr_positions

if args.resolution is not None:
	resolution = args.resolution

if args.seek is not None:
	seek = args.seek
	
if args.spec_version is not None:
	mezz_specification_version = args.spec_version
	
if args.start_end_indicators is not None:
	start_end_indicators = args.start_end_indicators

if args.tonemap is not None:
	tonemap = args.tonemap

if args.version is not None:
	mezz_version = args.version

# Check that source, boundaries and font files are present
input = Path(args.input)
if not os.path.isfile(input):
	sys.exit("Source file \""+str(input)+"\" does not exist.")
	
if not os.path.isfile(boundaries):
	sys.exit("Boundaries image file \""+str(boundaries)+"\" does not exist.")
	
if not os.path.isfile(font):
	sys.exit("Font file \""+str(font)+"\" does not exist.")
else:
	# Font file path formatting to accommodate ffmpeg/fontconfig required syntax 
	if str(font)[1:3] == ':\\':
		font = str(font).replace('\\', '/').replace(':', '\\:')
	elif str(font)[0] != ('\\' and '/' and '.'):
		font = './'+str(font).replace('\\', '/')
	elif str(font)[0] == ('/' or '\\'):
		font = '.'+str(font).replace('\\', '/')

# Create output file directory if it does not exist
output = Path(args.output)
if not os.path.isdir(output.parent):
	try:
		Path.mkdir(output.parent, parents=True)
	except OSError:
		print("Failed to create the directory for output mezzanine stream.")

# Check that output exists if only (re)generating metadata
if metadata_gen_only and not os.path.isfile(output):
	sys.exit("Mezzanine file \""+str(output)+"\" does not exist. \n"
			"Cannot generate metadata without the corresponding mezzanine file. \n"
			"Set --metadata-only to 'disabled' to generate mezzanine and metadata.")

# Set width and height based on resolution
width = resolution.split('x')[0]
height = resolution.split('x')[1]


# Configure metadata output paths
avsync_metadata_filepath = Path(str(output.parent)+'\\'+str(output.stem)+'_avsync.json')
mezz_metadata_filepath = Path(str(output.parent)+'\\'+str(output.stem)+'.json')

# Initialise mezzanine properties metadata
mezz_properties = MezzanineProperties(int(width), int(height), round(eval(framerate), 3))
mezz_properties.qr_positions = qr_positions
mezz_properties.label = label

# Set mezzanine source metadata
mezz_source_license = ""
try:
	mezz_source_license_file = open(str(Path(str(input.parent)+'\\'+input.stem+'_LICENSE.txt')), encoding="utf-8")
	mezz_source_license = mezz_source_license_file.read()
except OSError:
	print("Failed to load source LICENSE file. "
		  "Ensure the file is located in the same folder as the source with the name <source_file_name>_LICENSE.txt.")
mezz_source = MezzanineSource(input.name, mezz_source_cdn_path+input.name, mezz_source_license)


# Set output video encoding parameters based on the following properties of the original source video:
# color range, color space, pixel format, primaries and transfer function
source_videoproperties = subprocess.check_output(
	['ffprobe', '-i', str(input), '-show_streams', '-select_streams', 'v', '-loglevel', '0', '-print_format', 'json'])
source_videoproperties_json = json.loads(source_videoproperties)
if 'streams' in source_videoproperties_json:
	if 'color_space' in source_videoproperties_json['streams'][0] and tonemap == 'disabled':
		output_video_encoding_cl = \
			output_video_encoding_selection.get(source_videoproperties_json['streams'][0]['color_space'], H265)
		mezz_properties.codec = output_video_codec_name.get(output_video_encoding_cl[0], "other")
		if 'color_space' in source_videoproperties_json['streams'][0] == ('bt470bg' or 'smpte170m'):
			tonemap = 'enabled'
			tonemap_cl = tonemap_cl_non709
			output_video_encoding_cl.append('-colorspace')
			output_video_encoding_cl.append('bt709')
			output_video_encoding_cl.append('-pix_fmt')
			output_video_encoding_cl.append('yuv420p')
			output_video_encoding_cl.append('-color_primaries')
			output_video_encoding_cl.append('bt709')
			output_video_encoding_cl.append('-color_trc')
			output_video_encoding_cl.append('bt709')
		else:
			output_video_encoding_cl.append('-colorspace')
			output_video_encoding_cl.append(source_videoproperties_json['streams'][0]['color_space'])
		mezz_properties.matrix_coefficients = output_video_encoding_cl[output_video_encoding_cl.index('-colorspace')+1]

	else:
		# Either source is assumed to be BT.709 SDR in the absence of signalling or tone-mapping to BT.709 SDR
		output_video_encoding_cl = H264
		mezz_properties.codec = output_video_codec_name.get(output_video_encoding_cl[0], "other")
		output_video_encoding_cl.append('-colorspace')
		output_video_encoding_cl.append('bt709')
		mezz_properties.matrix_coefficients = output_video_encoding_cl[output_video_encoding_cl.index('-colorspace')+1]
		if tonemap == 'enabled':
			tonemap_cl = tonemap_cl_hdr2sdr
			output_video_encoding_cl.append('-pix_fmt')
			output_video_encoding_cl.append('yuv420p')
			output_video_encoding_cl.append('-color_primaries')
			output_video_encoding_cl.append('bt709')
			output_video_encoding_cl.append('-color_trc')
			output_video_encoding_cl.append('bt709')
	
	if 'pix_fmt' in source_videoproperties_json['streams'][0] and tonemap == 'disabled':
		output_video_encoding_cl.append('-pix_fmt')
		output_video_encoding_cl.append(source_videoproperties_json['streams'][0]['pix_fmt'])
	elif tonemap == 'disabled':
		output_video_encoding_cl.append('-pix_fmt')
		output_video_encoding_cl.append('yuv420p')
	mezz_properties.pixel_format = output_video_encoding_cl[output_video_encoding_cl.index('-pix_fmt')+1]
	px_fmt_bit_depth = mezz_properties.pixel_format.split("p")[1][0:2]
	if px_fmt_bit_depth == '':
		mezz_properties.bit_depth = 8
	else:
		mezz_properties.bit_depth = int(px_fmt_bit_depth)
	
	if 'color_primaries' in source_videoproperties_json['streams'][0] and tonemap == 'disabled':
		output_video_encoding_cl.append('-color_primaries')
		output_video_encoding_cl.append(source_videoproperties_json['streams'][0]['color_primaries'])
	elif tonemap == 'disabled':
		output_video_encoding_cl.append('-color_primaries')
		output_video_encoding_cl.append('bt709')
	mezz_properties.color_primaries = output_video_encoding_cl[output_video_encoding_cl.index('-color_primaries')+1]
	
	if 'color_transfer' in source_videoproperties_json['streams'][0] and tonemap == 'disabled':
		output_video_encoding_cl.append('-color_trc')
		output_video_encoding_cl.append(source_videoproperties_json['streams'][0]['color_transfer'])
	elif tonemap == 'disabled':
		output_video_encoding_cl.append('-color_trc')
		output_video_encoding_cl.append('bt709')
	mezz_properties.transfer_characteristics = output_video_encoding_cl[output_video_encoding_cl.index('-color_trc')+1]
	
	if 'color_range' in source_videoproperties_json['streams'][0]:
		output_video_encoding_cl.append('-color_range')
		output_video_encoding_cl.append(source_videoproperties_json['streams'][0]['color_range'])
	else:
		output_video_encoding_cl.append('-color_range')
		output_video_encoding_cl.append('tv')
	mezz_properties.range = metadata_properties_range.get(
		output_video_encoding_cl[output_video_encoding_cl.index('-color_range')+1], 'unknown')
	
	if 'r_frame_rate' in source_videoproperties_json['streams'][0] \
			and 'avg_frame_rate' in source_videoproperties_json['streams'][0]:
		if round(eval(source_videoproperties_json['streams'][0]['r_frame_rate']), 3) \
				== round(eval(source_videoproperties_json['streams'][0]['avg_frame_rate']), 3):
			mezz_properties.scan = 'progressive'
		elif round(eval(source_videoproperties_json['streams'][0]['r_frame_rate']), 2) \
				== 2*round(eval(source_videoproperties_json['streams'][0]['avg_frame_rate']), 2):
			mezz_properties.scan = 'interlaced'

# Display output video encoding parameters
output_video_encoding = ' '.join(output_video_encoding_cl)
print("Output video encoding parameters: "+output_video_encoding)
print()

# Align A/V sync beep audio sample rate with the sample rate of the source file audio
if audio_samplerate != 0:
	beep_audio_samplerate = str(audio_samplerate)
else:
	source_audioproperties = subprocess.check_output(
		['ffprobe', '-i', str(input), '-show_streams', '-select_streams', 'a', '-loglevel', '0', '-print_format', 'json'])
	source_audioproperties_json = json.loads(source_audioproperties)
	if 'streams' in source_audioproperties_json:
		if 'sample_rate' in source_audioproperties_json['streams'][0]:
			beep_audio_samplerate = source_audioproperties_json['streams'][0]['sample_rate']


# Set default content duration = total duration 
# If start/end indicator frames are added then 
# content duration < total duration = content duration + start/end indicator frames
content_duration = duration

# Set start/end indicator frame FFMPEG parameters 
# and associated filter parameters to concatenate with source test sequence before output
if start_end_indicators == 'enabled':
	content_duration = Decimal(content_duration-(2*start_end_indicator_nb_frames/eval(framerate))).quantize(Decimal('.001'), rounding=ROUND_UP)
	start_indicator_offset = start_end_indicator_nb_frames/eval(framerate)
	start_indicator_nb_frames = start_end_indicator_nb_frames
	end_indicator_nb_frames = start_end_indicator_nb_frames
	indicator_duration = str(Decimal(start_end_indicator_nb_frames/eval(framerate)).quantize(Decimal('.001'), rounding=ROUND_DOWN))
	start_end_indicators_cl = ['-t', indicator_duration, '-f', 'lavfi', 
							   '-i', 'color='+start_indicator_color+':size='+width+'x'+height+':rate='+framerate,
							   '-t', indicator_duration, '-f', 'lavfi', 
							   '-i', 'sine=frequency=1000:beep_factor=1:sample_rate='+beep_audio_samplerate,
							   '-t', indicator_duration, '-f', 'lavfi', 
							   '-i', 'color='+end_indicator_color+':size='+width+'x'+height+':rate='+framerate,
							   '-t', indicator_duration, '-f', 'lavfi', 
							   '-i', 'sine=frequency=1000:beep_factor=1:sample_rate='+beep_audio_samplerate]
	start_end_indicators_vmix_cl = '[7][content_video][9]\
										concat=\
										n=3:v=1:a=0\
									[video_with_start_end_indicators];\
									[bg_video][video_with_start_end_indicators]\
										overlay=\
									[main_video];'
	start_end_indicators_amix_cl = '[8][audio_with_avsync][10]\
										concat=\
											n=3:v=0:a=1\
									[aout]'
	mezz_properties.start_indicator = True
	mezz_properties.end_indicator = True
	
elif start_end_indicators == 'start':
	content_duration = Decimal(content_duration-(start_end_indicator_nb_frames/eval(framerate))).quantize(Decimal('.001'), rounding=ROUND_UP)
	start_indicator_offset = start_end_indicator_nb_frames/eval(framerate)
	start_indicator_nb_frames = start_end_indicator_nb_frames
	indicator_duration = str(Decimal(start_end_indicator_nb_frames/eval(framerate)).quantize(Decimal('.001'), rounding=ROUND_DOWN))
	start_end_indicators_cl = ['-t', indicator_duration, '-f', 'lavfi', 
							   '-i', 'color='+start_indicator_color+':size='+width+'x'+height+':rate='+framerate, 
							   '-t', indicator_duration, '-f', 'lavfi', 
							   '-i', 'sine=frequency=1000:beep_factor=1:sample_rate='+beep_audio_samplerate]
	start_end_indicators_vmix_cl = '[7][content_video]\
										concat=\
										n=2:v=1:a=0\
									[video_with_start_indicator];\
									[bg_video][video_with_start_indicator]\
										overlay=\
									[main_video];'
	start_end_indicators_amix_cl = '[8][audio_with_avsync]\
										concat=\
											n=2:v=0:a=1\
									[aout]'
	mezz_properties.start_indicator = True
	
elif start_end_indicators == 'end':
	content_duration = Decimal(content_duration-(start_end_indicator_nb_frames/eval(framerate))).quantize(Decimal('.001'), rounding=ROUND_UP)
	end_indicator_nb_frames = start_end_indicator_nb_frames
	indicator_duration = str(Decimal(start_end_indicator_nb_frames/eval(framerate)).quantize(Decimal('.001'), rounding=ROUND_DOWN))
	start_end_indicators_cl = ['-t', indicator_duration, '-f', 'lavfi', 
							   '-i', 'color='+end_indicator_color+':size='+width+'x'+height+':rate='+framerate,
							   '-t', indicator_duration, '-f', 'lavfi', 
							   '-i', 'sine=frequency=1000:beep_factor=1:sample_rate='+beep_audio_samplerate]
	start_end_indicators_vmix_cl = '[content_video][7]\
										concat=\
										n=2:v=1:a=0\
									[video_with_end_indicator];\
									[bg_video][video_with_end_indicator]\
										overlay=\
									[main_video];'
	start_end_indicators_amix_cl = '[audio_with_avsync][8]\
										concat=\
											n=2:v=0:a=1\
									[aout]'
	mezz_properties.end_indicator = True


# Compute the size of various overlay blocks, so they are consistently placed
qr_size = int(round(int(height)*0.25, 0))
flash_block_size = int(round(int(height)*0.125, 0))

# Generates a series of timestamped QR codes at the frame rate of the target output
# Each QR code is saved to a PNG file in the qr directory.
frame_duration = round(1/eval(framerate), 10)
frame_count = int(eval(framerate)*duration)
frame_pts = start_frame*round(frame_duration, 10)
frame_rate = round(eval(framerate), 3)

mezz_properties.duration = round(frame_count/eval(framerate), 3)
mezz_properties.frame_count = frame_count
mezz_properties.start_frame = start_frame

if not metadata_gen_only:
	print("Generating QR codes...")

	if not os.path.isdir(qr_file_dir):
		try:
			os.mkdir(qr_file_dir)
		except OSError:
			print("Failed to create the directory for the QR code image files.")

	for i in range(0, frame_count):
		frame_pts_rounded = round(frame_pts, 3)
		timecode = '{:02d}:{:02d}:{:06.3f}'.format(int(frame_pts_rounded/3600), int(frame_pts_rounded/60) % 60, frame_pts_rounded % 60)
		padded_frame = str(i+start_frame).zfill(frame_number_padding)
		
		qr_filename = Path(str(qr_file_dir)+'\\'+(str(i).zfill(5)+'.png'))
		qr = qrcode.QRCode(
			version=None,
			error_correction=qrcode.constants.ERROR_CORRECT_H,
			box_size=6,
			border=4,
			)
		qr.add_data(label+';'+timecode+';'+padded_frame+';'+str(frame_rate))
		qr.make(fit=True)
		
		qr_img = qr.make_image(fill_color='white', back_color='black')
		qr_img.save(str(qr_filename))
		
		frame_pts = round(frame_pts+frame_duration, 10)

	print("Done")
	print()

# Generate the bit patterns containing:
#   current frame (24 bit), total frames (24 bit), frame rate (17 bit),
#   horizontal (13 bit) and vertical (13 bit) resolution
# These bit patterns enable easier extraction of this metadata from each frame by automation tools
# (e.g. for white-box device testing)
if not metadata_gen_only:
	print("Generating bitpatterns...")

	if not os.path.isdir(bitpat_file_dir):
		try:
			os.mkdir(bitpat_file_dir)
		except OSError:
			print("Failed to create the directory for the bitpattern image files.")

	for i in range(0, frame_count):
		bp_create(bitpat_file_dir, i+start_frame, frame_count, frame_rate, int(width), int(height))
		
	print("Done")
	print()

# Generate the irregular A/V sync pattern consisting of a still image sequence and
# corresponding WAV file that contain aligned "beeps" and "flashes"
if not metadata_gen_only:
	print("Generating A/V sync pattern...", end='', flush=True)

	if not os.path.isdir(flash_file_dir):
		try:
			os.mkdir(flash_file_dir)
		except OSError:
			print("Failed to create the directory for the A/V sync pattern image files.")

	subprocess.run(['python', test_sequence_gen_script, 
		'--duration', str(math.ceil(duration)), 		# int duration in seconds needed
		'--fps', str(math.ceil(eval(framerate)*2)/2), 	# float needed (used for 12.5fps support)
		'--frame-filename', str(Path(str(flash_file_dir)+'\\%05d.png')),
		'--sampleRate', beep_audio_samplerate,
		'--size', '1x1', 
		'--wav-filename', beep_file,
		'--window-len', avsync_pattern_window_len,
		'--metadata-filename', str(avsync_metadata_filepath)])


# This large command accomplishes the Mezzanine transform :
# - Starts FFMPEG with 5 input sources:
#   [0] A virtual audio source that contains an irregular pattern of beeps for AV-sync
#   [1] The original video source seek-ed to the desired point
#   [2] An image file of frame boundary markers
#   [3] A series of QR code images generated in a previous step
#   [4] A series of images generated in a previous step depicting an irregular pattern of flashes
#       matching the beeps of [0]
#   [5] A series of bit pattern images generated in a previous step
#   [6] Black background used as the background video.
#       Ensures the PTS and frame counter correctly start from the first frame.
#   [7],[8],[9],[10] Are single colored frames with silent audio, used to signal the start and end of the stream,
#                    see above for the command line definitions
# - Applies the following complex filter to the demuxed inputs:
#     - Takes the black background video stream and sets the start PTS, start time and frame rate
#     - Takes the video stream from the original source and:
#       - Applies rudimentary tone mapping from HDR to SDR when --tonemap enabled
#       - Scales it to the desired output size while preserving original ratio
#       - Adds top/bottom black bars to enforce a 16:9 frame
#       - Fixes the output format based on the desired output (SDR/BT.709 or HDR/BT.2020)
#       - Forces the frame rate to the desired frame rate
#     - Takes the QR code stream and:
#       - Scales them relative to their final positioning in the composition
#     - Frames signalling the start/end of the content are overlayed on the first/last frames
#       of the video from the original source
#     - Draws the video frame rate, frame number and timecode of the current frame onto it
#     - Takes the stream of images depicting the pattern of AV-sync flashes and:
#       - Scales them relative to their final positioning in the composition
#       - Overlays the scaled pattern of flashes indicating a beep
#     - Draws 2px wide border around the video edge:
#       - Outer 1px black border
#       - Inner 1px white border
#     - Takes the boundary marker and:
#       - Scales it to the desired output size
#       - Full screen overlays the scaled boundary marker
#     - Takes the scaled QR code stream and:
#       - Places the QR codes in a pattern based on frame number
#     - Takes the bitpattern stream and:
#       - Places the bitpatterns in a fixed position relative to the resolution at the top left of the video 
#     - Takes the audio stream from the original source and:
#       - Resamples it to the chosen sample rate
#       - Mixes it with the audio stream containing the AV-sync beeps
#       - Mixes it with the audio streams containing the start/end indicator beeps
# - Post filter the output is mapped as follows:
#     - Video is the output of the last overlay composition
#     - Audio is the output of the audio mix filter
# - The mapped outputs are then:
#     - Encoded in h264 or h265 for video depending on the source content, and aac for audio
#     - Fixed to the desired output frame rate
#     - Fixed to the desired duration
#     - Written to the supplied output location (overwriting is enabled)
ffmpeg_cl = ['ffmpeg', 
	'-t', str(content_duration), '-i', beep_file,
	'-ss', seek, '-t', str(content_duration), '-stream_loop', '-1', '-i', str(input),
	'-framerate', framerate, '-i', str(boundaries),
	'-framerate', framerate, '-thread_queue_size', '1024', '-start_number', '0',
			 '-i', str(Path(str(qr_file_dir)+'\\'+'%05d.png')),
	'-framerate', framerate, '-thread_queue_size', '1024', '-start_number', '0',
			 '-i', str(Path(str(flash_file_dir)+'\\'+'%05d.png')),
	'-framerate', framerate, '-thread_queue_size', '1024', '-start_number', '0',
			 '-i', str(Path(str(bitpat_file_dir)+'\\'+'%05d.png'))] \
	+ ['-f', 'lavfi', '-i', 'color=black:d='+str(duration)+':s='+width+'x'+height] \
	+ start_end_indicators_cl \
	+ ['-filter_complex',
		'[6]\
			setpts=PTS-STARTPTS,\
			fps=\
				fps='+framerate+':\
				start_time=0\
		[bg_video];\
		[1:v]\
			'+tonemap_cl+'\
			scale=\
				size='+width+'x'+height+':\
				force_original_aspect_ratio=decrease,\
			setsar=1,\
			pad=\
				w='+width+':\
				h='+height+':\
				x=(ow-iw)/2:\
				y=(oh-ih)/2,\
			format='+output_video_encoding_cl[output_video_encoding_cl.index('-pix_fmt')+1]+',\
			fps=\
				fps='+framerate+':\
				start_time='+str(round(start_indicator_offset, 3))+'\
		[content_video];\
		[3]\
			scale=\
				w='+str(qr_size)+':\
				h=-1\
		[qrs];\
		'+start_end_indicators_vmix_cl+'\
		[main_video]\
			drawtext=\
				fontfile=\''+font+'\':\
				text=\''+label+'\':\
				x=(w-tw)/10:\
				y=(3*lh):\
				fontcolor=white:\
				fontsize=h*0.06:\
				box=1:\
				boxborderw=10:\
				boxcolor=black,\
			drawbox=\
				x=\'('+width+'*0.1)-4\':\
				y=\'('+height+'/2)-'+str(qr_size)+'-4\':\
				w='+str(2*qr_size)+'+4:\
				h='+str(2*qr_size)+'+4:\
				t=fill:\
				color=black,\
			drawtext=\
				fontfile=\''+font+'\':\
				text=\'%{pts\:hms\:'
					+str((lambda x: x/eval(framerate) if x > 0 else 0)(start_frame))
					+'};%{eif\:n+'+str(start_frame)+'\:d\:'+str(frame_number_padding)
					+'};'+str(frame_rate)+'\':\
				x=(w-tw)/2:\
				y=h-(4*lh):\
				fontcolor=white:\
				fontsize=h*0.06:\
				box=1:\
				boxborderw=10:\
				boxcolor=black\
		[annotated_main_video];\
		[4]\
			scale=\
				size='+str(flash_block_size)+'x'+str(flash_block_size)+'\
		[avsync_flash];\
		[annotated_main_video][avsync_flash]\
			overlay=\
				x=\'main_w*0.925-overlay_w\':\
				y=\'main_h*0.1\':\
				shortest=1:\
				repeatlast=0\
		[video_with_avsync_flash];\
		[video_with_avsync_flash]\
			drawbox=\
				x=1:\
				y=1:\
				w='+str(eval(width)-2)+':\
				h='+str(eval(height)-2)+':\
				c=black:\
				t=1\
		[video_with_inner_border];\
		[video_with_inner_border]\
			drawbox=\
				x=0:\
				y=0:\
				w='+str(eval(width))+':\
				h='+str(eval(height))+':\
				c=white:\
				t=1\
		[video_with_borders];\
		[2]\
			scale=\
				size='+width+'x'+height+'\
		[boundary_arrows];\
		[video_with_borders][boundary_arrows]\
			overlay=\
				repeatlast=1\
		[bounded_video];\
		[bounded_video][qrs]\
			overlay=\
				x=\'(main_w*0.1)+if(between(mod(n,'+str(qr_positions)+'),2,3),overlay_w)\':\
				y=\'(main_h/2)-ifnot(between(mod(n,'+str(qr_positions)+'),1,2),overlay_h)\':\
				shortest=1:\
				repeatlast=0\
		[bounded_video_with_qrs];\
		[bounded_video_with_qrs][5]\
			overlay=\
				x=4/480*'+width+':\
				y=4/270*'+height+'\
		[vout];\
		[1:a]\
			aresample='+str(audio_samplerate)+'\
		[resampled_main_audio];\
		[0][resampled_main_audio]\
			amix=\
				inputs=2:\
				duration=shortest:\
		[audio_with_avsync];'+start_end_indicators_amix_cl,
	'-map', '[vout]',
	'-map', '[aout]',
	'-c:v'] + output_video_encoding_cl \
	+ ['-c:a', 'aac', '-b:a', '320k', '-ac', '2',
	'-y',
	'-t', str(duration),
	str(output)]

if not metadata_gen_only:
	proc = subprocess.run(ffmpeg_cl)


# Output metadata
# Import CTA mezzanine license if available
mezz_license = ""
try:
	mezz_license_file = open(str(Path(str(input.parent)+'\\'+input.stem+'_CTA_LICENSE.txt')), encoding="utf-8")
	mezz_license = mezz_license_file.read()
except OSError:
	print("Failed to load mezzanine CTA LICENSE file. Ensure the file is located in the same folder as the source "
		  "with the name <source_file_name>_CTA_LICENSE.txt.")

# Calculate MD5 hash
BLOCK_SIZE = 65536
mezz_file_hash = hashlib.md5()
with open(output, 'rb') as mezz_file:
	mezz_file_block = mezz_file.read(BLOCK_SIZE)
	while len(mezz_file_block) > 0: 					# Until all data has been read from mezzanine file
		mezz_file_hash.update(mezz_file_block) 			# Update hash
		mezz_file_block = mezz_file.read(BLOCK_SIZE) 	# Read the next block from mezzanine file

mezz_metadata = Mezzanine(output.stem, mezz_version, mezz_specification_version, date.today().isoformat(), mezz_license,
						  './'+output.name, str(Path(__file__).resolve().name)+' '+' '.join(sys.argv[1:]),
						  ' '.join(ffmpeg_cl).replace('\t', ''), mezz_file_hash.hexdigest(), mezz_properties, mezz_source)

print()
print()
print("Name: "+mezz_metadata.name)
print("URI: "+mezz_metadata.URI)
print("Version: "+str(mezz_metadata.version))
print("Spec version: "+str(mezz_metadata.specification_version))
print("Creation date: "+mezz_metadata.creation_date)
print("License: "+mezz_metadata.license)
print("CL used: "+mezz_metadata.command_line)
print("FFMPEG CL used: "+mezz_metadata.ffmpeg_command_line)
print("MD5: "+mezz_metadata.md5)
print()
print("Width: "+str(mezz_metadata.properties.width))
print("Height: "+str(mezz_metadata.properties.height))
print("Frame rate: "+str(mezz_metadata.properties.frame_rate))
print("Scan: "+mezz_metadata.properties.scan)
print("Px Format: "+mezz_metadata.properties.pixel_format)
print("Bit depth: "+str(mezz_metadata.properties.bit_depth))
print("Color primaries: "+mezz_metadata.properties.color_primaries)
print("Matrix coefficients: "+mezz_metadata.properties.matrix_coefficients)
print("Transfer characteristics: "+mezz_metadata.properties.transfer_characteristics)
print("Range: "+mezz_metadata.properties.range)
print("Duration: "+str(mezz_metadata.properties.duration))
print("Frame count: "+str(mezz_metadata.properties.frame_count))
print("Start frame: "+str(mezz_metadata.properties.start_frame))
print("Start indicator: "+str(mezz_metadata.properties.start_indicator))
print("End indicator: "+str(mezz_metadata.properties.end_indicator))
print("QR positions: "+str(mezz_metadata.properties.qr_positions))
print("Label: "+mezz_metadata.properties.label)
print("Codec: "+mezz_metadata.properties.codec)
print()
print("Source name: "+mezz_metadata.source.name)
print("Source URI: "+mezz_metadata.source.URI)
print("Source license: "+mezz_metadata.source.license)
print()

# Save metadata to JSON file
mezz_metadata_file = open(str(mezz_metadata_filepath), "w")
json.dump(mezz_metadata, mezz_metadata_file, indent=4, cls=MezzanineEncoder)
mezz_metadata_file.write('\n')
mezz_metadata_file.close()

print("Mezzanine metadata stored in: "+str(mezz_metadata_filepath))
print()


# Remove the temporary files for the QR codes, flashes and beeps
if not metadata_gen_only:
	print("Removing temporary files...", end='', flush=True)

	os.remove(beep_file)
	frame_count = int(round(math.ceil(eval(framerate))*math.ceil(duration), 0))
	for i in range(0, frame_count):
		qr_filename = str(Path(str(qr_file_dir)+'\\'+(str(i).zfill(5)+'.png')))
		flash_filename = str(Path(str(flash_file_dir)+'\\'+(str(i).zfill(5)+'.png')))
		bitpattern_filename = str(Path(str(bitpat_file_dir)+'\\'+(str(i+start_frame).zfill(5)+'.png')))
		try:
			os.remove(qr_filename)
		except OSError as e:
			if e.errno != errno.ENOENT:		# No such file or directory
				raise
		try:
			os.remove(flash_filename)
		except OSError as e:
			if e.errno != errno.ENOENT:		# No such file or directory
				raise
		try:
			os.remove(bitpattern_filename)
		except OSError as e:
			if e.errno != errno.ENOENT:		# No such file or directory
				raise
	print("Done")
	
	print("Removing temporary folders...", end='', flush=True)
	if len(os.listdir(str(qr_file_dir))) == 0:
		os.rmdir(str(qr_file_dir))
	if len(os.listdir(str(flash_file_dir))) == 0:
		os.rmdir(str(flash_file_dir))
	if len(os.listdir(str(bitpat_file_dir))) == 0:
		os.rmdir(str(bitpat_file_dir))
		
	print("Done")
	print()
