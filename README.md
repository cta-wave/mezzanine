# About this Repo

This repo holds code and associated elements for automatically generating annotated WAVE mezzanine content from raw source material.  The annotations in the resulting 
multimedia files are used by the WAVE test suite to programmatically identify content parameters and to verify various elements of performance.  The WAVE Project is an 
industry interoperability effort for streaming internet video supported by over 60 companies and hosted by the Consumer Technology Association.  For more information on 
the WAVE Project, the WAVE test suite, please see [CTA.tech/WAVE](https://CTA.tech/WAVE) or email standards@CTA.tech.”


# Contents

1. [Creating annotated WAVE mezzanine content](#creating-annotated-wave-mezzanine-content)
2. [Generating all annotated WAVE mezzanine content](#generating-all-annotated-wave-mezzanine-content)
3. [Experimental scripts](#experimental-scripts)


# Creating annotated WAVE mezzanine content 

The steps to create annotated WAVE mezzanine content have been combined into a single Python script `mezzanine.py`. 

The `mezzanine.py` script does the following to the source content:
- Adds timecode, frame number with configurable zero padding, frame rate, configurable label text and font:
	- Displayed in video.
	- Encoded in QR code displayed on each frame.
	- Option to configure QR code to alternate between either 2 or 4 positions.
- Adds a low density bit pattern for each frame that signals:
	- Frame number.
	- Total frames.
	- Frame rate.
	- Horizontal resolution.
	- Vertical resolution.

  Note: The QR code is intended for black-box testing of devices using a camera to capture the video output,
  without requiring manufacturer involvement. The bit pattern is intended for white-box testing, where the video is
  processed directly within a device.
- Adds border indications:
	- Red triangular indicators (`assets/boundaries.png`).
	- 2 pixel wide border around the edge of the video (outer 1px white, inner 1px black).
- Integrates an A/V sync pattern at the top right of the video 
  using modified synchronisation timing video test sequence generator scripts 
  from [DVB companion screen synchronisation timing accuracy measurement](https://www.github.com/BBC/dvbcss-synctiming). 
  The pattern is an irregular sequence of "beeps" and "flashes" that only repeats after a configurable duration 
  (default 31 seconds).
- Mixes source content audio with A/V sync beeps to allow for visual lip-sync confirmation.
- Includes option to add a dark green (`0x006400`) color frame to indicate the start of the video, 
  and a dark red (`0x8B0000`) frame to indicate the end of the video.
- Optionally applies rudimentary tone-mapping to BT.709 SDR for each input file, 
  to create SDR mezzanine streams using an HDR source.
- Generates JSON metadata related to the mezzanine content, encoding, output file and source file. 
  This includes the mezzanine release version, and the corresponding WAVE Test Content Format Specification version.
- Video output configured to minimise lossy nature of transcoding and preserve properties of source content. 
  The codec used depends on source content color space:
	- H.264/AVC for BT.709 or undefined
	- H.265/HEVC for BT.2020nc or other defined value
  
  Note: These codecs are used to ensure the properties of the content are signalled correctly. 
  A more appropriate mezzanine video codec or raw YUV data may be used in future.

Requirements:
* [Python 3][python]
* [Pillow >=3.4][pillow]
* [qrcode >=6.1][qrcode]
* [ffmpeg][ffmpeg] (use a recent build from the master branch)
* [ffprobe][ffmpeg] (use a recent build from the master branch)

Using the provided `requirements.txt`, execute the following to install the Python dependencies:
`pip install -r requirements.txt`

Associated assets:
- `boundaries.png`, `boundaries.xcf`, `red_triangle.xcf` frame boundary markers overlay created in [GIMP][gimp]
- `Cousine-Regular.ttf` monospaced font from the [Cousine font family][cousine]

Tools:
* [GIMP 2.10][gimp]

Mezzanine sources:
* [WAVE original source files][waveorignial]

For example, you can execute the following command to produce an annotated mezzanine file:  
`py mezzanine.py --duration 60 --framerate 30 --label J1 --qr-positions 4 --resolution 1280x720 --seek 00:01:25 
--start-end-indicators enabled --font assets/Cousine-Regular.ttf --window-len 6 --tonemap disabled 
--version 2 --spec-version 1 --metadata-only disabled 
source/tearsofsteel_4k.mov _mezzanine/tos_J1_1280x720@30_60.mp4`

The full details of the available commands for the script can be found by executing `py mezzanine.py -h`

[python]: https://www.python.org/
[pillow]: https://pypi.org/project/Pillow/
[qrcode]: https://pypi.org/project/qrcode/
[cousine]: https://fonts.google.com/specimen/Cousine
[ffmpeg]: https://ffmpeg.org/
[gimp]: https://gimp.org/
[waveorignial]: https://dash-large-files.akamaized.net/WAVE/Original/


# Generating all annotated WAVE mezzanine content

The `metamezz.py` Python script enables generation of multiple annotated mezzanine streams with a single command, 
using `mezzanine.py` to generate each annotated mezzanine file. 

The requirements for `metamezz.py` are the same as for `mezzanine.py`. 

At least one source file and an output file prefix pair must be specified, for example:
`py metamezz.py source1.mov source1_output_prefix`

Additional parameters determine the specific annotated mezzanine files to generate (see further).

WAVE annotated mezzanine filenames use the following template: 
`<prefix>_<label>_<WxH>@<fps>_<duration>.mp4`

Where:
- `prefix` is a short string based on the source content used, e.g. "tos" for Tears of Steel.
- `label` is a short string used to identify a particular piece of test content, e.g. "A1", "L1", "L2".
- `W` and `H` are the horizontal and vertical resolutions in pixels.
- `fps` is the frame rate.
- `duration` is the duration of the annotated mezzanine content, in seconds.

For example: `croatia_O2_3840x2160@50_60.mp4`  or `tos_L1_1920x1080@60_60.mp4`

To generate a complete set of [WAVE mezzanine content](https://dash-large-files.akamaized.net/WAVE/Mezzanine/releases/) 
you can execute the following 2 commands:

`py metamezz.py 
"source\tearsofsteel_4k.mov" _mezzanine\tos 
"source\tearsofsteel_4k.mov" _mezzanine\tos 
"source\DVB_PQ10_VandV.mov" _mezzanine\croatia 
-rjf 
rjf\resolutions_15_30_60_fractional.json 
rjf\resolutions_15_30_60_non-fractional.json 
rjf\resolutions_12.5_25_50.json 
--tonemap disabled disabled enabled --spec-version 1 --version 2`

`py metamezz.py 
"source\tearsofsteel_4k.mov" _mezzanine\splice_main_tos 
"source\tearsofsteel_4k.mov" _mezzanine\splice_main_tos 
"source\DVB_PQ10_VandV.mov" _mezzanine\splice_main_croatia 
"source\Big Buck Bunny trailer_1080p30.mp4" _mezzanine\splice_ad_bbb 
"source\Big Buck Bunny trailer_1080p30.mp4" _mezzanine\splice_ad_bbb 
"source\Big Buck Bunny trailer_1080p.mov" _mezzanine\splice_ad_bbb 
-rjf 
rjf\splice_main_resolutions_30_fractional.json 
rjf\splice_main_resolutions_30_non-fractional.json 
rjf\splice_main_resolutions_25.json 
rjf\splice_ad_resolutions_30_fractional.json 
rjf\splice_ad_resolutions_30_non-fractional.json 
rjf\splice_ad_resolutions_25.json 
--tonemap disabled disabled enabled disabled disabled disabled --spec-version 1 --version 2`

This assumes the source files are located in the `source` folder, and the JSON files in the `rjf` folder.
The annotated mezzanine files generated are saved to the `_mezzanine` folder,
with the prefixes `tos` and `croatia` for the main mezzanine content, 
and with the prefixes `splice_main_tos`, `splice_main_croatia` and `splice_ad_bbb` for the splicing mezzanine content.
Tone-mapping is enabled for the croatia content, as the source is HDR, 
but the desired output for the mezzanine content is SDR.
The mezzanine release version is set to 2,
and the corresponding WAVE Test Content Format Specification version is set to 1.

The following set of JSON files is used to generate all WAVE annotated mezzanine content.
These JSON files are passed to `metamezz.py` using the `-rjf` parameter.
- Main annotated mezzanine content (60 second duration):
	- resolutions_12.5_25_50.json -- 12.5/25/50 fps
	- resolutions_15_30_60_fractional.json -- 14.985/29.97/59.94 fps
	- resolutions_15_30_60_non-fractional.json -- 15/30/60 fps
- Shorter main annotated mezzanine content for splicing tests (10 second duration):
	- splice_main_resolutions_25.json -- 12.5/25/50 fps
	- splice_main_resolutions_30_fractional.json -- 14.985/29.97/59.94 fps
	- splice_main_resolutions_30_non-fractional.json -- 15/30/60 fps
- "Ad" annotated mezzanine content for splicing tests (duration depends on frame rate):	
	- splice_ad_resolutions_25.json -- 12.5/25/50 fps (5.76 second duration)
	- splice_ad_resolutions_30_fractional.json -- 14.985/29.97/59.94 fps (21.255 second duration)
	- splice_ad_resolutions_30_non-fractional.json -- 15/30/60 fps (6.4 second duration)

The JSON structure used is: 
`{ "WIDTHxHEIGHT" : 
	[ [framerate (str), duration in seconds (float), starting position in source (str, HH:MM:SS), 
		label (str), number of variants (int), add second audio track (bool)], 
	[...] ]}`

Multiple combinations of frame rate, duration, start position, label and variants (with/without second audio track) 
can be defined for each resolution.  

Details of the available commands for the script can be obtained by executing `py metamezz.py -h`

Here is a brief description of the parameters:
- `-m enabled || disabled` disables mezzanine generation and only (re)generates JSON metadata using existing mezzanine 
   files. The source and output mezzanine files must both be present at the paths provided.
- `-r <string_containing_JSON>` or `-rjf <path_to_JSON_file>` that provide JSON defining the following properties 
  of the generated mezzanine content:
	- Resolution (width x height).
	- Frame rate (string, fractional rates must be specified as division operations, e.g. 30000/1001).
	- Duration (in seconds).
  	- Starting position in source content (string with timestamp using the HH:MM:SS notation).
	- Label (one or more characters, e.g. 'A', 
	  followed by a number, appended automatically for each variant starting from 1).
	  Labels are used to identify the different annotated mezzanine streams. They are displayed in the video, 
	  encoded in the QR codes displayed in the video, and included in the output filename. 
	  The character(s) identify the particular combination of {resolution, frame rate, duration}. 
	  The following number identifies the variant (see below). E.g. 'A1', ... 'ÁN', 'B1', ..., 'BN'.
	- The number of variants to create for each combination of 
	  {resolution, frame rate, duration, starting position, label}. 
	  A variant is a duplicate of the same mezzanine content with a different label (same letter, different number).
	  Specifying N variants for a combination with label 'A' would result in mezzanine streams with labels 'A1' to 'AN'.
	- Flag (boolean) that determines whether to generate a second audio track for streams from a particular combination 
	  of {resolution, frame rate, duration, starting position, label, number of variants}.
- `--tonemap [enabled || disabled, ...]` enables or disables rudimentary tone-mapping to BT.709 SDR for each input file, 
  to create SDR mezzanine streams using an HDR source. 
  Provide one value, and it will apply to all input source files. 
  Alternatively, provide one value per input source file, separated by a space.
- `--test 1 || True` is a flag indicating a test run, which will parse the parameters and list the streams to generate, 
  but won't actually generate the streams.

The `metamezz.py` script uses the following parameter defaults that can only be modified in the script, 
as they are not expected to be changed often, for consistency reasons:
- The script expects the presence of `mezzanine.py` in the same folder.
- The default border indicators are used and `boundaries.png` is expected to be in the `assets` folder.
- The font is set to `Cousine-Regular.ttf` and is expected to be in the `assets` folder.
- 4 QR code positions are used.
- Start and end indicators are enabled.
- The irregular AV sync pattern is set to repeat after 63 seconds.



# Experimental scripts

## Adding a second audio track to a mezzanine stream
The `add_second_audio_track.py` Python script uses the [`pyttsx3`][pyttsx3] library 
to create an audio file with the spoken audio "English". This is mixed with the original audio of a mezzanine file, 
repeating the spoken audio every 15 seconds. 

The script makes a copy of a mezzanine file, incorporating the new audio track as a second audio track.
The first audio track remains the same as in the original mezzanine file.

The output file naming convention is as follows: 
`<mezzanine_stream_name>_2ndAudio[English].<mezzanine_stream_file_extension>`

Usage example: 
`add_second_audio_track.py tos_A1_480x270@30_60.mp4` creates `tos_A1_480x270@30_60_2ndAudio[English].mp4`

Additional requirements:
* [pydub >=0.24.1][pydub]
* [pyttsx3 >=2.90][pyttsx3]

[pydub]: https://github.com/jiaaro/pydub/
[pyttsx3]: https://github.com/nateshmbhat/pyttsx3