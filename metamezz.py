import os
import subprocess


def generate_streams(input, source_duration, mezzanine_gen_script, font, qr_positions, resolutions, seek, start_end_indicators, window_len, tonemap, output, second_audio_gen_script, test):
	"""\
	Calls the WAVE mezzanine generation script to create annotated mezzanine streams using the input source content
	for each of the combinations defined in the resolutions parameter.
	
	:param input: The path to the source content for which annotated mezzanine streams will be generated.
	:param source_duration: The source content duration (in seconds).
	:param mezzanine_gen_script: The path to the mezzanine generation Python script.
	:param font: The path to/name of the font file to use when generating the annotations.
	:param qr_positions: The number of annotation on-screen QR code positions to use, may be 2 or 4.
	:param resolutions: Dictionary containing the combinations to generate annotated mezzanine streams for, using the source content. 
						Structure: {'WIDTHxHEIGHT':[[framerate (str), duration in seconds (int), label (str), number of variants (int), add second audio track (bool)], []]}
	:param seek: Seeks the source file to a starting position. Format must follow ffmpeg -ss parameter.
	:param start_end_indicators: Append a single frame before and after the source content, to signal the start and end of the test sequence. 
								 May be "enabled", "disabled", "start" (only) or "end" (only).
	:param window_len: Unique pattern window length (in seconds) for the annotated mezanine beep/flash sequence, which will repeat after 2^n -1 seconds. 
	:param tonemap: Enables rudimentary tone mapping to BT.709 SDR. Forces output in H.264/AVC. May be "enabled" or "disabled".
	:param output: The output annotated mezzanine file prefix. May include path.
	:param second_audio_gen_script: The path to the second audio track generation Python script.
	:param test: When this flag (bool) is set, stream creation is disabled. Used to create a list of the output streams without generating them.
	"""
	
	for res in resolutions.keys():
		for variant in resolutions.get(res):
			fps = variant[0]
			duration = variant[1]
			nb_variant_labels = variant[3]
			add_second_audio_track = variant[4]
			variant_label_range = range(nb_variant_labels)
			for variant_label in list(variant_label_range): 
				label_str = variant[2]+str(variant_label+1)
				if tonemap == 'enabled':
					print('[->BT.709 SDR] ', end="")
				if add_second_audio_track:
					print(str(output)+'_'+label_str+'_'+res+'@'+str(round(eval(fps),3))+'_'+str(duration)+'_2ndAudio[English].mp4')
				else:
					print(str(output)+'_'+label_str+'_'+res+'@'+str(round(eval(fps),3))+'_'+str(duration)+'.mp4')
				if not test:
					if not add_second_audio_track or (add_second_audio_track and not os.path.isfile(str(output)+'_'+label_str+'_'+res+'@'+str(round(eval(fps),3))+'_'+str(duration)+'.mp4')):
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
									'--tonemap', str(tonemap),
									str(input),
									str(output)+'_'+label_str+'_'+res+'@'+str(round(eval(fps),3))+'_'+str(duration)+'.mp4'
									])		
					if add_second_audio_track:
						subprocess.run(['python', second_audio_gen_script, 
								str(output)+'_'+label_str+'_'+res+'@'+str(round(eval(fps),3))+'_'+str(duration)+'.mp4'
								])


if __name__ == "__main__":

	import argparse
	import json
	import sys
	
	from pathlib import Path
	
	# Default parameters
	
	# Dictionary of resolutions (keys) with values indicating:
	#		- the frame rate of the stream(s) to create, 
	#		- the length of the stream(s) to create in seconds, 
	#		- the label to use for these variants,
	#		- the number of variants with this resolution, frame rate and label,
	#		- whether to add a second audio track to these variants (True or False)
	# Format: 
	#	'WIDTHxHEIGHT':[[framerate (str), duration in seconds (int), label (str), number of variants (int), add second audio track (bool)], []]
	# Notes: 
	#	Fractional rates must be specified as division operations e.g. '30000/1001'. 
	# 	Variants are streams that are identical except for their labels, which have a number appended.
	# 	E.g. with label 'A' when generating 2 variants, output streams will have labels 'A1' and 'A2'.
	resolutions = {
		'480x270':[['30',60,"A",1,False]],
		'512x288':[['30',60,"B",1,False]],
		'640x360':[['30',60,"C",1,False]],
		'704x396':[['30',60,"D",1,False]],
		'720x404':[['30',60,"E",1,False]],
		'768x432':[['30',60,"F",1,False]],
		'852x480':[['30',60,"G",1,False]],
		'960x540':[['30',60,"H",1,False]],
		'1024x576':[['30',60,"I",2,False]],
		'1280x720':[['30',60,"J",1,False]],
		'1600x900':[['30',60,"K",1,False]],
		'1920x1080':[['30',60,"L",2,False],['30',60,"L",1,True]]
	}
	
	# Arrays of source files (inputs) and associated output file prefixes (outputs)
	inputs = []
	outputs = []
	
	# Parameters for mezzanine.py not configurable via argument
	mezzanine_gen_script = Path('mezzanine.py')
	font = Path('Cousine-Regular.ttf')
	qr_positions = 4
	seek = '00:01:25'
	start_end_indicators = 'enabled'
	window_len = 6	#63 seconds
	
	# Paramaeters for add_second_audio_track.py not configurable via argumemt
	second_audio_gen_script = Path('add_second_audio_track.py')
	
	# Test run flag: used to parse inputs and print list of streams to generate without actually creating the output streams
	test = False
	
	# Tonemap setting: enables rudimentary tone mapping of source content to BT.709 SDR
	tonemap = ['disabled']
	
	# Basic argument handling
	parser = argparse.ArgumentParser(description="WAVE Mezzanine Batch Content Creator.")
	
	parser.add_argument(
		'-r', '--resolutions', dest='resolutions',  action='store', 
		required=False, 
		help="Specifies the resolutions, duration, label, number of label variants in which to generate the content, and whether to create a variant with a second audio track. JSON format: {\"WIDTHxHEIGHT\":[[framerate (str), duration in seconds (int), label (str), number of variants (int), add second audio track (bool)], []]}. Default:"+json.dumps(resolutions))
	
	parser.add_argument(
		'-rjf', '--resolutions-json-file', dest='resolutions_json',  action='store', 
		nargs='*',
		required=False, 
		help="Specifies the path to one or more JSON files containing resolutions, duration, label, number of label variants in which to generate the content, and whether to create a variant with a second audio track. JSON files are associated with source files in order. When only 1 source file is provided, all JSON files will be associated with it. JSON format: {\"WIDTHxHEIGHT\":[[framerate (str), duration in seconds (int), label (str), number of variants (int), add second audio track (bool)], []]}")
	
	parser.add_argument(
		'--test', dest='test', action='store',
		type=bool, required=False, nargs='?',
		help="This flag indicates the script should process the parameters and list the output streams to generate, without actually generating any streams. Default: False")
	
	parser.add_argument(
		'--tonemap', 
		nargs='*',
		required=False, 
		choices=['enabled','disabled'], 
		help="Enables rudimentary tone mapping of BT.2020nc HDR content to BT.709 SDR. Forces output in H.264/AVC. May be \"enabled\" or \"disabled\". Specify a single value for all source files or multiple values, one for each source file in order. Default: disabled")
	
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
			if len(args.resolutions_json) > 1:
				resolutions = []
				for json_file in args.resolutions_json:
					json_file_path = Path(json_file)
					resolutions_json_file = open(json_file_path)
					print("Successfully opened JSON resolutions file "+str(json_file_path))
					resolutions.append(json.load(resolutions_json_file))
					print("Successfully parsed JSON resolutions file "+str(json_file_path))
			else:
				json_file_path = Path(args.resolutions_json[0])
				resolutions_json_file = open(json_file_path)
				print("Successfully opened JSON resolutions file "+str(json_file_path))
				resolutions = json.load(resolutions_json_file)
				print("Successfully parsed JSON resolutions file "+str(json_file_path))
		except:
			print("Failed to parse JSON resolutions file. Ensure the file contains valid JSON. Check the path to the JSON file is correct.")
			sys.exit("Mezzanine creation aborted.")
	
	if args.test is not None:
		test = args.test
		
	if args.tonemap is not None :
		tonemap = args.tonemap
	
	if len(args.ios)%2 != 0:
		print("Provide an output file prefix for each input source file.")
		sys.exit("Mezzanine creation aborted.")
	
	# Basic method of differentiating the input filenames (that include filename extensions) from the corresponding output prefixes
	for io in args.ios:
		if io[-4:][0] == '.':
			inputs.append(Path(io))
			print('+ Input: '+io)
		else:
			outputs.append(Path(io))
			print('+ Output: '+io+'_label_WxH@fps_duration-in-seconds.mp4')
		
	total_streams = 0
	print()
	print('Resolution(s): ')
	if isinstance(resolutions,list) and len(inputs) > 1:
		for i,input in enumerate(inputs):
			print('+ Using source: '+str(input), end ="")
			if i == 0 and tonemap[0] == 'enabled':
				print(' tonemapped to BT.709 SDR')
			elif i > 0 and len(tonemap) > 1:
				if tonemap[i] == 'enabled':
					print(' [tonemapped to BT.709 SDR]')
				else:
					print()
			else:
				print()
			for res, variants in resolutions[i].items():
				for variant in list(variants):
					if variant[4]:
						print(res+' '+str(round(eval(variant[0]),3))+'fps '+str(variant[1])+'s '+str(variant[3])+' variant(s) with a second audio track')
					else:
						print(res+' '+str(round(eval(variant[0]),3))+'fps '+str(variant[1])+'s '+str(variant[3])+' variant(s)')
					total_streams += 1
	elif isinstance(resolutions,list):
		for resolution_group in resolutions:
			for res, variants in resolution_group.items():
				for variant in list(variants):
					if variant[4]:
						print(res+' '+str(round(eval(variant[0]),3))+'fps '+str(variant[1])+'s '+str(variant[3])+' variant(s) with a second audio track')
					else:
						print(res+' '+str(round(eval(variant[0]),3))+'fps '+str(variant[1])+'s '+str(variant[3])+' variant(s)')
					total_streams += 1
	else:
		for res, variants in resolutions.items():
			for variant in list(variants):
				if variant[4]:
					print(res+' '+str(round(eval(variant[0]),3))+'fps '+str(variant[1])+'s '+str(variant[3])+' variant(s) with a second audio track')
				else:
					print(res+' '+str(round(eval(variant[0]),3))+'fps '+str(variant[1])+'s '+str(variant[3])+' variant(s)')
				total_streams += 1
	print()
	
	print(str(total_streams)+" stream(s) will be generated in total.")
	print()
	
	if test:
		print("! Test run only. Output files will not be generated.")
	print()
	print("Generating annotated mezzanine streams:")
	
	# For each of the input source files, generate all the combinations defined in the resolutions parameter
	for i,input in enumerate(inputs):
		# Get the input source file video properties using ffprobe, as the duration is needed
		source_videoproperties = subprocess.check_output(['ffprobe', '-i', str(input), '-show_streams', '-select_streams', 'v', '-loglevel', '0', '-print_format', 'json'])
		source_videoproperties_json = json.loads(source_videoproperties)
		if 'streams'in source_videoproperties_json:
			# Get the source duration 
			source_duration = int(eval(source_videoproperties_json['streams'][0]['duration']))
			# Determine which tonemap parameter to use depending on whether one is provided per input file or only one is provided for all input files
			if len(tonemap) > 1:
				j = i
			else:
				j = 0
			# Handle multiple JSON files containing the resolutions
			if isinstance(resolutions,list):
				# If only 1 input file but multiple resolution JSON files, then we use the same input file for each of the resolution JSON files
				if len(inputs) == 1:
					for resolutions_group in resolutions:
						generate_streams(input, source_duration, mezzanine_gen_script, font, qr_positions, resolutions_group, seek, start_end_indicators, window_len, tonemap[0], outputs[0], second_audio_gen_script, test)
				# If there are multiple input files and JSON files containing the resolutions, we match them in order
				else:
					generate_streams(input, source_duration, mezzanine_gen_script, font, qr_positions, resolutions[i], seek, start_end_indicators, window_len, tonemap[j], outputs[i], second_audio_gen_script, test)
			# Handle a single JSON file/object containing the resolutions
			else:
				generate_streams(input, source_duration, mezzanine_gen_script, font, qr_positions, resolutions, seek, start_end_indicators, window_len, tonemap[j], outputs[i], second_audio_gen_script, test)
