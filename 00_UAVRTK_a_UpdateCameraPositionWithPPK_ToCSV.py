# -*- coding: utf-8 -*-
# June 2019
# AD
# This code aims at updating the position of the camera of Phantom 4 RTK based on RINEX flight info (PPK processing)
# It requires a .pos file (output of RTKLIB after processing) and a .MRK file containing timestamps of acqusitions as
# well as the pictures (for naming purpose)
# V.1.0


import os
import pandas as pd
import numpy as np
from astropy.time import Time
from math import cos, radians

pd.options.mode.chained_assignment = None  # default='warn'

# -----------------------------
# Variables [--> to adapt accordingly]
PictureFolder=r"C:\Users\adille\Desktop\Tests\Test_UAV_RTK\Flight2" # Folder with pictures
POSFile=r"C:\Users\adille\Desktop\Tests\Test_UAV_RTK\Flight2\100_0011_Rinex-V2.pos" # RTKLIB output .pos file
MRKFile=r"C:\Users\adille\Desktop\Tests\Test_UAV_RTK\Flight2\100_0011_Timestamp.MRK" # DJI output .MRK file
# provide path and name of output CSV file with New camera locations
OutputCSVFile=r"C:\Users\adille\Desktop\Tests\Test_UAV_RTK\Flight2\Test_UAV-RTK_RMCA_Flight2_UpdatedPos.csv"
# -----------------------------


# -----------------------------
# A. Read New GPS Data from CSV
# -----------------------------
cols_pos = ['GPST_Date','GPST_Local','latitude','longitude', 'height','Q', 'ns', 'sdn(m)', 'sde(m)', 'sdu(m)',
            'sdne(m)',  'sdeu(m)',  'sdun(m)', 'age(s)',  'ratio'] # create some col names
df_pos= pd.read_csv(POSFile, index_col=False, delim_whitespace=True,names=cols_pos,skiprows=range(0,25),engine="python")
cols_mrk = ['GPST_Time','GPST_week', 'PhaseCompNS','NS', 'PhaseCompEW','EW','PhaseCompV','V','latitude','lat',
            'longitude','lon', 'height','hgt','a','b','c','d','e','f','g'] # create some col names
df_mrk= pd.read_csv(MRKFile,index_col=0, sep = "\s+|\t+|\s+\t+|\t+\s+|,", engine='python',names=cols_mrk)
df_mrk=df_mrk.drop(columns=['NS','EW','V','lat','lon','hgt','a','b','c','d','e','f','g'])

# -----------------------------
# B. GPS Time / Local Time
# -----------------------------

# a. From GPS to Local Time
def GPSTime2Local(time):
    timeLocal0 = []
    for i in range(len(time)):
        tgps0= time[i]
        tgps=tgps0-19 # Added correction
        t = Time(tgps, format='gps',precision=3)
        t = Time(t, format='iso',precision=3)
        t = t.strftime("%H:%M:%S")
        timeLocal0.append(t)
        # print(str(tgps) + ' --> ' + str(t))
    return timeLocal0

timeGPS=df_mrk['GPST_Time'].values
timeLocal=GPSTime2Local(timeGPS)
df_mrk.insert(2,'GPST_Local',timeLocal)

# b. From iso to GPS
def Local2GPSTime(time):
    timeGPS0 = []
    for i in range(len(time)):
        tiso0= time[i]
        tiso='1980-01-08 '+ tiso0 #if GPS week not included --> start at 1980-01-08
        t = Time(tiso, format='iso',precision=4)
        t = Time(t, format='gps',precision=4)
        # print(str(tiso) + ' --> ' + str(t))
        timeGPS0.append(t)
    return timeGPS0
timeLocal=df_pos['GPST_Local'].values
timeGPS=Local2GPSTime(timeLocal)
df_pos.insert(2,'GPST_Time',timeGPS)


# -----------------------------
# C. Search for closest GPS point to Photo
# -----------------------------
print('\nSearch for closest GPS point to photo')
print("Photo #" + ' --> ' + " ID closest " + ' | ' " ID 2nd closest " )

df_mrk['GPST_Time']=Time(df_mrk['GPST_Time'],scale='utc', format='gps') # from float64 to Time Object
df_mrk.insert(3,'ClosestID',0)
df_mrk.insert(4,'ClosestTimeStamps',0.0)
df_mrk.insert(5,'ClosestLat',0.0)
df_mrk.insert(6,'ClosestLon',0.0)
df_mrk.insert(7,'ClosestHgt',0.0)

df_mrk.insert(8,'SndClosestID',0)
df_mrk.insert(9,'SndClosestTimeStamps',0.0)
df_mrk.insert(10,'SndClosestLat',0.0)
df_mrk.insert(11,'SndClosestLon',0.0)
df_mrk.insert(12,'SndClosestHgt',0.0)

# Search nearest time between Photo and GPS measures
def nearest_ind(items, pivot):
    time_diff = np.abs([date - pivot for date in items])
    return time_diff.argmin(0)


for i in range(1, (len(df_mrk['GPST_Time'])+1)):

    # a) Closest
    first = nearest_ind(df_pos['GPST_Time'], df_mrk['GPST_Time'][i])
    df_mrk['ClosestID'][i]=first
    df_mrk['ClosestTimeStamps'][i] = df_pos['GPST_Time'][first]
    df_mrk['ClosestLat'][i] = df_pos['latitude'][first]
    df_mrk['ClosestLon'][i] = df_pos['longitude'][first]
    df_mrk['ClosestHgt'][i] = df_pos['height'][first]

    # b) Second closest
    dta = df_pos['GPST_Time'][first - 1] - df_mrk['GPST_Time'][i]
    dtb = df_pos['GPST_Time'][first + 1] - df_mrk['GPST_Time'][i]
    dt = (abs(dta), abs(dtb))
    second0 = dt.index(min(dt)) # index of second closest
    if second0 == 0:
        second=first - 1
    elif second0 == 1:
        second = first + 1
    df_mrk['SndClosestID'][i] = second
    df_mrk['SndClosestTimeStamps'][i] = df_pos['GPST_Time'][second]
    df_mrk['SndClosestLat'][i] = df_pos['latitude'][second]
    df_mrk['SndClosestLon'][i] = df_pos['longitude'][second]
    df_mrk['SndClosestHgt'][i] = df_pos['height'][second]

    # Print
    print(str(i) + ' --> ' + str(first) + ' | '+ str(second))



# -----------------------------
# D. Position calculation
# -----------------------------
print('\nCalculate corrected photo positions')

# Create some new cols
df_mrk.insert(13,'TS_Diff',0.0)
df_mrk.insert(14,'InterpLat',0.0)
df_mrk.insert(15,'InterpLon',0.0)
df_mrk.insert(16,'InterpHgt',0.0)
df_mrk.insert(17,'PhaseCompNS_deg',0.0)
df_mrk.insert(18,'PhaseCompEW_deg',0.0)
df_mrk.insert(19,'PhaseCompV_m',0.0)
df_mrk.insert(20,'UpdatedLat',0.0)
df_mrk.insert(21,'UpdatedLon',0.0)
df_mrk.insert(22,'UpdatedHgt',0.0)

# 1 degree of Longitude = cosine (latitude in decimal degrees) * length of degree at equator (111.321 km)
degLon = cos(radians(df_mrk['latitude'][1])) * 111.321

for i in range(1, (len(df_mrk['GPST_Time'])+1)):
    df_mrk['TS_Diff'][i] = (df_mrk['GPST_Time'][i] - df_mrk['ClosestTimeStamps'][i]) / \
                           ( df_mrk['SndClosestTimeStamps'][i] - df_mrk['ClosestTimeStamps'][i])

    # Interpolation of position between the two closest points (in function of timing)
    df_mrk['InterpLat'][i] = (df_mrk['ClosestLat'][i] * (1 - df_mrk['TS_Diff'][i])) + \
                             ( df_mrk['SndClosestLat'][i] * df_mrk['TS_Diff'][i])
    df_mrk['InterpLon'][i] = (df_mrk['ClosestLon'][i] * (1 - df_mrk['TS_Diff'][i])) + \
                             ( df_mrk['SndClosestLon'][i] * df_mrk['TS_Diff'][i])
    df_mrk['InterpHgt'][i] = (df_mrk['ClosestHgt'][i] * (1 - df_mrk['TS_Diff'][i])) + \
                             ( df_mrk['SndClosestHgt'][i] * df_mrk['TS_Diff'][i])

    # Conversion of phase compensation between antennae and antennae to CMOS centre (in mm --> in degrees)
    df_mrk['PhaseCompNS_deg'][i] = df_mrk['PhaseCompNS'][i] / 1000000 / 111.111
    df_mrk['PhaseCompEW_deg'][i] = df_mrk['PhaseCompEW'][i] / 1000000 / degLon
    df_mrk['PhaseCompV_m'][i] = df_mrk['PhaseCompV'][i] / 1000

    # Calulate the updated positions
    df_mrk['UpdatedLat'][i]= df_mrk['InterpLat'][i] + df_mrk['PhaseCompNS_deg'][i]
    df_mrk['UpdatedLon'][i] = df_mrk['InterpLon'][i] + df_mrk['PhaseCompEW_deg'][i]
    df_mrk['UpdatedHgt'][i] = df_mrk['InterpHgt'][i] - df_mrk['PhaseCompV_m'][i] # minus because downward is positive
    print("Photo #" + str(i) + " --> " + str(df_mrk['UpdatedLat'][i]) + " ; " + str(df_mrk['UpdatedLon'][i]) + " ; " +
          str(df_mrk['UpdatedHgt'][i]))


# Calculate some statistics
df_mrk['DiffLat']=df_mrk['latitude'] - df_mrk['UpdatedLat']
df_mrk['DiffLon']=df_mrk['longitude'] - df_mrk['UpdatedLon']
df_mrk['DiffHgt']=df_mrk['height'] - df_mrk['UpdatedHgt']

print('\n--> I updated ' + str(i) + ' camera positions')
print('The mean change in NS location is ' + str(df_mrk['DiffLat'].mean()) + ' degrees (' +
      str(df_mrk['DiffLat'].mean()*1000 * 111) + ' m)'  )
print('The mean change in EW location is ' + str(df_mrk['DiffLon'].mean()) + ' degrees (' +
      str(df_mrk['DiffLon'].mean()*1000 * degLon) + ' m)'  )
print('The mean change in Vert location is ' + str(df_mrk['DiffHgt'].mean()) + ' m ')


# -----------------------------
# E. Output CSV
# -----------------------------
# Create a final CSV file
df_final = df_mrk[['UpdatedLat', 'UpdatedLon', 'UpdatedHgt']].copy()
df_final.rename(columns={'UpdatedLat': 'Latitude', 'UpdatedLon': 'Longitude','UpdatedHgt': 'Elevation'}, inplace=True)
df_final.insert(0,'Photo','name')
imagelist=[]
for file in os.listdir(PictureFolder):
    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tif')):
        imagelist.append(file)
df_final['Photo']=imagelist

df_final.to_csv(OutputCSVFile,index = None)
print('\nI created a CSV files with the updated positions names located in :\n'+ str(OutputCSVFile))