#!/bin/bash

function help() {
    echo "\
WAVE Mezzanine Content Creator
$0 [-b <img-file>] [-s <ss-param>] [-d <duration>] [-f <framerate>] <source-file> <output-file>

    -b, --boundaries <img-file>
        Specifies a file that contains boundary markers
        Default: boundaries.png

    -s, --seek <ss-param>
        Seeks the source file to a starting position
        Format must follow ffmpeg -ss parameter
        Default: 0

    -d, --duration <duration>
        The duration, in seconds, of the source file to process from the seek position in
        Default: 30

    -f, --framerate <framerate>
        The target framerate of the output file
        Fractional rates must be specified as division operations \"30000/1001\"
        Default: \"00:00:30.0\"

    -n, --name <string>
        Provide a name for this mezzanine, will exist in qrcode
        Default: \"cta-wave-mezzanine\"

    -t, --font <string>
        The font to utilize for drawing timecodes on frames, must be full path to file
        Default: System Specified Default

    -h, --help
        Displays this help message
"
    if [[ ! -z $1 ]]; then
        echo "Error: $1"
        exit 1
    fi
    exit
}

FONT=""
SEEK="00:00:00.000"
DURATION=30
FRAMERATE=30
BOUNDARIES="boundaries.png"
NAME="cta-wave-mezzanine"

POSITIONAL=()
while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--boundaries)
        BOUNDARIES="$2"
        shift
        shift
        ;;
        -s|--seek)
        SEEK="$2"
        shift
        shift
        ;;
        -d|--duration)
        DURATION="$2"
        shift
        shift
        ;;
        -f|--framerate)
        FRAMERATE="$2"
        shift
        shift
        ;;
        -n|--name)
        NAME="$2"
        shift
        shift
        ;;
        -t|--font)
        FONT="$2"
        shift
        shift
        ;;
        -h|--help)
        help
        ;;
        *)
        POSITIONAL+=("$1")
        shift
        ;;
    esac
done
set -- "${POSITIONAL[@]}"

SOURCE=$1
OUTPUT=$2

if [[ -z $SOURCE ]] || [[ -z $OUTPUT ]]; then
    help "Both <source-file> and <output-file> must be specified"
fi

if [[ ! -f $SOURCE ]]; then
    help "<source-file> (\"$SOURCE\") does not exist"
fi

if [[ ! -f $BOUNDARIES ]]; then
    help "Boundaries <img-file> (\"$BOUNDARIES\") does not exist"
fi

# Helper for performing rounded float operations since bash cannot directly do this
function roundedfloat {
    awk "BEGIN {printf \"%.$2f\", $1}"
}

# Generates a series of timestamped QR codes at the framerate of the target output
# Each QR code is generated and output to stdout
function generateqrcodes {
    FRAME_DURATION=`roundedfloat "1/($FRAMERATE)" 10`
    FRAME_COUNT=`roundedfloat "($FRAMERATE)*$DURATION" 0`

    FRAME_PTS=0
    for (( i=0; i<$FRAME_COUNT; i++))
    do
        TIMECODE=`awk "BEGIN {printf \"%d:%02d:%06.3f\", $FRAME_PTS/3600, $FRAME_PTS/60, $FRAME_PTS%60;}"`
        qrencode -l H -s 6 -o - "$NAME,$TIMECODE"

        # Note that simple multiplication of frame duration is too accurate, instead the
        # pts must be computed by adding the accurate frame duration to the rounded pts.
        # This is still not exactly correct after the 5th digit, but we round to 3 digits
        # for the timestamp and that will always match the drawtext value precision
        FRAME_PTS=`roundedfloat "$FRAME_PTS+$FRAME_DURATION" 7`
    done
}

# This large command accomplishes the Mezzanine transform in one decode go:
# - Generates a set of per-frame QR codes for our expected target duration and outputs them to stdout
# - Starts FFMPEG with 4 input sources
#   [0] A virtual audio source that beeps every second
#   [1] The original video source seeked to the desired point
#   [2] An image file of frame boundary markers
#   [3] A series of qr code images at the target framerate from stdin
# - Applies the following complex filter to the demuxed inputs:
#   - Takes the video stream from the original source and:
#       - Adds top/bottom black bars to make it 16:9
#       - Forces the framerate to the desired framerate
#       - Fixes the output format to yuv420p
#       - Draws the timecode of the current frame onto it
#   - Takes the modified video stream and overlays the boundary marker at full screen
#   - Takes the video stream + overlay and overlays a qr code at alternating positions
#  - The output of the filter is then:
#   - Encoded in h264 and aac
#   - Fixed to the desired duration
#   - Written to the supplied output location

generateqrcodes | \
    ffmpeg \
        -f lavfi -i "sine=beep_factor=4" \
        -ss $SEEK -i $SOURCE \
        -i $BOUNDARIES \
        -framerate $FRAMERATE -f image2pipe -vcodec png -i - \
        -filter_complex " \
            [1:v]\
                pad=1920:1080:0:140,\
                setsar=1,\
                format=yuv420p,\
                fps=fps=$FRAMERATE,\
                drawtext=\
                    fontfile=$FONT:\
                    text='%{pts \:hms}':\
                    x=(w-tw)/2:\
                    y=h-(4*lh):\
                    fontcolor=white:\
                    fontsize=60:\
                    box=1:\
                    boxborderw=20:\
                    boxcolor=black\
            [framed]; \
            [framed][2] \
                overlay=\
                    repeatlast=1 \
            [bounded]; \
            [bounded][3] \
                overlay=\
                    x=130: \
                    y=320+'if(eq(mod(n,2),0),230,0)' \
            [stamped]\
        " \
        -map '[stamped]' \
        -map 0:a:0 \
        -c:v libx264 -preset slower -crf 5 \
        -c:a aac -b:a 320k -ac 2 \
        -t $DURATION \
        -y \
        $OUTPUT

