# Creating WAVE mezzanine content from Tears of Steel (ToS)

## Tools Used

* [Cousine monospaced font][cousine]
* [ffmpeg 4.2.2][ffmpeg]
* [ffprobe 4.2.2][ffmpeg]
* [Gimp 2.10][gimp]
* [imagemagick 7.0.10-11][imagemagick]
* [qrencode 4.0.2][qrencode]
* [Ubuntu 20.04 LTS][ubuntu]
* [VLC 3.0.10][vlc]

## Steps

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
