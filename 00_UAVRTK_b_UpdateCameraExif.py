# -*- coding: utf-8 -*-
# June 2019
# AD
# This code aims at updating the EXIF info of the JPEG files based on a CSV file containing the updated position
# of the camera. It will create a copy of the pictures in a folder renamed with "PICTURE-FOLDER_UpdatedGPS"
# Part of the exif handling with Pillow comes from https://www.sylvaindurand.org/gps-data-from-photos-with-python/
# V.1.0

import os, shutil, sys
import piexif
import pandas as pd
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.ExifTags import GPSTAGS

# -----------------------------
# Variables [--> to adapt accordingly]
PictureFolder=r"C:\Users\adille\Desktop\Tests\Test_UAV_RTK\Flight2" # Floder with pictures
# CSV with 4 columns : 1) PhotoName.jpg 2) Latitude 3) Longitude 4) Elevation
CSVwithLocations=r"C:\Users\adille\Desktop\Tests\Test_UAV_RTK\Flight2\Test_UAV-RTK_RMCA_Flight2_UpdatedPos.csv"
# -----------------------------


# -----------------------------
# A. Create a copy of cameras
# -----------------------------
# Create a new folder were original pictures are copied and exif geotagging updated
count=0
path=os.path.split(PictureFolder)
PictureFolder_Updated=path[0] + "\\" + path[1] + "_UpdatedGPS"
if not os.path.exists(PictureFolder_Updated):
    os.mkdir(PictureFolder_Updated)
    print("\nA directory " , PictureFolder_Updated ,  " has been created ")
    src_files = os.listdir(PictureFolder)

    # Copy all images in the new folder
    for file_name in src_files:
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.tif')):
                full_file_name = os.path.join(PictureFolder, file_name)
                if os.path.isfile(full_file_name):
                    shutil.copy(full_file_name, PictureFolder_Updated)
                    count = count+1
    print(str(count) + ' images have been copied to the folder')
else:
    print("\nThe directory " , PictureFolder_Updated ,  " already exists, no images have been copied")
    sys.exit()


# -----------------------------
# B. Some functions
# -----------------------------

# Read EXIF GPS Data
def get_exif(filename):
    image = Image.open(filename)
    image.verify()
    return image._getexif()

# Get label for EXIF metadata
def get_labeled_exif(exif):
    labeled = {}
    for (key, val) in exif.items():
        labeled[TAGS.get(key)] = val
    return labeled

# Get EXIF GPS metadata
def get_geotagging(exif):
    if not exif:
        raise ValueError("No EXIF metadata found")
    geotagging = {}
    for (idx, tag) in TAGS.items():
        if tag == 'GPSInfo':
            if idx not in exif:
                raise ValueError("No EXIF geotagging found")

            for (key, val) in GPSTAGS.items():
                if key in exif[idx]:
                    geotagging[val] = exif[idx][key]

    return geotagging

#Transform EXIF locations to DD coordinates
def get_decimal_coordinates(info):
    for key in ['Latitude', 'Longitude']:
        if 'GPS'+key in info and 'GPS'+key+'Ref' in info:
            e = info['GPS'+key]
            ref = info['GPS'+key+'Ref']
            info[key] = ( e[0][0]/e[0][1] +
                          e[1][0]/e[1][1] / 60 +
                          e[2][0]/e[2][1] / 3600
                        ) * (-1 if ref in ['S','W'] else 1)

    for a in ['Altitude']:
        if 'GPS'+ 'Altitude' in info :
            b=info['GPS'+a]
            info[a]=b[0]/b[1]

    if 'Latitude' in info and 'Longitude' in info and 'Altitude' in info:
        return [info['Latitude'], info['Longitude'], info['Altitude']]

#Transform DD to DMS coordinates
def decdeg2dms(dd):
   is_positive = dd >= 0
   dd = abs(dd)
   minutes,seconds = divmod(dd*3600,60)
   degrees,minutes = divmod(minutes,60)
   degrees = degrees if is_positive else -degrees
   # return (degrees,minutes,seconds)
   return ((int(degrees*1000), 1000), (int(minutes*1000), 1000), (int(seconds*1000000), 1000000))



# -----------------------------
# C. Read New GPS Data from CSV
# -----------------------------
df= pd.read_csv(CSVwithLocations, sep=",", index_col=0)

# -----------------------------
# D. Modify EXIF data according to CSV values
# -----------------------------

for image in os.listdir(PictureFolder_Updated):
    filepath = os.path.join(PictureFolder_Updated, image)

    # Coordinates before Update
    exif = get_exif(filepath)
    if exif is not None:
        geotags = get_geotagging(exif)  # GPS tags
        LatLonAlt = get_decimal_coordinates(geotags)
        print('\n' + image)
        print('Original coordinates' + ' ' + str(LatLonAlt))

    # Check the coordinates from CSV
    lat0 = df.loc[image][0]
    lon0 = df.loc[image][1]
    alt0 = df.loc[image][2]
    print('New coordinates from CSV ' + ' ' + str(lat0) + ' ' + str(lon0) + ' ' + str(alt0))

    # Modify to EXIF GPS Tags form
    lat = decdeg2dms(lat0)
    lon = decdeg2dms(lon0)
    alt=(int(alt0*1000000),1000000)

    # Implement the updated positions in the images EXIF
    img = Image.open(filepath)
    exif_dict = piexif.load(img.info['exif'])
    exif_dict['GPS'][piexif.GPSIFD.GPSLatitude] = lat
    exif_dict['GPS'][piexif.GPSIFD.GPSLongitude] = lon
    exif_dict['GPS'][piexif.GPSIFD.GPSAltitude] = alt
    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, filepath)

    # Check the coordinates after Update on the camera
    exif2 = get_exif(filepath)
    if exif2 is not None:
        geotags2 = get_geotagging(exif2)  # GPS tags
        LatLonAlt2 = get_decimal_coordinates(geotags2)
        print('Updated coordinates' + ' ' + str(LatLonAlt2))
