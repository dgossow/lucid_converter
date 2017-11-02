#!/usr/bin/python

import os
import shutil
import tempfile
from datetime import datetime
from os import path
import base64
from collections import OrderedDict

from PIL import Image  # from Pillow package
import xxhash
from libxmp import XMPFiles, XMPMeta, XMPError
from libxmp.consts import XMP_NS_TIFF

XMP_NS_GPHOTOS_IMAGE = u'http://ns.google.com/photos/1.0/image/'
XMP_NS_GPHOTOS_AUDIO = u'http://ns.google.com/photos/1.0/audio/'
XMP_NS_GPHOTOS_PANORAMA = u'http://ns.google.com/photos/1.0/panorama/'

GPANO_PROPERTIES = [
    u'CroppedAreaLeftPixels',
    u'CroppedAreaTopPixels',
    u'CroppedAreaImageWidthPixels',
    u'CroppedAreaImageHeightPixels',
    u'FullPanoWidthPixels',
    u'FullPanoHeightPixels',
    u'InitialViewHeadingDegrees',
]

def get_image_dimensions(img_filepath):
    image = Image.open(img_filepath)
    size = image.size
    image.close()
    return size

def join_vr_image(left_img_filename, right_img_filename, audio_filename=None, output_filepath=None,
                  CroppedAreaLeftPixels=None,
                  CroppedAreaTopPixels=None,
                  CroppedAreaImageWidthPixels=None,
                  CroppedAreaImageHeightPixels=None,
                  FullPanoWidthPixels=None,
                  FullPanoHeightPixels=None,
                  InitialViewHeadingDegrees=None):

    tmp_vr_filename = next(tempfile._get_candidate_names())
    shutil.copy(left_img_filename, tmp_vr_filename)

    width, height = get_image_dimensions(tmp_vr_filename)

    if CroppedAreaLeftPixels is None:
        CroppedAreaLeftPixels = 0
    if CroppedAreaTopPixels is None:
        CroppedAreaTopPixels = height
    if CroppedAreaImageWidthPixels is None:
        CroppedAreaImageWidthPixels = width
    if CroppedAreaImageHeightPixels is None:
        CroppedAreaImageHeightPixels = height
    if FullPanoWidthPixels is None:
        FullPanoWidthPixels = width
    if FullPanoHeightPixels is None:
        FullPanoHeightPixels = int(width/2.0)
    if InitialViewHeadingDegrees is None:
        InitialViewHeadingDegrees = 180

    xmpfile = XMPFiles(file_path=tmp_vr_filename, open_forupdate=True)
    xmp = xmpfile.get_xmp()
    xmp.register_namespace(XMP_NS_GPHOTOS_PANORAMA, 'GPano')
    xmp.register_namespace(XMP_NS_GPHOTOS_IMAGE, 'GImage')
    xmp.register_namespace(XMP_NS_GPHOTOS_AUDIO, 'GAudio')
    xmp.register_namespace(XMP_NS_TIFF, 'tiff')

    xmp.set_property(XMP_NS_GPHOTOS_IMAGE,
                    'GImage:Mime', 'image/jpeg')
    xmp.set_property(XMP_NS_GPHOTOS_PANORAMA,
                    'GPano:ProjectionType', 'equirectangular')
    xmp.set_property(XMP_NS_GPHOTOS_PANORAMA,
                    'GPano:CroppedAreaLeftPixels', str(CroppedAreaLeftPixels))
    xmp.set_property(XMP_NS_GPHOTOS_PANORAMA,
                    'GPano:CroppedAreaTopPixels', str(CroppedAreaTopPixels))
    xmp.set_property(XMP_NS_GPHOTOS_PANORAMA,
                    'GPano:CroppedAreaImageWidthPixels',
                    str(CroppedAreaImageWidthPixels))
    xmp.set_property(XMP_NS_GPHOTOS_PANORAMA,
                    'GPano:CroppedAreaImageHeightPixels',
                    str(CroppedAreaImageHeightPixels))
    xmp.set_property(XMP_NS_GPHOTOS_PANORAMA,
                    'GPano:FullPanoWidthPixels',
                    str(FullPanoWidthPixels))
    xmp.set_property(XMP_NS_GPHOTOS_PANORAMA,
                    'GPano:FullPanoHeightPixels',
                    str(FullPanoHeightPixels))
    xmp.set_property(XMP_NS_GPHOTOS_PANORAMA,
                    'GPano:InitialViewHeadingDegrees',
                    str(InitialViewHeadingDegrees))

    left_img_b64 = None
    with open(left_img_filename, 'rb') as fh:
        left_img_data = fh.read()
    left_img_b64 = base64.b64encode(left_img_data)
    xmp.set_property(XMP_NS_GPHOTOS_IMAGE, u'GImage:Mime', 'image/jpeg')
    xmp.set_property(XMP_NS_GPHOTOS_IMAGE, u'GImage:Data', left_img_b64.decode('utf-8'))
    del left_img_b64
    # gc.collect()

    right_img_b64 = None
    with open(right_img_filename, 'rb') as fh:
        right_img_data = fh.read()
    right_img_b64 = base64.b64encode(right_img_data)
    xmp.set_property(XMP_NS_GPHOTOS_IMAGE, u'GImage:Mime', 'image/jpeg')
    xmp.set_property(XMP_NS_GPHOTOS_IMAGE, u'GImage:Data', right_img_b64.decode('utf-8'))
    del right_img_b64
    # gc.collect()

    if audio_filename is not None:
        audio_b64 = None
        with open(audio_filename, 'rb') as fh:
            audio_data = fh.read()
        audio_b64 = base64.b64encode(audio_data)
        xmp.set_property(XMP_NS_GPHOTOS_AUDIO, u'GAudio:Mime', 'audio/mp4a-latm')
        xmp.set_property(XMP_NS_GPHOTOS_AUDIO, u'GAudio:Data', audio_b64.decode('utf-8'))
        del audio_b64
        # gc.collect()

    if xmpfile.can_put_xmp(xmp):
        xmpfile.put_xmp(xmp)
    xmpfile.close_file()

    if output_filepath is None:
        vr_filepath = path.join(upload_dir(), '%s.vr.jpg' % get_hash_id(tmp_vr_filename))
    else:
        vr_filepath = output_filepath

    shutil.move(tmp_vr_filename, vr_filepath)

    return vr_filepath

#join_vr_image("left_equirect.jpg", "right_equirect.jpg",
#              output_filepath="DDtZUx5RXwL.vr_600x600_85.jpg",
#              CroppedAreaLeftPixels = 320, CroppedAreaTopPixels=0,
#              CroppedAreaImageWidthPixels=1280,
#              CroppedAreaImageHeightPixels=1280,
#              FullPanoWidthPixels=2560,
#              FullPanoHeightPixels=1280,
#              InitialViewHeadingDegrees=0)

