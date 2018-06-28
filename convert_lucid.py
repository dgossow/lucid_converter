#!/usr/bin/python

import cv2
import os
import numpy as np
import math
from join import join_vr_image
import pickle
import shutil
from PIL import Image
from PIL.ExifTags import TAGS
from subprocess import call

f = 840 # 848

# from FOV calibration
left_R_right = [ 
  [0.9999807, -0.0054444, 0.0029904],
  [0.0054263, 0.999967, 0.006035],
  [-0.0030231, -0.0060187, 0.9999773]]

# fov: 1094, 1002
cx_left = 1084
cy_left = 1102 # 1102

# fov: 3251, 1108
cx_right = 3282
cy_right = 1108 #1108

left_camera_matrix = [[f, 0., cx_left],
  [0., f, cy_left],
  [0., 0., 1.]]
#left_dist_coeffs = [-0.0865861923, 0., 0., 0.]
left_dist_coeffs = [-0.0888, 0., 0., 0.]

right_camera_matrix = [[f, 0.,  cx_right], 
  [0., f, cy_right],
  [0., 0., 1.]]
right_dist_coeffs = [-0.087, 0., 0., 0.]
#right_dist_coeffs = [-0.088, 0., 0., 0.]

def cv_project(camera_matrix, dist_coeffs, xc, yc, zc):
  object_points = np.float32([[xc,yc,zc]]).reshape(-1,3)
  camera_matrix = np.float32(camera_matrix).reshape(3,3)
  dist_coeffs = np.float32(dist_coeffs).reshape(1,4)
  rvec = np.zeros(3).reshape(1, 1, 3)
  tvec = np.zeros(3).reshape(1, 1, 3)
  if object_points.ndim == 2:
    object_points = np.expand_dims(object_points, 0)
  image_points = cv2.fisheye.projectPoints(object_points, rvec, tvec, camera_matrix, dist_coeffs)
  #print object_points[0], image_points[0][0][0]
  return image_points[0][0][0]

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
  
def compute_remap(pano_size, camera_matrix, dist_coeffs, R=None):
  map_x = np.zeros((pano_size, pano_size))
  map_y = np.zeros((pano_size, pano_size))

  for y in range(0, pano_size):
    for x in range(0, pano_size):
      [xc, yc, zc] = equirect_unproject(pano_size, pano_size, x, y)
      if R != None:
          [xc, yc, zc] = np.matmul(left_R_right, [xc, yc, zc])
      if (zc < 0.0001):
        zc = 0.0001
      [x_out, y_out] = cv_project(camera_matrix, dist_coeffs, xc, yc, zc)
      map_x[y, x] = x_out
      map_y[y, x] = y_out

  map_x_32 = map_x.astype('float32')
  map_y_32 = map_y.astype('float32')
  return map_x_32, map_y_32

def render_equirect(image, map_x_32, map_y_32, out_file):
  image_equirect = cv2.remap(image, map_x_32, map_y_32, cv2.INTER_CUBIC | cv2.BORDER_CONSTANT)
  cv2.imwrite(out_file, image_equirect, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
  return image_equirect

out_path = "lucid_cardboard/"
split_out_path = "lucid_split/"
in_path = "lucid/"
pano_size = 2200

if not os.path.isdir(out_path):
  os.mkdir(out_path)
if not os.path.isdir(split_out_path):
  os.mkdir(split_out_path)


if (os.path.isfile("lucid_maps")):
  print "Loading warp map from disk."
  input_file = open("lucid_maps", "rb")
  maps = pickle.load(input_file)
else:
  print "Computing warp map"
  maps = [
    compute_remap(pano_size, left_camera_matrix, left_dist_coeffs, R=left_R_right),
    compute_remap(pano_size, right_camera_matrix, right_dist_coeffs)]
  output = open('lucid_maps', 'wb')
  pickle.dump(maps, output)

for filename in sorted(os.listdir(in_path)):
  in_file = os.path.join(in_path, filename)
  if not in_file.endswith(".jpg"):
    continue
  print "Processing", in_file
  orig_img = cv2.imread(in_file)
  file_basename = os.path.splitext(os.path.basename(in_file))[0]
  left_img_name = split_out_path + file_basename + "_left.jpg"
  right_img_name = split_out_path + file_basename + "_right.jpg"
  
  img_left = render_equirect(orig_img, maps[0][0], maps[0][1], left_img_name)
  img_right = render_equirect(orig_img, maps[1][0], maps[1][1], right_img_name)
  cv2.imwrite(split_out_path + file_basename + "_combined.jpg",
              0.5 * img_left + 0.5 * img_right)

  cv2.circle(orig_img, (cx_left, cy_left), 1050, (0, 0, 0), 5)
  cv2.circle(orig_img, (cx_left, cy_left), 1050, (255, 255, 255), 2)
  cv2.circle(orig_img, (cx_right, cy_right), 1050, (0, 0, 0), 5)
  cv2.circle(orig_img, (cx_right, cy_right), 1050, (255, 255, 255), 2)
  cv2.imwrite(split_out_path + file_basename + "_debug.jpg", orig_img)

  # copy EXIF
  img_in = Image.open(in_file)
  img_out = Image.open(left_img_name)
  img_out.save(left_img_name, "jpeg", exif=img_in.info['exif'])
  
  output_filepath=out_path + file_basename + ".cardboard.jpg"
  join_vr_image(left_img_name, right_img_name,
                output_filepath=output_filepath,
                CroppedAreaLeftPixels = pano_size / 2, CroppedAreaTopPixels=0,
                CroppedAreaImageWidthPixels=pano_size,
                CroppedAreaImageHeightPixels=pano_size,
                FullPanoWidthPixels=pano_size * 2,
                FullPanoHeightPixels=pano_size)

  # hack to transfer created-by date
  #call(["cp", "-p", in_file, output_filepath])
  #with open(output_filepath, 'wb+') as output, open('tmpfile.jpg', 'rb') as input:
  #  while True:
  #      data = input.read(100000)
  #      if data == '':  # end of file reached
  #          break
  #      output.write(data)

  # copy EXIF
  #img_in = Image.open(in_file)
  #img_out = Image.open(output_filepath)
  #img_out.save(output_filepath, "jpeg", exif=img_in.info['exif'])


#os.remove("left_tmp.jpg")
#os.remove("right_tmp.jpg")

