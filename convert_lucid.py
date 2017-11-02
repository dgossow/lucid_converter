#!/usr/bin/python

import cv2
import os
import numpy as np
import math
from join import join_vr_image

# fx fy cx cy w
intrinsics = [
  [790.4084509398062, 789.27446607759, 1094.582267855196, 1102.24716498591, 1.059562527186768],
  [795.5514788612121, 795.0706495100468, 3251.816212680399, 1108.755968562144, 1.057656643682703]]

left_R_right = [ 
  [0.9999807, -0.0054444, 0.0029904],
  [0.0054263, 0.999967, 0.006035],
  [-0.0030231, -0.0060187, 0.9999773]]

def fov_project(intrinsics, xc, yc, zc):
  if zc < 1e-10:
    return -1, -1
  xu = xc/zc
  yu = yc/zc
  ru = np.sqrt(xu*xu + yu*yu)
  if ru > 7:
    return -1, -1
  rd_ru = 1.0
  if ru > 1.e-5:
    rd = 1.0 / intrinsics[4] * np.arctan(2 * ru * np.tan(intrinsics[4] / 2))
    rd_ru = rd/ru
  x = intrinsics[2] + intrinsics[0] * xu * rd_ru
  y = intrinsics[3] + intrinsics[1] * yu * rd_ru
  return x, y

def equirect_unproject(width, height, x, y):
  longit = x / float(width-1) * math.pi
  latit = (y - float(height-1) / 2) / float(height-1) * math.pi
  x = -1.0 * math.cos(latit) * math.cos(longit)
  y = math.sin(latit)
  z = math.cos(latit) * math.sin(longit)
  return x, y, z
  
def compute_remap(pano_size, intrinsics, R=None):
  map_x = np.zeros((pano_size, pano_size))
  map_y = np.zeros((pano_size, pano_size))

  for y in range(1, pano_size -1):
    for x in range(1, pano_size - 1):
      [xc, yc, zc] = equirect_unproject(pano_size, pano_size, x, y)
      if R != None:
          [xc, yc, zc] = np.matmul(left_R_right, [xc, yc, zc])
      [x_out, y_out] = fov_project(intrinsics, xc, yc, zc)
      map_x[y, x] = x_out
      map_y[y, x] = y_out

  map_x_32 = map_x.astype('float32')
  map_y_32 = map_y.astype('float32')
  return map_x_32, map_y_32

def render_equirect(image, map_x_32, map_y_32, out_file):
  image_equirect = cv2.remap(image, map_x_32, map_y_32, cv2.INTER_CUBIC | cv2.BORDER_CONSTANT)
  cv2.imwrite(out_file, image_equirect)

out_path = "lucid_cardboard/"
split_out_path = "lucid_split/"
in_path = "lucid/"
pano_size = 2160

if not os.path.isdir(out_path):
  os.mkdir(out_path)
if not os.path.isdir(split_out_path):
  os.mkdir(split_out_path)

print "Computing warp map"
maps = [
  compute_remap(pano_size, intrinsics[0], R = left_R_right),
  compute_remap(pano_size, intrinsics[1])]

for filename in os.listdir(in_path):
  in_file = os.path.join(in_path, filename)
  if not in_file.endswith(".jpg"):
    continue
  print "Processing", in_file
  orig_img = cv2.imread(in_file)
  file_basename = os.path.splitext(os.path.basename(in_file))[0]
  left_img_name = split_out_path + file_basename + "_left.jpg"
  right_img_name = split_out_path + file_basename + "_right.jpg"
  render_equirect(orig_img, maps[0][0], maps[0][1], left_img_name)
  render_equirect(orig_img, maps[1][0], maps[1][1], right_img_name)
  
  join_vr_image(left_img_name, right_img_name,
                output_filepath=out_path + file_basename + ".cardboard.jpg",
                CroppedAreaLeftPixels = pano_size / 2, CroppedAreaTopPixels=0,
                CroppedAreaImageWidthPixels=pano_size,
                CroppedAreaImageHeightPixels=pano_size,
                FullPanoWidthPixels=pano_size * 2,
                FullPanoHeightPixels=pano_size)

#os.remove("left_tmp.jpg")
#os.remove("right_tmp.jpg")

