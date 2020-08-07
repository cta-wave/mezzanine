## Creating WAVE mezzanine content using a single Python script

The steps to create WAVE mezzanine content have been combined into a single Python script `mezzanine.py`. 

This script does the following to the source content:
- Adds timecode, frame number with configurable zero padding, configurable label text and font:
	- Displayed in video.
	- Encoded in QR code displayed on each frame.
	- Option to configure QR code to alternate between either 2 or 4 positions.
- Adds configurable border indicators (default: `boundaries.png`).
- Integrates an A/V sync pattern at the top right of the video using modified synchronisation timing video test sequence generator scripts from [DVB companion screen synchronisation timing accuracy measurement](https://www.github.com/BBC/dvbcss-synctiming) to generate a sequence of "beeps" and "flashes" with an irregular pattern that only repeats after a configurable duration (default 31 seconds). 
- Mixes source content audio with A/V sync beeps to allow for visual lip-sync confirmation.
- Includes option to add a dark green (`0x006400`) color frame to indicate the start of the video, and a dark red (`0x8B0000`) frame to indicate the end of the video.
- Video output configured to minimise lossy nature of transcoding and preserve properties of source content. The codec used depends on source content color space:
	- H.264/AVC for BT.709 or undefined
	- H.265/HEVC for BT.2020nc or other defined value

Requirements:
* [Python 3][python]
* [Pillow >=3.4][pillow]
* [qrcode >=6.1][qrcode]
* [ffmpeg 4.3.1][ffmpeg]
* [ffprobe 4.3.1][ffmpeg]

Using the provided `requirements.txt`, execute the following to install the Python dependancies:
`pip install -r requirements.txt`

Associated assets:
- `boundaries.png`, `boundaries.xcf`, `red_triangle.xcf` frame boundary markers overlay created in [GIMP][gimp], exported to PNG
- `Cousine-Regular.ttf` monospaced font from the [Cousine font family][cousine]

Tools:
* [GIMP 2.10][gimp]

Mezzanine sources:
* [WAVE original source files][waveoriginal] 


For example, to generate an annotated mezzanine file you will need the following original files referenced above:
- `tearsofsteel_4k.mov`
- `boundaries.png`
- `Cousine-Regular.ttf`

You can then execute the following to produce the an annotated mezzanine output file: 
`py mezzanine.py -s 00:00:07.250 -d 30 -f 30 -r 1280x720 -b boundaries.png -t Cousine-Regular.ttf -l A1 -q 4 --start-end-indicators enabled --window-len 6 tearsofsteel_4k.mov tos-30sec-example.mp4`

The full details of the available commands for the script can be found by executing `py mezzanine.py -h`

[python]: https://www.python.org/
[pillow]: https://pypi.org/project/Pillow/
[qrcode]: https://pypi.org/project/qrcode/
[cousine]: https://fonts.google.com/specimen/Cousine
[ffmpeg]: https://ffmpeg.org
[gimp]: https://gimp.org
[waveorignial] http://dash-large-files.akamaized.net/WAVE/Original/


## Meta-script generating all annotated mezzanine streams

An additional Python script `metamezz.py` has been created to enable generation of all annotated mezzanine streams with a single command.
The `metamezz.py` script calls `mezzanine.py` to generate each annotated mezzanine file, so the requirements for `metamezz.py` are the same as for `mezzanine.py`. 

For each source file, an output file prefix is required: `py metamezz.py source1.mov source1_output_prefix source2.mov source2_output_prefix` and so on.

To generate the current set of [WAVE mezzanine content](http://dash-large-files.akamaized.net/WAVE/Mezzanine/) you can execute the following:
`py metamezz.py source/tearsofsteel_4k.mov mezzanine/tos source/DVB_PQ10_VandV.mov mezzanine/croatia`

This uses the default parameters, assumes the source files are in the `source` folder and generates the annotated mezzanine files in the `mezzanine` folder.

Additional parameters can be provided:
- `-r string_containing_JSON` or `-rjf path_to_JSON_file` that provide JSON defining:
	- The resolutions streams are generated in.
	- The duration of each stream generated.
	- The number of variants to create for each combination of resolution+duration.
- `-fl char` that defines the starting label to use for the list of streams (e.g. 'A').
- `-t` that is a flag indicating a test run, which will parse the parameters and list the streams to generate, but won't actually generate the streams.

Labels are used to identify the annotated mezzanine streams. They are displayed in the video, encoded in the QR codes displayed in the video, and included in the output filename.
The `metamezz.py` script uses a single character as the label, that is automatically incremented for each of the resolutions in the list, and starts with 'A' by default. 
To be able to create multiple variants for some combinations of resolution+duration, a number is appended to every label, acting as an index. 
For example, for the first resolution generated, 'A1' is the default label.
When specifying N variants for the first resolution+duration combination, N streams will be created with the labels A1 .. AN.

The default list of resolution+duration+variant combinations is also included in the `all_resolutions.json` file. 
The JSON structure used is: `{"WIDTHxHEIGHT":[[duration in seconds (int), number of variants (int)], [...]]}`
Multiple combinations of duration and variants can be defined for each resolution. 
The `all_resolutions.json` JSON file can be modified to suit your needs and passed to `metamezz.py` using the `-rjf *filename*` parameter.

The `metamezz.py` script uses the following parameter defaults that can only be modified in the script, as they are not expected to be changed often, for consistency reasons:
- The font is set to `Cousine-Regular.ttf` and is expected to be in the same folder.
- 4 QR code positions are used.
- The script seeks to 00:01:25 in the source content, unless the content is too short.
- Start and end indicators are enabled.
- The irregular AV sync pattern is set to repeat after 63 seconds.
- The script expects the presence of `mezzanine.py` in the same folder.

The full details of the available commands for the script can be found by executing `py metamezz.py -h`


# Historical mezzanine creation scripts below
### Creating WAVE mezzanine content from Tears of Steel (ToS)

### Tools Used

* [Cousine monospaced font][cousine]
* [ffmpeg 4.2.2][ffmpeg]
* [ffprobe 4.2.2][ffmpeg]
* [Gimp 2.10][gimp]
* [imagemagick 7.0.10-11][imagemagick]
* [qrencode 4.0.2][qrencode]
* [Ubuntu 20.04 LTS][ubuntu]
* [VLC 3.0.10][vlc]

### Steps

1. Download 1080p version of ToS from the Blender mirror site:
`wget http://ftp.nluug.nl/pub/graphics/blender/demo/movies/ToS/ToS-4k-1920.mov`
1. Extract a lossless 30-second segment from ToS, add top and bottom black bars to make it 16:9 aspect, 30fps, remove audio track:
`ffmpeg -i ToS-4k-1920.mov -ss 00:00:07.250 -t 00:00:30.0 -c:v libx264 -preset slower -crf 5 -filter:v "pad=1920:1080:0:140,setsar=1,fps=fps=30" -an tos-30sec-video-16-9.mp4`
1. Create a thirty-second audio track with beep every 5 seconds:
`ffmpeg -f lavfi -i "sine=beep_factor=4:duration=30" -c:a "aac" -b:a 320k -ac 2 tos-30sec-audio.m4a`
1. Export video frames at 30fps to sequence of lossless PNGs:
`mkdir frames && ffmpeg -y -i tos-30sec-video-16-9.mp4 -filter_complex "fps=fps=30" frames/%d.png`
1. Write a list of the PNGs to a text file:
`ls frames | sort -n -k1.1 > images.txt`
1. Export the timecodes of the video frames to a text file, using 00:00:00.000000 time format (ffprobe doesn't support 00:00:00.000 notation):
`ffprobe -f lavfi -i "movie=tos-30sec-video-16-9.mp4,fps=fps=30" -show_frames -show_entries frame=pkt_pts_time -sexagesimal -of csv=p=0 > frametimes.txt`
1. Trim trailing three millisecond digits from lines in frametimes.txt (must round up the remaining three because ffmpeg pts format is H:MM:SS.sss):
`awk 'BEGIN{OFS=FS=":"}{ $3=sprintf("%06.3f", $3) }1' frametimes.txt > frametimes-sss.txt`
1. Combine PNGs with frame timecodes into a tab-delimited text file:
`paste images.txt frametimes-sss.txt > images-frametimes.txt`
1. Generate QR codes (six-character clip ID, frame timestamp) for every frame.
`./qrencode.sh`
1. Apply QR codes to export PNGs (note that this script will take a while).
`./imagemagick.sh`
1. Use QR'd PNGs as sources to generate lossless MP4 file with QR codes and timecode box:
`ffmpeg -framerate 30 -start_number 0 -i "composited/%d.png" -c:v libx264 -preset slower -crf 5 -filter_complex "format=yuv420p,fps=fps=30,drawtext=fontfile=/usr/share/fonts/truetype/cousine/Cousine-Regular.ttf: text='%{pts \:hms}': x=(w-tw)/2: y=h-(4*lh): fontcolor=white: fontsize=60: box=1: boxborderw=20: boxcolor=Black" tos-qrs.mp4`
1. Create frame boundary markers overlay in Gimp, export to PNG (see boundaries.xcf and boundaries.png).
1. Create final file with frame boundary overlay and audio:
`ffmpeg -y -i tos-qrs.mp4 -i boundaries.png -i tos-30sec-audio.m4a -c:v libx264 -preset slower -crf 5 -filter_complex "[0:v][1:v] overlay=0:0,format=yuv420p,fps=fps=30" -c:a "aac" -b:a 320k -ac 2 tos-30sec-final.mp4`
1. Verify tos-30sec-final.mp4 playback in VLC. Mobile QR reader apps are available in the Apple and Google stores to verify the QR codes in each frame against the timecode.

[cousine]: https://fonts.google.com/specimen/Cousine
[ffmpeg]: https://ffmpeg.org
[gimp]: https://gimp.org
[imagemagick]: https://imagemagick.org
[qrencode]: https://fukuchi.org/works/qrencode/index.html.en
[ubuntu]: https://ubuntu.com
[vlc]: https://fonts.google.com/specimen/Cousine

### Alternate Single Script Method

The above steps have been combined into a single script `mezzanine.sh`. To accomplish the above steps with the same result you will need the following original files referenced above:

- `ToS-4k-1920.mov`
- `boundaries.png`
- `Cousine-Regular.ttf`

You can then execute the following to produce the equivalent output file:
`./mezzanine.sh -s 00:00:07.250 -d 30 -f 30 -b boundaries.png -t "Cousine-Regular.ttf" ToS-4k-1920.mov tos-30sec-final.mp4`

The full details of the available commands for the script can be found by executing `./mezzanine.sh -h`
