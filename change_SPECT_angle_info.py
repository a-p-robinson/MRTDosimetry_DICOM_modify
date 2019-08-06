# -*- coding: utf-8 -*-
"""
Created on Tue Jun 11 12:45:42 2019
import radial position from txt list and other position info from a reference GE dcm file into a Siemens dcm file
@author: jdabin

Copyright (C) 2019 Jeremie Dabin                                       

This program is free software: you can redistribute it and/or modify     
it under the terms of the GNU General Public License as published by     
the Free Software Foundation, either version 3 of the License, or        
(at your option) any later version.                                      

This program is distributed in the hope that it will be useful,          
but WITHOUT ANY WARRANTY; without even the implied warranty of           
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            
GNU General Public License for more details.                             

You should have received a copy of the GNU General Public License        
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import pydicom
import os

os.chdir("C://Users//jdabin//Desktop//Input")
dataFile = open("detector_position_GE.txt", "r")
rad_position = []
for line in dataFile:
    rad_position.append(line.split()[0])
dataFile.close()
ds_ref = pydicom.read_file("Tomo24hrBC_EM1001_DS.dcm")

os.chdir("C://Users//jdabin//Desktop//Input//SPECT")
for file_name in os.listdir():
    ds = pydicom.read_file(file_name)
    #(0054,0022) Detector Information Sequence
    if ds[0x00540021].value == 2:
        ds[0x00540022][0][0x00181142].value = rad_position[0:60] # 60 values for 120 frames if 2 detectors
        ds[0x00540022][0][0x00540200].value = ds_ref[0x00540052][0][0x00540200].value
        ds[0x00540022][1][0x00181142].value = rad_position[60:120]
        if (ds_ref[0x00540052][0][0x00540200].value + 180) >= 360:
            ds[0x00540022][1][0x00540200].value = str(ds_ref[0x00540052][0][0x00540200].value + 180 - 360)
        else:
            ds[0x00540022][1][0x00540200].value = str(ds_ref[0x00540052][0][0x00540200].value + 180)
        #(0054,0052) Rotation Information Sequence
        ds[0x00540052][0][0x00181140].value = ds_ref[0x00540052][0][0x00181140].value #rotation direction - 1 value
        ds[0x00540052][0][0x00181142].value = rad_position[0:60] # Radial position --> 60 values for 120 frames if 2 detectors
        ds[0x00540052][0][0x00181144].value = ds_ref[0x00540052][0][0x00181144].value #angular step - 1 value
        ds[0x00540052][0][0x00540200].value = ds_ref[0x00540052][0][0x00540200].value # Start angle - 1 value
    # following else clause not tested
    else: 
        ds[0x00540022][0][0x00181142].value = rad_position[0:120]
        ds[0x00540022][0][0x00540200].value = ds_ref[0x00540052][0][0x00540200].value
        #(0054,0052) Rotation Information Sequence
        ds[0x00540052][0][0x00181140].value = ds_ref[0x00540052][0][0x00181140].value #rotation direction - 1 value
        ds[0x00540052][0][0x00181142].value = rad_position[0:120] # Radial position
        ds[0x00540052][0][0x00181144].value = ds_ref[0x00540052][0][0x00181144].value #angular step - 1 value
        ds[0x00540052][0][0x00540200].value = ds_ref[0x00540052][0][0x00540200].value # Start angle - 1 value
    ds.save_as(file_name)
