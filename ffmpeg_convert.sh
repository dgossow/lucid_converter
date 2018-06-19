ffmpeg \
'-framerate' '45' \
'-y' \
'-i' 'baby_rect_2k/%d.png' \
'-i' 'baby.m4a' \
'-vcodec' 'mpeg4' \
'-qscale:v' '2' \
'baby_rect_2k.mp4' \
'-threads' '0'