# -*- coding: utf-8 -*-
"""
Created on Mon May 28 13:56:52 2018
Summary: 
Import images (dcm,ima,mhd or hdr) into a copy of DICOM files from a specific SPECT-CT system

Usage: DICOM_modify.py [-h] -m MODEL -w WORKSTATION -i INPUT_FOLDER
                       [-o OUTPUT_FOLDER]                       
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

#%%Library import
from pathlib import Path
import os
import pydicom
from pydicom._dicom_dict import DicomDictionary  # the actual dict of {tag: (VR, VM, name, is_retired, keyword), ...}
import numpy as np
import re
import argparse
import sys
from natsort import natsorted

list_models=["Brightview XCT", "Discovery 670", "Infinia Hawkeye4", "Optima 640", "Symbia T2", "Symbia Intevo Bold"]
list_stations=["Hermes", "Jetstream", "Syngo","e.soft", "Xeleris"]

#%%
def changeTagValue(ds, tag, Value):
    """
    
    Summary:
    Change tag value from file ds and replace it with Value
   
    Parameters:
    - ds: a DICOM file
    - tag: a Tag value (or a list of tag for nested tags) as int or 0xAAAABBBB or [0xAAAABBBB, 0xAAAABBBB]
    - Value: the new Tag value
     
    Remarks:
     - if Tag present in DICOM file, tag changed
     - if Tag absent, created and message printed
     - if nested tag (up to third level: ex: ds[0x00540012][0][0x00540013][0][0x00540014]), value changed; does not work if absent 
     - necessary to import from pydicom._dicom_dict import DicomDictionary 
    """
     
     # if tag is list --> nested tag
    if isinstance(tag, list):
        if len(tag)==2:
            ds[tag[0]][0][tag[1]].value=Value
        elif len(tag)==3:
            ds[tag[0]][0][tag[1]][0][tag[2]].value=Value
        elif len(tag)>3:
            print("code needs to be adapted")    
    elif tag in ds:
        ds[tag].value=Value
    #if Tag not in Dicom file, message printed and new Tag is created based on DicomDictionary definitions 
    else:
        print("Tag "+str(tag)+" created")
        #add_new(tag, VR, value)
        ds.add_new(tag,DicomDictionary[tag][0], Value)

#%%
def lastReplace(text, increment):
    """
    
    Summary:
    replace last element from text with last element + increment
    
    Parameters:
    - text: a string composed of elements separated by "."
    - increment: the increment to be added to the last element of text
    
    Remarks:
    - 
    """
    [start_text, end_text] = text.rsplit(".", 1)
    final_text=start_text+"."+str(int(end_text)+increment)
    return final_text  

#%%
def readHDR(hdrFileName):
    """
    Summary:
    extract the raw data filename, endianess, dimensions and type from an interfile header (.hdr)
   
    Parameters:
    - hdrFileName: the interfile header file name
     
    Remarks:
    -
    """
    hdrFile = open(hdrFileName, "r")
    for line in hdrFile:
        if re.search("name of data file", line):
            line = line.rstrip("\n\r")
            dataFileName = re.split("=", line)[-1]
        if re.search("matrix size \[1\]", line): #"\[" necessary because regular expression if not "[" in line works
            line = line.rstrip("\n\r")
            dimX = re.split("=", line)[-1]
        if re.search("matrix size \[2\]", line):
            line = line.rstrip("\n\r")
            dimY = re.split("=", line)[-1]
        if re.search("number of projections", line):
            line = line.rstrip("\n\r")
            line = line.rstrip("\n\r")
            dimZ = re.split("=", line)[-1]
        if re.search("imagedata byte order", line):
           line = line.rstrip("\n\r")
           words = re.split("=", line)[-1]
           if re.match("LITTLEENDIAN", words):
               endianess = "<"
           if re.match("BIGENDIAN", words):
               endianess = ">"      
        if re.search("number format", line):
            line = line.rstrip("\n\r")
            words = re.split("=", line)[-1]
            if re.match("unsigned integer", words):
                dtype = "u"
            if re.match("signed integer", words):
                dtype = "i"
        if re.search("number of bytes per pixel", line):
            line=line.rstrip("\n\r")
            bits=re.split("=", line)[-1]
    hdrFile.close()

    return (int(dimZ),int(dimY),int(dimX)), dataFileName, np.dtype(endianess+dtype+bits)

#%%
def readRawHDRData(hdrFileName):
    """
    Summary:
    convert the raw data from an interfile into a numpy array
   
    Parameters:
    - path: the path to the hdr file and the raw data file
    - hdrFileName: the interfile header file name
     
    Remarks:
    -
    """
    dimensions, dataFileName, dtype = readHDR(hdrFileName)
    arrayFlat = np.fromfile(dataFileName,dtype=dtype)
    array3D = np.reshape(arrayFlat, dimensions, order='C')
    return array3D 
#%%
def readMHD(mhdFileName):
    """
    Summary:
    extract the raw data filename, endianess, dimensions and type from an mhd header (.mhd)
   
    Parameters:
    - mhdFileName: the interfile header file name
     
    Remarks:
    -
    """
    mhdFile = open(mhdFileName, "r")
    for line in mhdFile:
        if re.search("ElementDataFile", line):
            line = line.rstrip("\n\r")
            dataFileName = re.split(" ", line)[-1]
        if re.search("DimSize", line):
            line = line.rstrip("\n\r")
            dimX,dimY,dimZ = re.split(" ", line)[-3:]
        if re.search("BinaryDataByteOrderMSB", line) or re.search("ElementByteOrderMSB", line):
           line = line.rstrip("\n\r")
           words = re.split(" ", line)[-1]
           if re.match("False", words):
               endianess = "<"
           if re.match("True", words):
               endianess = ">"      
        if re.search("ElementType", line):
            line = line.rstrip("\n\r")
            if re.split(" ", line)[-1]=="MET_USHORT":
                dtype_bits = "u2"
            if re.split(" ", line)[-1]=="MET_SHORT":
                dtype_bits = "i2"
                
    mhdFile.close()

    return (int(dimZ),int(dimY),int(dimX)), dataFileName, np.dtype(endianess+dtype_bits)

#%%
def readRawMHDData(mhdFileName):
    """
    Summary:
    convert the raw data from a mhd file into a numpy array
   
    Parameters:
    - path: the path to the mhd file and the raw data file
    - mhdFileName: the interfile header file name
     
    Remarks:
    -
    """
    dimensions, dataFileName, dtype = readMHD(mhdFileName)
    arrayFlat = np.fromfile(dataFileName,dtype=dtype)
    array3D = np.reshape(arrayFlat, dimensions, order='C')
    return array3D 

#%%image_to_array
def image_to_array(images):
    """
    Summary:
    convert images (hdr,mhd or dcm) file into a numpy array
     
    Parameters:
    - images: the name of the image file
        
    Remarks:
    -
    """
    if images.lower().endswith("dcm") or images.lower().endswith("ima"):
        ds = pydicom.read_file(images)
        array= ds.pixel_array
    elif images.lower().endswith("hdr"):
        array=readRawHDRData(images)
    elif images.lower().endswith("mhd"):
        array=readRawMHDData(images)
    return array
#%% 
def ctAddSim(input_folder, sim_input_folder, output_folder):
    """
    
    Summary:
    create new CT DICOM files with new images
    
    Parameters:
    - input_folder: path to the folder containing the original CT DICOM files
    - sim_input_folder: path to the folder containing the simulated images (dcm (or IMA) or hdr or mhd)
    - output_folder: path to the folder where the modified CT DICOM files are to be saved
   
    Remarks:
    - one file containing all simulated projection images or one file for each projection image
    - simulated image dimensions as row x col x n_images or if one image per file row x col
      
    """
    list_files=os.listdir(input_folder)
    list_sim_trans=os.listdir(sim_input_folder)
    list_sim=[]
    image_extension=["dcm","ima","mhd","hdr"]
    for item in image_extension:
        sim=[file for file in list_sim_trans if file.lower().endswith(item)]
        list_sim.extend(sim)
    n_list_sim=len(list_sim)
    list_sim=natsorted(list_sim)
    for [index, file] in enumerate(list_files):
        os.chdir(input_folder)
        file_name_modified=str("modified_"+file)
        ds=pydicom.read_file(file)
        #modify tags
        val=ds[0x00080018].value
        val=lastReplace(val, 10000)
        changeTagValue(ds,0x00080018,val)
        val=ds[0x0020000d].value
        val=lastReplace(val, 10000)
        changeTagValue(ds,0x0020000d,val)
        val=ds[0x0020000e].value
        val=lastReplace(val, 10000)
        changeTagValue(ds,0x0020000e,val)
        # add simulated images 
        os.chdir(sim_input_folder)
        if n_list_sim == 1:
            array=image_to_array(list_sim[0])
            array_short = array[index,:,:] 
            ds.PixelData=array_short.tostring()
        else:
            array=image_to_array(list_sim[index])
            ds.PixelData=array.tostring()            
        #save files
        os.chdir(output_folder)
        ds.save_as(file_name_modified)
#%%
def spectAddSim(input_folder, sim_input_folder, output_folder, model, workstation):
    """
    
    Summary:
    create new SPECT DICOM files with new images
    
    Parameters:
    - input_folder: path to the folder containing the original SPECT DICOM files
    - sim_input_folder: path to the folder containing the simulated images (dcm (or IMA) or hdr or mhd)
    - output_folder: path to the folder where the modified SPECT DICOM files are to be saved
    - model: name of the SPECTCT model, to be chosen among list_models
    - workstation: name of the reconstruction workstation, to be chosen among list_stations
    
    Remarks:
    - one DICOM file containing all energy windows or one file for each window
    - one file containing all simulated energy windows or one file for each window
    - simulatde image dimensions as row x col x frames or if one image per file row x col
    - if workstation = "Hermes", only first energy window is kept (the scatter windows are removed) and related tags are modified
    
    """
    list_files=os.listdir(input_folder)
    #just keep first energy window if reconstruction on Hermes
    if (model == "Optima 640" or model == "Brightview XCT") and workstation == "Hermes":
        list_files=[list_files[0]]
    n_files=len(list_files)
    list_sim_trans=os.listdir(sim_input_folder)
    list_sim=[]
    image_extension=["dcm","ima","mhd","hdr"]
    for item in image_extension:
        sim=[file for file in list_sim_trans if file.lower().endswith(item)]
        list_sim.extend(sim)
    n_list_sim=len(list_sim)
    list_sim=natsorted(list_sim)
    for [index, file] in enumerate(list_files):
       os.chdir(input_folder)
       file_name_modified=str("modified_"+file)
       ds=pydicom.read_file(file)
       n_energy_w=ds[0x00540011].value
       n_frames=ds[0x00280008].value
       # might become an input
       n_emission_w=1
       ### modify of tags to prevent original overwriting ###
       val=ds[0x00080018].value
       val=lastReplace(val, 10000)
       changeTagValue(ds,0x00080018,val)
       val=ds[0x0020000d].value
       val=lastReplace(val, 10000)
       changeTagValue(ds,0x0020000d,val)
       val=ds[0x0020000e].value
       val=lastReplace(val, 10000)
       changeTagValue(ds,0x0020000e,val)
       if model == "Symbia Intevo Bold":
           if "Advanced" not in ds[0x0008103E].value:
               #0X00611077 --> reference to series of Advanced NM (0X0020000E)
               val=ds[0x00611077].value
               val=lastReplace(val, 10000)
               changeTagValue(ds,0x00611077,val)
               #0X00611078 --> reference to Media storage SOP instance UID of Advanced NM (0X00020003)
               val=ds[0x00611078].value
               val=lastReplace(val, 10000)
               changeTagValue(ds,0x00611078,val)
       ### add simulated images ###
       os.chdir(sim_input_folder)
       if (n_list_sim == n_files) :           
           array=image_to_array(list_sim[index])
       elif (n_list_sim == 1 and n_files > 1):
           array=image_to_array(list_sim[0])
           array=array[(0+int(n_frames*index)):int(n_frames*(1+index)),:,:]
       elif (n_list_sim > 1 and n_files == 1):
           array=np.empty(shape=ds.pixel_array.shape, dtype=ds.pixel_array.dtype)
           for i in range(n_list_sim):
               array[(0+int(n_frames/n_energy_w*index)):int(n_frames/n_energy_w*(1+index)),:,:]=image_to_array(list_sim[i])
       ds.PixelData=array.tostring()
       ### modify tags related to Hermes ###
       if workstation == "Hermes":
           if model != "Optima 640" or model != "Brightview XCT":
               #remove or modify tags related to scatter windows
               changeTagValue(ds,0x00280008,int(ds[0x00280008].value*(n_emission_w/n_energy_w)))
               changeTagValue(ds,0x00540010,ds[0x00540010].value[0:int(len(ds[0x00540010].value)*(n_emission_w/n_energy_w))])
               changeTagValue(ds,0x00540011,n_emission_w)
               changeTagValue(ds,0x00540012,ds[0x00540012][0:n_emission_w])
               changeTagValue(ds,0x00540020,ds[0x00540020].value[0:int(len(ds[0x00540020].value)*(n_emission_w/n_energy_w))])
               changeTagValue(ds,0x00540050,ds[0x00540050].value[0:int(len(ds[0x00540050].value)*(n_emission_w/n_energy_w))])
               changeTagValue(ds,0x00540090,ds[0x00540090].value[0:int(len(ds[0x00540090].value)*(n_emission_w/n_energy_w))]) 
               if model == "Symbia T2" or model == "Symbia Intevo Bold":   
                   changeTagValue(ds,0x00351001,"Simulated EM1")
               elif model == "Discovery 670" or model == "Infinia Hawkeye4":
                   # GE Discovery specific tags
                   changeTagValue(ds,0x0011100D,"No scatter windows")
                   changeTagValue(ds,0x00111012,"Simulated EM1")
                   changeTagValue(ds,0x00111030,"Simulated EM1")
                   changeTagValue(ds,0x00111050,"Simulated EM1")
                   changeTagValue(ds,0x00551012,ds[0x00551012][0:n_emission_w])   
           elif model == "Optima 640":
               # GE Optima specific tags
               changeTagValue(ds,0x0011100D,"No scatter windows")  
               changeTagValue(ds,0x00111012,"Simulated EM1")
               changeTagValue(ds,0x00111030,"Simulated EM1")
               changeTagValue(ds,0x00111050,"Simulated EM1")
           else:
               print("Model not recognised or not implemented")
               sys.exit()
       # Save file
       os.chdir(output_folder)
       ds.save_as(file_name_modified)
#%%Parsing
# Parse the arguments
parser = argparse.ArgumentParser(description = "Create a copy of original DICOM files with modified images")
parser.add_argument("-m", "--model", help="\"Brightview XCT\", \"Discovery 670\", \"Infinia Hawkeye4\", \"Optima 640\", \"Symbia T2\", \"Symbia Intevo Bold\"", required=True)
parser.add_argument("-w", "--workstation", help="\"Hermes\", \"Jetstream\", \"Syngo\", \"Xeleris\"", required=True)
parser.add_argument("-i", "--input_folder", help = "Path to the folder containing the original DICOM files and the simulated images \"C:\\Users\\...\"", required=True)
parser.add_argument("-o", "--output_folder", help = "Optional: Path to the folder where the modified images are to be saved \"C:\\Users\\...\"", required=False)
parser._optionals.title = "Arguments"
args = parser.parse_args()

# Process the file
# Input folders
path_CT=Path(args.input_folder).joinpath("CT")
path_SPECT=Path(args.input_folder).joinpath("SPECT")
path_CT_sim=Path(args.input_folder).joinpath("sim_CT")
path_SPECT_sim=Path(args.input_folder).joinpath("sim_SPECT")
# Output folders
if args.output_folder:
    path_output_folder=Path(args.output_folder)
else:
    path_output_folder=Path(args.input_folder).joinpath("Output")
    path_output_folder.mkdir()
path_modified_CT=path_output_folder.joinpath("CT_modified")
path_modified_CT.mkdir()
path_modified_SPECT=path_output_folder.joinpath("SPECT_modified")
path_modified_SPECT.mkdir()

# Are model and workstation recognised?
if args.model not in list_models:
    print("The system model " + args.model + " is not recognised. \nPlease check the spelling or try another name. \nThe recognised systems are:")
    for item in list_models:
        print("\n" + item)
    sys.exit()
if args.workstation not in list_stations:
    print("The workstation " + args.workstation + " is not recognised. \nPlease check the spelling or try another name. \nThe recognised workstations are:")
    for item in list_stations:
        print("\n" + item)
    sys.exit()
if args.workstation and args.model:
    print("\nOriginal acquisition system: " + args.model + " to be reconstructed on " + args.workstation
          + "\nOriginal DICOM files in folders " + str(path_CT) + " and " + str(path_SPECT))

# Are original and simulated images provided?
if os.listdir(path_CT)==[] :
    print("No CT files provided")
elif os.path.isdir(path_CT_sim):
    if not os.listdir(path_CT_sim)==[]:
        print("\nImporting simulated CT images from " + str(path_CT_sim))
        ctAddSim(path_CT, path_CT_sim, path_modified_CT)
        print("\nCT files successfully modified and saved in " + str(path_modified_CT))
    else:
        print("\nNo simulated CT images were found")
if os.listdir(path_SPECT)==[]:
    print("No SPECT files provided")
elif os.path.isdir(path_SPECT_sim):
    if not os.listdir(path_SPECT_sim)==[]:
        print("\nImporting simulated SPECT images from " + str(path_SPECT_sim))
        spectAddSim(path_SPECT, path_SPECT_sim, path_modified_SPECT, args.model, args.workstation)
        print("\nSPECT files successfully modified and saved in " + str(path_modified_SPECT))
    else:
        print("\nNo simulated CT images were found")
print("\n")