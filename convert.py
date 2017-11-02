#!/usr/bin/python

import cv2
import numpy as np
import math

import controllers.main

# fx fy cx cy w
intrinsics = [
  [384.4186, 382.2022, 655.2742, 508.9167, 0.9550048],
  [383.6429, 381.5082, 655.4424, 486.0166, 0.9527258]]

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
  x = -1.0 * math.cos(latit) * math.cos(longit)
  y = math.sin(latit)
  z = math.cos(latit) * math.sin(longit) + 1e-15
  return x/z, y/z

def render_equirect(image, pano_size, intrinsics):
  map_x = np.zeros((pano_size, pano_size))
  map_y = np.zeros((pano_size, pano_size))

  for y in range(1, pano_size -1):
    for x in range(1, pano_size - 1):
      [x_norm, y_norm] = equirect_unproject(pano_size, pano_size, x, y)
      [x_out, y_out] = fov_project(intrinsics, x_norm, y_norm)
      map_x[y, x] = x_out
      map_y[y, x] = y_out

  map_x_32 = map_x.astype('float32')
  map_y_32 = map_y.astype('float32')
  image_equirect = cv2.remap(image, map_x_32, map_y_32, cv2.INTER_CUBIC | cv2.BORDER_CONSTANT)
  return image_equirect

orig_img = cv2.imread("0.jpg")

width = orig_img.shape[0]
height = orig_img.shape[1] / 2

#extract left and right image.
map_x = np.array([np.arange(height)]).repeat(width, axis=0).transpose()
map_y = np.array([width - 1 - np.arange(width)]).repeat(height, axis=0)
map_x_32 = map_x.astype('float32')
map_y_32 = map_y.astype('float32')

left_img = cv2.remap(orig_img, map_x_32, map_y_32, cv2.INTER_NEAREST)
right_img = cv2.remap(orig_img, map_x_32 + height, map_y_32, cv2.INTER_NEAREST)
cv2.imwrite("left.png", left_img)
cv2.imwrite("right.png", right_img)

pano_size = max(width, height)

left_img_equirect = render_equirect(left_img, pano_size, intrinsics[0])
cv2.imwrite("left_equirect.jpg", left_img_equirect)
right_img_equirect = render_equirect(right_img, pano_size, intrinsics[1])
cv2.imwrite("right_equirect.jpg", right_img_equirect)

