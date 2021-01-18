import argparse
import os
import subprocess
import sys

from pathlib import Path
from pydub import AudioSegment, effects

import pyttsx3


def set_amplitude(audio, target_dBFS):
    dBFS_delta = target_dBFS - audio.dBFS
    return audio.apply_gain(dBFS_delta)


if __name__ == "__main__":

	# Basic argument handling
	parser = argparse.ArgumentParser(description="WAVE Mezzanine 2nd Audio Generator.")
	parser.add_argument('input', help="Source file.")
	
	args = parser.parse_args()

	# Check that source and boundaries files are present
	if not os.path.isfile(args.input):
		sys.exit("Source file \""+args.input+"\" does not exist.")

	mezzanine = Path(args.input)
	mezzanine_out = Path(str(mezzanine.parent)+'\\'+str(mezzanine.stem)+'_2ndAudio[English]'+str(mezzanine.suffix))
	
	# Generate audio to mix with mezzanine audio, creating an additional different audio track
	engine = pyttsx3.init()
	engine.setProperty('rate', 100)
	engine.setProperty('volume', 1.0)
	engine.save_to_file("English", 'temp_voice.wav')
	engine.runAndWait()

	# Normalise voice audio
	raw = AudioSegment.from_file('temp_voice.wav', 'wav')
	normalized = effects.normalize(raw)
	# normalized = set_amplitude(raw, -23.0)
	normalized.export("temp_nvoice.wav", format="wav")
	
	# Get voice audio length
	voice_duration = str(subprocess.check_output(['ffprobe', '-i', 'temp_nvoice.wav', '-show_entries', 'format=duration', '-v', 'quiet', '-of', 'csv']))
	voice_duration = float(voice_duration.split(',')[1][:-5])
	silence_duration = 15 - voice_duration
	
	# Generate silence (anullsrc=r=48000:cl=mono)
	#ffmpeg -t <silence_duration> -f lavfi -i anullsrc=channel_layout=mono:sample_rate=48000 temp_silence.wav
	subprocess.call(['ffmpeg', 
		'-t', str(silence_duration),
		'-f', 'lavfi',
		'-i', 'anullsrc=channel_layout=mono:sample_rate=48000',
		'-y',
		'temp_silence.wav'])

	# Concatenate voice and silence
	#ffmpeg -i temp_nvoice.wav -i temp_silence.wav -filter_complex "[0] [1] concat=n=2:v=0:a=1 [a]" -map "[a]" temp_voiceandsilence.wav
	subprocess.call(['ffmpeg', 
		'-i', 'temp_nvoice.wav',
		'-i', 'temp_silence.wav',
		'-filter_complex', '[0] [1] concat=n=2:v=0:a=1 [a]',
		'-map', '[a]',
		'-y',
		'temp_voiceandsilence.wav'])

	# Mix mezzanine audio with voice+silence
	#ffmpeg -i <mezzanine_file> -stream_loop -1 -i temp_voiceandsilence.wav -filter_complex "[0:a] [1] amix=inputs=2:duration=first:dropout_transition=2:weights=1 1 [a]" -map "[a]" temp_audiotrack2.wav
	subprocess.call(['ffmpeg', 
		'-i', str(mezzanine),
		'-stream_loop', '-1',
		'-i', 'temp_voiceandsilence.wav',
		'-filter_complex', '[0:a][1] amix=inputs=2:duration=first:dropout_transition=2:weights=1 1 [a]',
		'-map', '[a]',
		'-y',
		'temp_audiotrack2.wav'])

	# Normalise mixed audio
	raw = AudioSegment.from_file('temp_audiotrack2.wav', 'wav')
	#normalized = effects.normalize(raw)
	normalized = set_amplitude(raw, -23.0)
	normalized.export("temp_naudiotrack2.wav", format="wav")

	# Encode audio track
	subprocess.call(['ffmpeg', 
		'-i', 'temp_naudiotrack2.wav',
		'-c:a','aac',
		'-b:a', '320k', '-ac', '2',
		'-y',
		'temp_audiotrack2.aac'])

	# Mux new audio track into mezzanine
	#ffmpeg -i <mezzanine_file> -i temp_audiotrack2.aac -map 0 -map 1 -vcodec copy -acodec copy <mezzanine_file_with_2nd_audio>
	subprocess.call(['ffmpeg', 
		'-i', str(mezzanine),
		'-i', 'temp_audiotrack2.aac',
		'-map', '0',
		'-map', '1',
		'-vcodec','copy',
		'-acodec','copy',
		'-y',
		str(mezzanine_out)])

	# Remove the temporaray audio files
	print("Removing temporary files...", end='', flush=True)

	os.remove('temp_voice.wav')
	os.remove('temp_nvoice.wav')
	os.remove('temp_silence.wav')
	os.remove('temp_voiceandsilence.wav')
	os.remove('temp_audiotrack2.wav')
	os.remove('temp_naudiotrack2.wav')
	os.remove('temp_audiotrack2.aac')
	
	print("Done")
