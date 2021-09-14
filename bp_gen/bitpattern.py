# Generates a bit pattern containing frame number, total frames, frame rate, horizontal and vertical resolution
# Step 1: define bit pattern for 240x135 video
# Step 2: upscale as needed towards target resolution
# Note: intended for 480x270 video with 2x2 bit pattern "bit" size as the lowest resolution
def bp_create(bitpat_file_dir, frame_number, nof_frames, framerate, pix_per_ln, ln_per_frame):
	import cv2
	import numpy as np

	from pathlib import Path

	bits_per_ln = 96		# coded_bits_per_line (data payload, excluding calibration bits)
	nof_data_ln = 2			# number_of_data_lines
	nof_black_ln_bef = 2		# number_of_black_lines_before
	nof_black_ln_aft = 1		# number_of_black_lines_after
	nof_black_px_bef = 5		# number_of_black_pixels_before
	nof_black_px_aft = 3		# number_of_black_pixels_after
	y_dim = nof_black_ln_bef + 1 + nof_data_ln + nof_black_ln_aft 	# total lines in bit pattern,
																	# includes 1 calibration line
	x_dim = nof_black_px_bef + 2 + bits_per_ln + nof_black_px_aft 	# total pixels per bit pattern line,
																	# includes 2 calibration bits
																	# (note: 1px = 1bit at this stage of the process)

	vact_ref = 135.0		# make float, as target result must be float
	hact_ref = 240.0		# 
	vinc = vact_ref / ln_per_frame
	hinc = hact_ref / pix_per_ln

	# Settings consist of: frame_number | nof_frames | framerate | pix_per_ln | ln_per_frame
	# Each setting is followed by the number of bits used to encode it
	settings = [(frame_number, 24), (nof_frames, 24), (int(framerate*1000), 17), (pix_per_ln, 13), (ln_per_frame, 13)]
	ibp = np.zeros((y_dim, x_dim), dtype='uint8')

	bitinppat = np.zeros((bits_per_ln*nof_data_ln,), dtype='uint8')
	pnt = 0
	for x in settings:
		setting = x[0]
		for i in range(x[1]):
			bitinppat[pnt] = setting % 2
			pnt = pnt + 1 
			setting = setting >> 1

	ycur = nof_black_ln_bef
	xcur = nof_black_px_bef

	for i in range((bits_per_ln+2)):
		ibp[ycur, xcur + i] = 1-(i % 2) 	# calibration line

	for j in range(nof_data_ln): 			# calibration pixels per data line
		for i in range(2):
			ibp[ycur+1+j, xcur + i] = ((i+j) % 2)

	for j in range(nof_data_ln):
		for i in range(bits_per_ln):
			ibp[ycur+1+j, xcur+2+i] = bitinppat[j*bits_per_ln + i]

	xstart = 0
	xstop = int(x_dim/hinc)
	ystart = 0
	ystop = int(y_dim/vinc)

	i00 = np.zeros((ystop, xstop, 3), dtype='uint8')

	print(str(xstop)+"x"+str(ystop), end='', flush=True)

	for j in range(ystart, ystop): 			# ystart, ystop, xstart, xstop
		for i in range(xstart, xstop):
			ycur = int(j*vinc)
			xcur = int(i*hinc)
			i00[j, i, :] = ibp[ycur, xcur]*255.0

	status = cv2.imwrite(str(Path(str(bitpat_file_dir)+'\\'+str(frame_number).zfill(5)+'.png')), i00)
	print("| "+str(settings)+" | "+{True: 'saved', False: 'failed'}[status])
