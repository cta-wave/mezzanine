#!/bin/bash

FONT="monospace"
SEEK="00:00:00.000"
DURATION=30
FRAMERATE=30
BOUNDARIES="boundaries.png"
RESOLUTION="1920x1080"
WIDTH=""  # Pulled from RESOLUTION string, see below
HEIGHT="" # Pulled from RESOLUTION string, see below
LABEL="mezz"
FRAME_NUMBER_PADDING=7

function help() {
    echo "\
WAVE Mezzanine Content Creator
$0 [<flags>] <source-file> <output-file>

    -b, --boundaries <img-file>
        Specifies a file that contains boundary markers
        Default: $BOUNDARIES

    -d, --duration <duration>
        The duration, in seconds, of the source file to process from the seek position in
        Default: $DURATION

    -f, --framerate <framerate>
        The target framerate of the output file
        Fractional rates must be specified as division operations \"30000/1001\"
        Default: $FRAMERATE

    --frame-number-padding <padding>
        The amount of zero padding to use when displaying the current frame number
        Default: ${FRAME_NUMBER_PADDING}

    -h, --help
        Displays this help message

    -l, --label <string>
        Provide a label for this mezzanine, will exist in qrcodes and on-screen
        Default: \"$LABEL\"

    -r, --resolution <string>
        The target resolution of the output, video will be scaled and padded to fit resolution
        Should be specified as \"<width>x<height>\"
        Default: \"$RESOLUTION\"

    -s, --seek <ss-param>
        Seeks the source file to a starting position
        Format must follow ffmpeg -ss parameter
        Default: \"$SEEK\"

    -t, --font <string>
        The font to utilize for drawing timecodes on frames, must be full path to file
        Default: System Specified Default for $FONT
"
    if [[ ! -z $1 ]]; then
        echo "Error: $1"
        exit 1
    fi
    exit
}

POSITIONAL=()
while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--boundaries)
        BOUNDARIES="$2"
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
        --frame-number-padding)
        FRAME_NUMBER_PADDING=$2
        shift
        shift
        ;;
        -h|--help)
        help
        ;;
        -l|--label)
        LABEL="$2"
        shift
        shift
        ;;
        -r|--resolution)
        RESOLUTION="$2"
        shift
        shift
        ;;
        -t|--font)
        FONT="$2"
        shift
        shift
        ;;
        -s|--seek)
        SEEK="$2"
        shift
        shift
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

# Grab width and height from input resolution
WIDTH=$(awk -Fx '{print $1}' <<< $RESOLUTION)
HEIGHT=$(awk -Fx '{print $2}' <<< $RESOLUTION)

if [[ -z $WIDTH ]] || [[ -z $HEIGHT ]]; then
    help "Resolution must be form of <width>x<height>, given: \"$RESOLUTION\""
fi

# Helper for performing rounded float operations since bash cannot directly do this
function roundedfloat {
    awk "BEGIN {printf \"%.$2f\", $1}"
}

# Compute QR size relative to output framing, target 25% frame height
QR_SIZE=`roundedfloat "$HEIGHT*0.25" 0`

# Generates a series of timestamped QR codes at the framerate of the target output
# Each QR code is generated and output to stdout
function generateqrcodes {
    FRAME_COUNT=`roundedfloat "($FRAMERATE)*$DURATION" 0`
    FRAME_DURATION=`roundedfloat "1/($FRAMERATE)" 10`

    FRAME_PTS=0
    for (( i=0; i<$FRAME_COUNT; i++))
    do
        TIMECODE=`awk "BEGIN {printf \"%d:%02d:%06.3f\", $FRAME_PTS/3600, $FRAME_PTS/60, $FRAME_PTS%60;}"`
        PADDED_FRAME=`printf %0${FRAME_NUMBER_PADDING}d $i`
        qrencode -l H -s 6 -o - "$LABEL;$TIMECODE;$PADDED_FRAME"

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
#       (thread queuing set high to avoid waiting on qr gen)
# - Applies the following complex filter to the demuxed inputs:
#   - Takes the video stream from the original source and:
#       - Scales it to the desired output size while preserving original ratio
#       - Adds top/bottom black bars to enforce a 16:9 frame
#       - Fixes the output format to yuv420p
#       - Forces the framerate to the desired framerate
#       - Draws the timecode of the current frame onto it
#   - Takes the boundary marker and:
#       - Scales it to the desired output size
#   - Takes the qr code stream and:
#       - Scales them relative to their final positioning in the composition
#   - Performs a series of overlay compositions
#       - Uses the padded source as the base
#       - Full screen overlays the scaled boundary marker
#       - Places the QR codes in a pattern based on frame number
#  - Post filter the output is mapped as follows:
#   - Video is the output of the last overlay composition
#   - Audio is directly from the beep input
#  - The mapped outputs are then:
#   - Encoded in h264 for video and aac for audio
#   - Fixed to the desired output framerate
#   - Fixed to the desired duration
#   - Written to the supplied output location (overwriting is enabled)

generateqrcodes | \
    ffmpeg \
        -f lavfi -i "sine=beep_factor=4" \
        -ss $SEEK -i $SOURCE \
        -i $BOUNDARIES \
        -framerate $FRAMERATE -f image2pipe -thread_queue_size 512 -vcodec png -i - \
        -filter_complex "\
            [1:v]\
                scale=\
                    size=${WIDTH}x${HEIGHT}:\
                    force_original_aspect_ratio=decrease,\
                setsar=1,\
                pad=\
                    w=$WIDTH:\
                    h=$HEIGHT:\
                    x=(ow-iw)/2:\
                    y=(oh-ih)/2,\
                format=yuv420p,\
                fps=fps=$FRAMERATE,\
                drawtext=\
                    fontfile=$FONT:\
                    text='$LABEL':\
                    x=(w-tw)/2:\
                    y=(4*lh):\
                    fontcolor=white:\
                    fontsize=h*0.06:\
                    box=1:\
                    boxborderw=10:\
                    boxcolor=black,\
                drawtext=\
                    fontfile=$FONT:\
                    text='%{pts\:hms};%{eif\:n\:d\:${FRAME_NUMBER_PADDING}}':\
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
                    size=${WIDTH}x${HEIGHT}\
            [boundaries];\
            [3]\
                scale=\
                    w=${QR_SIZE}:\
                    h=-1\
            [qrs];\
            [content][boundaries]\
                overlay=\
                    repeatlast=1\
            [bounded];\
            [bounded][qrs]\
                overlay=\
                    x=main_w*0.1:\
                    y='if(eq(mod(n,2),0),main_h*0.2,main_h*0.8-overlay_h)'\
            [vfinal]\
        " \
        -map '[vfinal]' \
        -map '0:a' \
        -c:v libx264 -preset slower -crf 5 \
        -c:a aac -b:a 320k -ac 2 \
        -r $FRAMERATE \
        -t $DURATION \
        -y \
        $OUTPUT

