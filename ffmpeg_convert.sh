ffmpeg \
'-framerate' '45' \
'-y' \
'-i' 'baby_rect/%d.png' \
'-vcodec' 'mpeg4' '-b:v' '12000k' \
'-qscale:v' '2' \
'-strict' \
'experimental' \
'baby_rect.mp4' \
'-threads' '0'