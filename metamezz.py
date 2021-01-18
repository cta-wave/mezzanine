import os
import subprocess


def generate_streams(input, source_duration, mezzanine_gen_script, font, label, qr_positions, resolutions, seek, start_end_indicators, window_len, output, second_audio_gen_script, test):
	"""\
	Calls the WAVE mezzanine generation script to create annotated versions of the input source content
	for each of the selected resolution-duration-variant combinations.
	Variants are streams that are identical except for their labels, which have a number appended.
	E.g. with label 'A' when generating 2 variants, output streams will have labels 'A1' and 'A2'.
	
	:param input: The path to the source content for which annotated mezzanine streams will be generated.
	:param source_duration: The source content duration (in seconds).
	:param mezzanine_gen_script: The path to the mezzanine generation Python script.
	:param font: The path to/name of the font file to use when generating the annotations.
	:param label: The initial label to use for the first resolution in the list. 
				A single character is expected (e.g. 'A'). Will be incremented in the ASCII value order. 
				Numbers will be appended to indicate the variant (e.g. 'A1').
	:param qr_positions: The number of annotation on-screen QR code positions to use, may be 2 or 4.
	:param resolutions: Dictionary containing the combinations of resolution, duration and label variant to generate using the source content. 
						Structure: {'WIDTHxHEIGHT':[[framerate (str), duration in seconds (int), number of variants (int), add second audio track (bool)], []]}
	:param seek: Seeks the source file to a starting position. Format must follow ffmpeg -ss parameter.
	:param start_end_indicators: Append a single frame before and after the source content, to signal the start and end of the test sequence. 
								 May be "enabled", "disabled", "start" (only) or "end" (only).
	:param window_len: Unique pattern window length (in seconds) for the annotated mezanine beep/flash sequence, which will repeat after 2^n -1 seconds. 
	:param output: The output annotated mezzanine file prefix. May include path.
	:param second_audio_gen_script: The path to the second audio track generation Python script.
	:param test: When this flag (bool) is set, stream creation is disabled. Used to create a list of the output streams without generating them.
	"""
	
	for res in resolutions.keys():
		for variant in resolutions.get(res):
			fps = variant[0]
			duration = variant[1]
			nb_variant_labels = variant[2]
			add_second_audio_track = variant[3]
			variant_label_range = range(nb_variant_labels)
			for variant_label in list(variant_label_range): 
				label_str = chr(label)+str(variant_label+1)
				if add_second_audio_track:
					print(output+'_'+label_str+'_'+res+'@'+str(round(eval(fps),2))+'_'+str(duration)+'_2ndAudio[English].mp4')
				else:
					print(output+'_'+label_str+'_'+res+'@'+str(round(eval(fps),2))+'_'+str(duration)+'.mp4')
				if not test:
					if not add_second_audio_track or (add_second_audio_track and not os.path.isfile(output+'_'+label_str+'_'+res+'@'+str(round(eval(fps),2))+'_'+str(duration)+'.mp4')):
						subprocess.run(['python', mezzanine_gen_script, 
									'--duration', str(duration),
									'--framerate', fps,
									'--label', label_str,
									'--qr-positions', str(qr_positions),
									'--resolution', res,
									'--seek', str((lambda x: seek if x > ((int(seek.split(':')[0])*60*60+int(seek.split(':')[1])*60+int(seek.split(':')[2]))+duration) else '00:00:00')(source_duration)),
									'--start-end-indicators', start_end_indicators,
									'--font', font,
									'--window-len', str(window_len),
									input,
									output+'_'+label_str+'_'+res+'@'+str(round(eval(fps),2))+'_'+str(duration)+'.mp4'
									])		
					if add_second_audio_track:
						subprocess.run(['python', second_audio_gen_script, 
								output+'_'+label_str+'_'+res+'@'+str(round(eval(fps),2))+'_'+str(duration)+'.mp4'
								])
		label += 1


if __name__ == "__main__":

	import argparse
	import json
	import sys

	from pathlib import Path

	# Default parameters
	
	# Dictionary of resolutions (keys) with values indicating:
	#		- the frame rate of the stream(s) to create, 
	#		- the length of the stream(s) to create in seconds, 
	#		- the number of variants of this length,
	#		- whether to add a second audio track to these variants (0 or 1)
	# Format: 
	#	'WIDTHxHEIGHT':[[framerate (str), duration in seconds (int), number of variants (int), add second audio track (bool)], []]
	# Notes: 
	#	Fractional rates must be specified as division operations e.g. '30000/1001'. 
	# 	Variants are streams that are identical except for their labels, which have a number appended.
	# 	E.g. with label 'A' when generating 2 variants, output streams will have labels 'A1' and 'A2'.
	resolutions = {
		'480x270':[['30',60,3,False]],
		'512x288':[['30',60,1,False]],
		'640x360':[['30',60,1,False]],
		'704x396':[['30',60,1,False]],
		'720x404':[['30',60,1,False]],
		'768x432':[['30',60,1,False]],
		'852x480':[['30',60,1,False]],
		'960x540':[['30',60,1,False]],
		'1024x576':[['30',60,3,False]],
		'1280x720':[['30',60,3,False]],
		'1600x900':[['30',60,1,False]],
		'1920x1080':[['30',60,3,False],['30',60,1,True]],
		'2560x1440':[['30',60,1,False]],
		'3200x1800':[['30',60,1,False]],
		'3840x2160':[['30',60,1,False]],
		'480x270':[['30000/1001',60,3,False]],
		'512x288':[['30000/1001',60,1,False]],
		'640x360':[['30000/1001',60,1,False]],
		'704x396':[['30000/1001',60,1,False]],
		'720x404':[['30000/1001',60,1,False]],
		'768x432':[['30000/1001',60,1,False]],
		'852x480':[['30000/1001',60,1,False]],
		'960x540':[['30000/1001',60,1,False]],
		'1024x576':[['30000/1001',60,3,False]],
		'1280x720':[['30000/1001',60,3,False]],
		'1600x900':[['30000/1001',60,1,False]],
		'1920x1080':[['30000/1001',60,3,False],['30000/1001',60,1,True]],
		'2560x1440':[['30000/1001',60,1,False]],
		'3200x1800':[['30000/1001',60,1,False]],
		'3840x2160':[['30000/1001',60,1,False]],
		'480x270':[['60',60,3,False]],
		'512x288':[['60',60,1,False]],
		'640x360':[['60',60,1,False]],
		'704x396':[['60',60,1,False]],
		'720x404':[['60',60,1,False]],
		'768x432':[['60',60,1,False]],
		'852x480':[['60',60,1,False]],
		'960x540':[['60',60,1,False]],
		'1024x576':[['60',60,3,False]],
		'1280x720':[['60',60,3,False]],
		'1600x900':[['60',60,1,False]],
		'1920x1080':[['60',60,3,False],['60',60,1,True]],
		'2560x1440':[['60',60,1,False]],
		'3200x1800':[['60',60,1,False]],
		'3840x2160':[['60',60,1,False]],
		'480x270':[['60000/1001',60,3,False]],
		'512x288':[['60000/1001',60,1,False]],
		'640x360':[['60000/1001',60,1,False]],
		'704x396':[['60000/1001',60,1,False]],
		'720x404':[['60000/1001',60,1,False]],
		'768x432':[['60000/1001',60,1,False]],
		'852x480':[['60000/1001',60,1,False]],
		'960x540':[['60000/1001',60,1,False]],
		'1024x576':[['60000/1001',60,3,False]],
		'1280x720':[['60000/1001',60,3,False]],
		'1600x900':[['60000/1001',60,1,False]],
		'1920x1080':[['60000/1001',60,3,False],['60000/1001',60,1,True]],
		'2560x1440':[['60000/1001',60,1,False]],
		'3200x1800':[['60000/1001',60,1,False]],
		'3840x2160':[['60000/1001',60,1,False]],
	}
	
	# Default first label
	first_label = ord('A')
	
	# Arrays of source files (inputs) and associated output file prefixes (outputs)
	inputs = []
	outputs = []

	# Parameters for mezzanine.py not configurable via argument
	mezzanine_gen_script = Path('mezzanine.py')
	font = 'Cousine-Regular.ttf'
	qr_positions = 4
	seek = '00:01:25'
	start_end_indicators = 'enabled'
	window_len = 6	#63 seconds
	
	# Paramaeters for add_second_audio_track.py not configurable via argumemt
	second_audio_gen_script = Path('add_second_audio_track.py')
	
	# Test run flag: used to parse inputs and print list of streams to generate without actually creating the output streams
	test = False
	
	# Basic argument handling
	parser = argparse.ArgumentParser(description="WAVE Mezzanine Batch Content Creator.")

	parser.add_argument(
		'-r', '--resolutions', dest='resolutions',  action='store', 
		required=False, 
		help="Specifies the resolutions, duration and number of label variants in which to generate the content. List resolutions from lowest to highest. JSON format: {\"WIDTHxHEIGHT\":[[framerate (str), duration in seconds (int), number of variants (int), add second audio track (bool)], []]}. Default:"+json.dumps(resolutions))

	parser.add_argument(
		'-rjf', '--resolutions-json-file', dest='resolutions_json',  action='store', 
		required=False, 
		help="Specifies the path to a JSON file containing resolutions, duration and number of label variants in which to generate the content. List resolutions from lowest to highest. JSON format: {\"WIDTHxHEIGHT\":[[framerate (str), duration in seconds (int), number of variants (int), add second audio track (bool)], []]}")
		
	parser.add_argument(
		'-fl', '--first-label', dest='first_label', action='store',
		required=False, 
		help="Set the first label to use for generating the mezzanine streams. Default: "+chr(first_label))
		
	parser.add_argument(
		'--test', dest='test', action='store',
		type=bool, required=False, nargs='?',
		help="This flag indicates the script should process the parameters and list the output streams to generate, without actually generating any streams. Default: False")
		
	parser.add_argument('ios', nargs='*', help="Source file(s) and associated output prefix.")

	args = parser.parse_args()

	if args.resolutions is not None:
		try:
			resolutions = json.loads(args.resolutions)
			print("Successfully parsed JSON resolutions argument.")
		except:
			print("Failed to parse JSON resolutions argument. Provide a string containing valid JSON, ensuring double quotes are escaped.")
			sys.exit("Mezzanine creation aborted.")
			
	if args.resolutions_json is not None:
		try:
			resolutions_json_file = open(args.resolutions_json)
			resolutions = json.load(resolutions_json_file)
			print("Successfully parsed JSON resolutions file.")
		except:
			print("Failed to parse JSON resolutions file. Ensure the file contains valid JSON. Check the path to the JSON file is correct.")
			sys.exit("Mezzanine creation aborted.")
	
	if args.first_label is not None:
		first_label = ord(args.first_label)
	
	if args.test is not None:
		test = args.test
	
	if len(args.ios)%2 != 0:
		print("Provide an output file prefix for each input source file.")
		sys.exit("Mezzanine creation aborted.")
	
	print('Resolution(s): ')
	for res, variants in resolutions.items():
		for variant in list(variants):
			if variant[3]:
				print(res+' '+str(eval(variant[0]))+'fps '+str(variant[1])+'s '+str(variant[2])+' variant(s) with a second audio track')
			else:
				print(res+' '+str(eval(variant[0]))+'fps '+str(variant[1])+'s '+str(variant[2])+' variant(s)')
	print()

	# Basic method of differentiating the input filenames (that include filename extensions) from the corresponding output prefixes
	for io in args.ios:
		if io[-4:][0] == '.':
			inputs.append(io)
			print('+ Input: '+io)
		else:
			outputs.append(io)
			print('+ Output: '+io+'_label_WxH@fps_duration-in-seconds.mp4')
	
	if test:
		print("! Test run only. Output files will not be generated.")
	print()
	print("Generating annotated mezzanine streams:")


	# For each of the input source files, generate all resolution-duration-label combinations based on the source fps
	for i,input in enumerate(inputs):
		# Get the input source file video properties using ffprobe, as the fps and duration are needed
		source_videoproperties = subprocess.check_output(['ffprobe', '-i', input, '-show_streams', '-select_streams', 'v', '-loglevel', '0', '-print_format', 'json'])
		source_videoproperties_json = json.loads(source_videoproperties)
		if 'streams'in source_videoproperties_json:
			# Get the source duration 
			source_duration = int(eval(source_videoproperties_json['streams'][0]['duration']))
			
			# Generate all resolution-duration-label combinations for this input source file, at the selected framerate (based on the source file framerate)
			generate_streams(input, source_duration, mezzanine_gen_script, font, first_label, qr_positions, resolutions, seek, start_end_indicators, window_len, outputs[i], second_audio_gen_script, test)
