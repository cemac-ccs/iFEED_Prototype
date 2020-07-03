#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 12:40:46 2020

Data Collator

Combines data for iFEED runs into single country-level files.

@author: chmcsy
"""

import iris
import os
import year_collator as rcpcol
import errlib
from glob import glob
import nco

nco=Nco()

countries={
        "malawi":0,
        "safrica":1,
        "tanzania":2,
        "zambia":3
        }
#crops={
#      "cassava":0,
#      "groundnut":1,
#      "maize":2,
#      "millet":3,
#      "potato":4,
#      "rice":5,
#      "sorghum":6,
#      "soybean":7,
#      "sugarcane":8,
#      "sweetpot":9,
#      "wheat":10
#      }
crops={
      "maize":0,
      "potato":1,
      "soybean":2
      }
models={
       "bcc-csm1-1":0,
       "bcc-csm1-1-m":1,
       "BNU-ESM":2,
       "CanESM2":3,
       "CNRM-CM5":4,
       "CSIRO-Mk3-6-0":5,
       "GFDL-CM3":6,
       "GFDL-ESM2G":7,
       "GFDL-ESM2M":8,
       "IPSL-CM5A-LR":9,
       "IPSL-CM5A-MR":10,
       "MIROC5":11,
       "MIROC-ESM":12,
       "MIROC-ESM-CHEM":13,
       "MPI-ESM-LR":14,
       "MPI-ESM-MR":15,
       "MRI-CGCM3":16,
       "NorESM1-M":17
       }
rcps={
     "rcp26":0,
     "rcp85":2
     }

innerproc = 8

outpth='/nfs/a101/chmcsy/ncouts'

datadir='/nfs/a101/earsj/glamOuts/africap/DIMlookup/rawouts'

def dirverify(iopath, inout):

    if not os.path.exists(iopath):
        if inout == "output":
            print('Directory for netCDF output does not exist\n')
            try:
                os.makedirs(iopath)
            except:
                raise errlib.FileError("Unable to create output folder")
            else:
                print ("Folder {} was created".format(iopath))
        else:
            raise errlib.FileError('Directory for netCDF output does not exist\n')


    if iopath and not os.path.isdir(iopath):
        	raise errlib.ArgumentsError('NetCDF '+inout+' location is not a directory\n')

def filesincountry(country):

    countrylst = []
    for crop in crops.keys():
        for model in models.keys():
            for rcp in rcps.keys():
                countrylst.append(os.path.join(datadir,country,crop,model,rcp))

    for path in countrylst:
        if not os.path.exists(path):
            countrylst.remove(path)
            print (path)
            continue
        if len(os.listdir(os.path.join(path,'2025'))) == 0:
            countrylst.remove(path)
            print (path)

    return countrylst

def rcp (ascdir):

    if ascdir[-1]=="/":
        simval=ascdir.split('/')[-5:-1]
    else:
        simval=ascdir.split('/')[-4:]
        ascdir=ascdir+"/"

    yrs=rcpcol.getyrs(ascdir)
    if len(yrs) == 0:
        raise errlib.FatalError("No yearly folders found in {}\n".format(ascdir))

    try:
        dimvals=[countries[valnames[0]],crops[valnames[1]],models[valnames[2]],rcps[valnames[3]]]
    except:
        raise errlib.ArgumentsError("Could not assign dimensions based on the values: \n\ncountry = {},\ncrop = {},\nmodel = {},\nrcp = {}".format(*valnames))

    outfil=os.path.join(outpth,"ind_rcp",simval[0],"_".join(simval[1:]))

    indata=[yrs,ascdir,simval,innerproc,dimvals,outfil]

    if innerproc > 1:

        rcpcol.multiprocess_rcp(indata)

    else:

        rcpcol.singleprocess_rcp(indata)

def catdata(catlist,outfil,dim):

    nco.ncks(input=catlist[0], output="{}_recdim.nc".format(catlist[0][:-3]), options=['-O','-h', '--mk_rec_dmn '+dim])

    catlist.insert(1,"{}_recdim.nc".format(catlist[0][:-3]))
    newfile=outfil+'.nc'
    (path, file) = os.path.split(newfile)
    if not os.path.exists(path):
        os.makedirs(path)
    nco.ncrcat(input=catlist[1:], output=newfile)

    for file in catlist:
        os.remove(file)


def combinedata(country):

    dataloc = os.path.join(outpth,'ind_rcp',country)

    for crop in crops.keys():
        for model in models.keys():
            catlst1=glob(os.path.join(dataloc,"{}_{}_*.nc".format(crop,model)))
            catlst1.sort()
            catdata(catlist1,os.path.join(dataloc,"{}_{}.nc".format(crop,model)),"rcp")

        catlst2=glob(os.path.join(dataloc,"{}_*.nc".format(crop)))
        catlst2.sort()
        catdata(catlist2,os.path.join(dataloc,"{}_{}.nc".format(crop)),"model")

    catlst3=glob(os.path.join(dataloc,"*.nc"))
    catlst3.sort()
    catdata(catlst3,os.path.join(outpth,country+".nc"),"crop")

    nco.ncks(input=catlist[0], output="{}_recdim.nc".format(catlist[0][:-3]), options=['-O','-h', '--mk_rec_dmn time'])


def singlecountry (dirlst,country):

    print ("Collecting and merging data for {}".format(country))

    bigcubelist=iris.cube.CubeList([])

    for direc in dirlst:
        rcp(direc)

    combinedata(country)

    outcubelst=bigcubelist.concatenate()

    return outcubelst

def main():

    dirverify(datadir,"input")

    os.chdir(datadir)

    dirverify(outpth, "output")

    for country in countries.keys():

        dirlst=filesincountry(country)

        cubelst=iris.cube.CubeList([])

        cubelst=singlecountry(dirlst,country)

        print ("Cube output for %s\n" % country)
        print (cubelst[0])

        outfil = os.path.join(outpth,country+'.nc')

        try:
            iris.fileformats.netcdf.save(cubelst, outfil, zlib=True)
        except:
            raise errlib.NonFatal("Could not output the cube for %s" % country)

if __name__=="__main__":
    main()