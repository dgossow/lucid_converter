import os
import shutil

for filename in os.listdir("lucid_cardboard_failed"):
  if not filename.endswith(".jpg"):
    continue
  fn_trunk = filename[0:9]
  in_file = os.path.join("lucid_complete", fn_trunk + ".jpg")
  out_file = os.path.join("lucid", fn_trunk + ".jpg")
  print "Copy ", in_file, out_file
  shutil.copy(in_file, out_file)
