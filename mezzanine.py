import argparse
import json
import os
import subprocess
import sys

import PIL
import qrcode

from pathlib import Path
from shutil import which


# Video output encoding presets
H264 = ['libx264', '-preset', 'slower', '-crf', '5']
H265 = ['libx265', '-preset', 'slower', '-crf', '5']


# Check FFMPEG and FFPROBE are installed
if which('ffmpeg') is None:
	sys.exit("FFMPEG was not found, ensure FFMPEG is added to the system PATH or is in the same folder as this script.")
if which('ffprobe') is None:
	sys.exit("FFMPEG was not found, ensure FFPROBE is added to the system PATH or is in the same folder as this script.")


# Default parameters
avsync_pattern_window_len = '5'
beep_file = 'beeps.wav' 			# Not configurable via argument
beep_audio_samplerate = '48000'
boundaries = 'boundaries.png'
duration = 30
flash_file_dir = Path('flash/') 	# Not configurable via argument
font = 'monospace'
frame_number_padding = 7
framerate = '30'
label = 'mezz'
output_video_encoding_cl = H265		# Defined based on original source content colorspace, default H.265/HEVC
output_video_encoding_selection = {'bt2020nc':H265,'bt709':H264} # Mapping between source content colorspace and output video codec
qr_file_dir = Path('qr/')			# Not configurable via argument
qr_positions = 2
resolution= '1920x1080'
seek = '00:00:00.000'
start_end_indicators = 'disabled'
start_end_indicator_nb_frames = 1	# Not configurable via argument, number of indicator frames to insert at the start and/or end
start_end_indicators_cl =[]			# Defined based on start_end_indicators, see below
start_end_indicators_mix_cl = '[vfinal][afinal] concat=n=1:v=1:a=1 [vout][aout]' # Defined based on start_end_indicators, see below
start_indicator_frame_offset = 0	# Defined based on start_end_indicators, see below
start_indicator_color = '0x006400'	# Not configurable via argument, color in hexadecimal 0xRRGGBB sequence
end_indicator_color = '0x8B0000'	# Not configurable via argument, color in hexadecimal 0xRRGGBB sequence
test_sequence_gen_script = Path('test_sequence_gen/src/generate.py') # Not configurable via argument
width=''  # Pulled from resolution string, see below
height='' # Pulled from resolution string, see below


# Basic argument handling
parser = argparse.ArgumentParser(description="WAVE Mezzanine Content Creator.")

parser.add_argument(
	'-b', '--boundaries', 
	required=False, 
	help="Specifies a file that contains boundary markers. Default: "+boundaries)
	
parser.add_argument(
	'-d', '--duration', 
	required=False, 
	type=int, 
	help="The duration, in seconds, of the source file to process from the seek position in. Default: "+str(duration))
	
parser.add_argument(
	'-f', '--framerate', 
	required=False, 
	help="The target framerate of the output file. Fractional rates must be specified as division operations \"30000/1001\". Default: "+framerate)
	
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
	'-q', '--qr-positions', 
	required=False, 
	type=int, choices=[2,4], 
	help="The number of on-screen QR code positions to use, may be 2 or 4. Default: "+str(qr_positions))
	
parser.add_argument(
	'-r', '--resolution', 
	required=False, 
	help="The target resolution of the output, video will be scaled and padded to fit resolution. Should be specified as \"<width>x<height>\". Default: "+resolution)

parser.add_argument(
	'-s', '--seek', 
	required=False, 
	help="Seeks the source file to a starting position. Format must follow ffmpeg -ss parameter. Default: "+seek)

parser.add_argument(
	'--start-end-indicators', 
	required=False, 
	choices=['enabled','disabled','start','end'], 
	help="Append a single frame before and after the source content, to signal the start and end of the test sequence. May be \"enabled\", \"disabled\", \"start\" (only) or \"end\" (only). Default: disabled")
	
parser.add_argument(
	'-t', '--font', 
	required=False, 
	help="The font to utilize for drawing timecodes on frames, must be full path to file. Default: "+font)

parser.add_argument(
	'-w', '--window-len', 
	required=False, 
	help="Unique pattern window length (in seconds). Beep/flash sequence will repeat after 2^n -1 seconds. Default is "+avsync_pattern_window_len+", meaning the sequence repeats after "+str(2**int(avsync_pattern_window_len)-1)+" seconds.")

parser.add_argument('input', help="Source file.")
parser.add_argument('output', help="Output file.")

args = parser.parse_args()


# Set parameters to values provided in arguments
if args.window_len is not None:
	avsync_pattern_window_len = args.window_len

if args.boundaries is not None:
	boundaries = args.boundaries
	
if args.duration is not None:
	duration = args.duration

if args.font is not None:
	font = args.font

if args.frame_number_padding is not None:
	frame_number_padding = args.frame_number_padding

if args.framerate is not None:
	framerate = args.framerate

if args.label is not None:
	label = args.label

if args.qr_positions is not None:
	qr_positions = args.qr_positions

if args.resolution is not None:
	resolution= args.resolution

if args.seek is not None:
	seek = args.seek
	
if args.start_end_indicators is not None:
	start_end_indicators = args.start_end_indicators


# Check that source and boundaries files are present
if not os.path.isfile(args.input):
	sys.exit("Source file \""+args.input+"\" does not exist.")
	
if not os.path.isfile(boundaries):
	sys.exit("Boundaries image file \""+boundaries+"\" does not exist.")

	
# Set output video encoding parameters based on the following properties of the original source video:
# color range, color space, pixel format, primaries and transfer function
source_videoproperties = subprocess.check_output(['ffprobe', '-i', args.input, '-show_streams', '-select_streams', 'v', '-loglevel', '0', '-print_format', 'json'])
source_videoproperties_json = json.loads(source_videoproperties)
if 'streams'in source_videoproperties_json:
	if 'color_space' in source_videoproperties_json['streams'][0]:
		output_video_encoding_cl = output_video_encoding_selection.get(source_videoproperties_json['streams'][0]['color_space'],H265)
		output_video_encoding_cl.append('-colorspace')
		output_video_encoding_cl.append(source_videoproperties_json['streams'][0]['color_space'])
	else:
		output_video_encoding_cl = H264
	if 'pix_fmt' in source_videoproperties_json['streams'][0]:
		output_video_encoding_cl.append('-pix_fmt')
		output_video_encoding_cl.append(source_videoproperties_json['streams'][0]['pix_fmt'])
	if 'color_primaries' in source_videoproperties_json['streams'][0]:
		output_video_encoding_cl.append('-color_primaries')
		output_video_encoding_cl.append(source_videoproperties_json['streams'][0]['color_primaries'])
	if 'color_range' in source_videoproperties_json['streams'][0]:
		output_video_encoding_cl.append('-color_range')
		output_video_encoding_cl.append(source_videoproperties_json['streams'][0]['color_range'])
	if 'color_transfer' in source_videoproperties_json['streams'][0]:
		output_video_encoding_cl.append('-color_trc')
		output_video_encoding_cl.append(source_videoproperties_json['streams'][0]['color_transfer'])
output_video_encoding = ' '.join(output_video_encoding_cl)
print("Output video encoding parameters: "+output_video_encoding)


# Align A/V sync beep audio sameple rate with the samplerate of the source file audio
source_audioproperties = subprocess.check_output(['ffprobe', '-i', args.input, '-show_streams', '-select_streams', 'a', '-loglevel', '0', '-print_format', 'json'])
source_audioproperties_json = json.loads(source_audioproperties)
if 'streams'in source_audioproperties_json:
	if 'sample_rate' in source_audioproperties_json['streams'][0]:
		beep_audio_samplerate = source_audioproperties_json['streams'][0]['sample_rate']


# Set width and height based on resolution
width = resolution.split('x')[0]
height = resolution.split('x')[1]


# Set start/end indicator frame FFMPEG parameters and associated filter parameters to concatenate with source test sequence before output
if start_end_indicators == 'enabled':
	start_end_indicators_cl = ['-t', str(start_end_indicator_nb_frames/eval(framerate)), '-f', 'lavfi', '-i', 'color='+start_indicator_color+':size='+width+'x'+height+':rate='+framerate,
								'-t', str(start_end_indicator_nb_frames/eval(framerate)), '-f', 'lavfi', '-i', 'sine=frequency=1000:beep_factor=1:sample_rate='+beep_audio_samplerate,
								'-t', str(start_end_indicator_nb_frames/eval(framerate)), '-f', 'lavfi', '-i', 'color='+end_indicator_color+':size='+width+'x'+height+':rate='+framerate,
								'-t', str(start_end_indicator_nb_frames/eval(framerate)), '-f', 'lavfi', '-i', 'sine=frequency=1000:beep_factor=1:sample_rate='+beep_audio_samplerate]
	start_end_indicators_mix_cl = '[5][6][vfinal][afinal][7][8]\
										concat=\
											n=3:v=1:a=1\
									[vout][aout]'
	start_indicator_frame_offset = start_end_indicator_nb_frames	
	
elif start_end_indicators == 'start':
	start_end_indicators_cl = ['-t', str(start_end_indicator_nb_frames/eval(framerate)), '-f', 'lavfi', '-i', 'color='+start_indicator_color+':size='+width+'x'+height+':rate='+framerate,
								'-t', str(start_end_indicator_nb_frames/eval(framerate)), '-f', 'lavfi', '-i', 'sine=frequency=1000:beep_factor=1:sample_rate='+beep_audio_samplerate]
	start_end_indicators_mix_cl = '[5][6][vfinal][afinal]\
										concat=\
											n=2:v=1:a=1\
									[vout][aout]'
	start_indicator_frame_offset = start_end_indicator_nb_frames
	
elif start_end_indicators == 'end':
	start_end_indicators_cl = ['-t', str(start_end_indicator_nb_frames/eval(framerate)), '-f', 'lavfi', '-i', 'color='+end_indicator_color+':size='+width+'x'+height+':rate='+framerate,
								'-t', str(start_end_indicator_nb_frames/eval(framerate)), '-f', 'lavfi', '-i', 'sine=frequency=1000:beep_factor=1:sample_rate='+beep_audio_samplerate]
	start_end_indicators_mix_cl = '[vfinal][afinal][5][6]\
										concat=\
											n=2:v=1:a=1\
									[vout][aout]'

	
# Compute the size of various overlay blocks so they are consistently placed
qr_size = int(round(int(height)*0.25,0))
flash_block_size = int(round(int(height)*0.125,0))


# Generates a series of timestamped QR codes at the framerate of the target output
# Each QR code is saved to a PNG file in the qr directory.
frame_duration = round(1/eval(framerate),10)
frame_count = int(round(eval(framerate)*duration,0))
frame_pts = float(round(start_indicator_frame_offset*frame_duration,7))

print("Generating QR codes...", end='', flush=True)

if not os.path.isdir(qr_file_dir):
	try:
		os.mkdir(qr_file_dir)
	except OSError:
		print ("Failed to create the directory for the QR code image files.")

for i in range(0,frame_count):
	timecode = '{:02d}:{:02d}:{:06.3f}'.format(int(frame_pts/3600), int(frame_pts/60), frame_pts%60)
	padded_frame = str(i+start_indicator_frame_offset).zfill(frame_number_padding)
	
	
	qr_filename = qr_file_dir / (str(i).zfill(5)+'.png')
	qr = qrcode.QRCode(
		version=None,
		error_correction=qrcode.constants.ERROR_CORRECT_H,
		box_size=6,
		border=4,
		)
	qr.add_data(label+';'+timecode+';'+padded_frame)
	qr.make(fit=True)
	
	qr_img = qr.make_image(fill_color='white', back_color='black')
	qr_img.save(qr_filename)
	
	frame_pts = round(frame_pts+frame_duration,7)

print("Done")


# Generate the irregular A/V sync pattern consisting of a still image sequence and
# corresponding WAV file that contain aligned "beeps" and "flashes"
print("Generating A/V sync pattern...", end='', flush=True)

if not os.path.isdir(flash_file_dir):
	try:
		os.mkdir(flash_file_dir)
	except OSError:
		print ("Failed to create the directory for the A/V sync pattern image files.")

subprocess.run(['python', test_sequence_gen_script, 
	'--duration', str(duration),
	'--fps', framerate, 
	'--frame-filename', flash_file_dir / '%05d.png',
	'--sampleRate', beep_audio_samplerate,
	'--size', '1x1', 
	'--wav-filename', beep_file,
	'--window-len', avsync_pattern_window_len])


# This large command accomplishes the Mezzanine transform :
# - Starts FFMPEG with 5 input sources:
#   [0] A virtual audio source that contains an irregular pattern of beeps
#   [1] The original video source seeked to the desired point
#   [2] An image file of frame boundary markers
#   [3] A series of QR code images generated in a previous step
#   [4] A series of images generated in a previous step depicting an irregular pattern of flashes matching the beeps of [0]
#   [5],[6],[7],[8] Are single colored frames with silent audio, used to signal the start and end of the stream
# - Applies the following complex filter to the demuxed inputs:
#     - Takes the video stream from the original source and:
#       - Scales it to the desired output size while preserving original ratio
#       - Adds top/bottom black bars to enforce a 16:9 frame
#       - Fixes the output format to yuv420p
#       - Forces the framerate to the desired framerate
#       - Draws the timecode of the current frame onto it
#     - Takes the boundary marker and:
#       - Scales it to the desired output size
#     - Takes the QR code stream and:
#       - Scales them relative to their final positioning in the composition
#     - Takes the stream of images depicting the pattern of flashes and:
#       - Scales them relative to their final positioning in the composition
#     - Performs a series of overlay compositions:
#       - Uses the padded source as the base
#       - Full screen overlays the scaled boundary marker
#       - Places the QR codes in a pattern based on frame number
#       - Overlays the scaled pattern of flashes indicating a beep
#     - Takes the audio stream from the original source and:
#       - Mixes it with the audio stream containing the beeps
#     - Frames signalling the start/end of the content are concatenated to the start/end of the output of the last overlay composition
#     - Silent audio is concatenated to the start/end of the output of the audio mix filter
# - Post filter the output is mapped as follows:
#     - Video is either:
#       - the output of the concatenation of the last overlay composition and start/end frames when they are enabled
#       - else the output of the last overlay composition
#     - Audio is either:
#       - the output of the concatenation of the audio mix filter output with silence for the start/end frames when they are enabled
#       - else the output of the audio mix filter
# - The mapped outputs are then:
#     - Encoded in h264 or h265 for video depending on the source content, and aac for audio
#     - Fixed to the desired output framerate
#     - Fixed to the desired duration
#     - Written to the supplied output location (overwriting is enabled)
subprocess.call(['ffmpeg', 
	'-t', str(duration), '-i', beep_file,
	'-ss', seek, '-t', str(duration), '-i', args.input,
	'-i', boundaries,
	'-framerate', framerate, '-thread_queue_size', '1024', '-start_number', '0', '-i', qr_file_dir / '%05d.png',
	'-framerate', framerate, '-thread_queue_size', '1024', '-start_number', '0', '-i', flash_file_dir / '%05d.png']
	+ start_end_indicators_cl
	+['-filter_complex',	
		'[1:v]\
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
			fps=fps='+framerate+',\
			drawtext=\
				fontfile='+font+':\
				text=\''+label+'\':\
				x=(w-tw)/10:\
				y=(3*lh):\
				fontcolor=white:\
				fontsize=h*0.06:\
				box=1:\
				boxborderw=10:\
				boxcolor=black,\
			drawtext=\
				fontfile='+font+':\
				text=\'%{pts\:hms\:'
					+str((lambda x: x/eval(framerate) if x > 0 else 0)(start_indicator_frame_offset))
					+'};%{eif\:n+'+str(start_indicator_frame_offset)+'\:d\:'+str(frame_number_padding)+'}\':\
				x=(w-tw)/2:\
				y=h-(4*lh):\
				fontcolor=white:\
				fontsize=h*0.06:\
				box=1:\
				boxborderw=10:\
				boxcolor=black\
		[content];\
		[2]\
			scale=\
				size='+width+'x'+height+'\
		[boundaries];\
		[3]\
			scale=\
				w='+str(qr_size)+':\
				h=-1\
		[qrs];\
		[4]\
			scale=\
				size='+str(flash_block_size)+'x'+str(flash_block_size)+'\
		[beepindicator];\
		[content][boundaries]\
			overlay=\
				repeatlast=1\
		[bounded];\
		[bounded][qrs]\
			overlay=\
				x=\'(main_w*0.1)+if(between(mod(n,'+str(qr_positions)+'),2,3),overlay_w)\':\
				y=\'(main_h/2)-ifnot(between(mod(n,'+str(qr_positions)+'),1,2),overlay_h)\'\
		[qrplaced];\
		[qrplaced][beepindicator]\
			overlay=\
				x=\'main_w*0.925-overlay_w\':\
				y=\'main_h*0.1\'\
		[vfinal];\
		[0][1:a]\
			amix=\
				inputs=2:\
				duration=longest:\
		[afinal];'+start_end_indicators_mix_cl,
	'-map', '[vout]',
	'-map', '[aout]',
	'-c:v'] + output_video_encoding_cl
	+['-c:a', 'aac', '-b:a', '320k', '-ac', '2',
	'-r', framerate,
	'-y',
	args.output])


# Remove the temporaray files for the QR codes, flashes and beeps
print("Removing temporary files...", end='', flush=True)

os.remove(beep_file)
for i in range(0,frame_count):
	qr_filename = qr_file_dir / (str(i).zfill(5)+'.png')
	flash_filename = flash_file_dir / (str(i).zfill(5)+'.png')
	os.remove(qr_filename)
	os.remove(flash_filename)
	
print("Done")
