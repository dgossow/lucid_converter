#!/usr/bin/python

import cv2
import os
import numpy as np
import math

import quaternions
import join

# fx fy cx cy w
intrinsics = [
  [384.4186, 382.2022, 1279.0 - 655.2742, 959.0 - 508.9167, 0.9550048],
  [383.6429, 381.5082, 1279.0 - 655.4424, 959.0 - 486.0166, 0.9527258]]
# p_A = RotationMatrix(A_q_B) * p_B
#A_q_B = quaternions.Quaternion(0.9999906364066803, 0.003013466268845641, -0.001503382640239678, -0.002717712392139117)
A_q_B = quaternions.Quaternion.from_euler([0, 0.0, 0])
identity_quat = quaternions.Quaternion(1, 0, 0, 0)
#A_q_B = identity_quat
#print A_q_B.get_rotation_matrix()
#print np.array(A_q_B.get_rotation_matrix()).dot(np.array([0, 0, 1]))
#exit()

def fov_project(intrinsics, xu, yu):
  ru = np.sqrt(xu*xu + yu*yu)
  rd_ru = 1.0
  if ru > 1.e-5:
    rd = 1.0 / intrinsics[4] * np.arctan(2 * ru * np.tan(intrinsics[4] / 2))
    rd_ru = rd/ru
  x = intrinsics[2] + intrinsics[0] * xu * rd_ru
  y = intrinsics[3] + intrinsics[1] * yu * rd_ru
  if y < 2:
    y = -1
  if y > height - 3:
    y = -1
  return x, y

def equirect_unproject(width, height, x, y):
  longit = x / float(width-1) * math.pi
  latit = (y - float(height-1) / 2) / float(height-1) * math.pi
  xp = -1.0 * math.cos(latit) * math.cos(longit)
  yp = math.sin(latit)
  zp = math.cos(latit) * math.sin(longit) + 1e-15
  return xp, yp, zp

def make_mask(mask_size, border):
  mask = np.zeros((mask_size[0], mask_size[1], 3))
  border = float(border)
  
  for y in range(0, mask_size[0] -1):
    for x in range(0, mask_size[1] - 1):
      alpha = 1
      if x < border:
        alpha = x / border
      if x > mask_size[1] - border - 1:
        alpha = (mask_size[1] - x - 1) / border
      if y < border:
        alpha = y / border
      if y > mask_size[0] - border - 1:
        alpha = (mask_size[0] - y - 1) / border
      mask[y, x, :] = alpha
  return mask

def fisheye_to_equirect(image_size, pano_size, intrinsics, q):

  map_x = np.zeros((pano_size, pano_size))
  map_y = np.zeros((pano_size, pano_size))
  
  R = np.array(q.get_rotation_matrix())
  
  for y in range(1, pano_size -1):
    for x in range(1, pano_size - 1):
      # unproject to 3d
      [xu, yu, zu] = equirect_unproject(pano_size, pano_size, x, y)
      # rotate
      p3d_rot = R.dot(np.array([xu, yu, zu]))
      #normalize
      x_norm = p3d_rot[0] / p3d_rot[2]
      y_norm = p3d_rot[1] / p3d_rot[2]
      # re-project
      [x_out, y_out] = fov_project(intrinsics, x_norm, y_norm)
      map_x[y, x] = x_out
      map_y[y, x] = y_out

  map_x_32 = map_x.astype('float32')
  map_y_32 = map_y.astype('float32')
  return map_x_32, map_y_32

orig_img = cv2.imread("0.jpg")

width = orig_img.shape[0]
height = orig_img.shape[1] / 2
pano_size = 1280#1600#2048#max(width, height)
image_size = [height, width]

out_path = "baby_rect/"
in_path = "baby/"

print "computing rectification maps..."
[map_left_x, map_left_y] = fisheye_to_equirect(image_size, pano_size, intrinsics[0], identity_quat)
[map_right_x, map_right_y] = fisheye_to_equirect(image_size, pano_size, intrinsics[1], A_q_B)

print "computing masks..."
fisheye_mask = make_mask(image_size, image_size[0] / 100.0)
equirect_mask = make_mask([pano_size, pano_size], pano_size / 100.0)
mask_left = cv2.remap(fisheye_mask, map_left_x, map_left_y, cv2.INTER_CUBIC | cv2.BORDER_CONSTANT)
mask_right = cv2.remap(fisheye_mask, map_right_x, map_right_y, cv2.INTER_CUBIC | cv2.BORDER_CONSTANT)
mask = equirect_mask * mask_left * mask_right

# maps for extracting left/right from original
map_x = np.array([np.arange(height)]).repeat(width, axis=0).transpose()
map_y = np.array([width - 1 - np.arange(width)]).repeat(height, axis=0)
map_x_32 = map_x.astype('float32')
map_y_32 = map_y.astype('float32')

print "rectifying images..."
if not os.path.isdir(out_path):
  os.mkdir(out_path)

for filename in os.listdir(in_path):
  in_file = os.path.join(in_path, filename)
  if not in_file.endswith(".jpg"):
    continue
  print "Processing", in_file
  orig_img = cv2.imread(in_file)
  file_basename = os.path.splitext(os.path.basename(in_file))[0]
  
  #extract left and right image.
  left_img = cv2.remap(orig_img, map_x_32, map_y_32, cv2.INTER_NEAREST)
  right_img = cv2.remap(orig_img, map_x_32 + height, map_y_32, cv2.INTER_NEAREST)
  #cv2.imwrite("left.png", left_img)
  #cv2.imwrite("right.png", right_img)

  left_img_equirect = cv2.remap(left_img, map_left_x, map_left_y, cv2.INTER_CUBIC | cv2.BORDER_CONSTANT)
  left_img_equirect = left_img_equirect * mask
  #cv2.imwrite("left_equirect.jpg", left_img_equirect)

  right_img_equirect = cv2.remap(right_img, map_right_x, map_right_y, cv2.INTER_CUBIC | cv2.BORDER_CONSTANT)
  right_img_equirect = right_img_equirect * mask
  #cv2.imwrite("right_equirect.jpg", right_img_equirect)

  mixed_img_equirect = 0.5 * left_img_equirect + 0.5 * right_img_equirect
  #cv2.imwrite("mixed_equirect.jpg", mixed_img_equirect)

  output_filepath=out_path + file_basename + ".png"
  output_image = np.zeros((pano_size, pano_size * 2, 3))
  output_image[:, 0:pano_size, :] = left_img_equirect
  output_image[:, pano_size:pano_size*2, :] = right_img_equirect
  cv2.imwrite(output_filepath, output_image)
