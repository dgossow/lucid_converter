import os
from shutil import copyfile

in_path = 'baby_rect'
last_img = ''

for i in range(1,2783) :
  path = os.path.join(in_path, str(i) + '.png')
  if os.path.isfile(path):
    last_img = path
  else:
    print "copy", last_img, path
    copyfile(last_img, path)
