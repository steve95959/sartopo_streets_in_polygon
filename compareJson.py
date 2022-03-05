# compareJson.py - read a SARTopo geojson file that contains
#   objects grouped into folders, and split it into one file per folder.
#   Each generated file will have a folder and all the objects that
#   were in that folder in the original file.  This is done for two reasons:
#   1) as of May 2021, the import checkbox list in SARTopo is not grouped
#       by folder, like the export checkbox is (feature request submitted 5-17-2021)
#   2) the import checkbox list can become very laggy and glitchy if the file
#       has thousands of objects

import json
import os
import glob
import shapely

# if the json file decodes to a dictionary j, then
# j['features'] is a list of objects (each one being a dictionary)

# two passes:
# 1) only read Folder objects; for each one, read the name and the id;
#     use the name to determine the generated filename; use the id
#     to find contained objects in the second pass
# 2) real all objects (including folders); if id or folderID matches
#     a folder ID from the first pass, then write the object to
#     the corresponding file

# fn='C:\\Users\\caver\\Documents\\zh\\ZH-CSP-2021May26.json'
# dir='C:\\Users\\caver\\Documents\\zh'
# prefix=''
# suffix='-2021May26'

# fn='C:\\Users\\caver\\Downloads\\Dixie\\DixieStreetsInPolygons.json'
# dir='C:\\Users\\caver\\Downloads\\Dixie\\DixieStreetsInPolygons'

print("At top")
dir='C:\\Users\\steve\\Documents\\SAR Documents\\ZoneHaven\\ZonesWithBufferAssignments-7Jan2022'
dir2='C:\\Users\\steve\\documents\sar documents\\zonehavenFolders'
## get list of files, open one at a time
print("B4 loop")
os.chdir(dir)
print("AFT dir set")
for file in glob.glob("*.json"):
  print("File:"+str(file))
  fn=os.path.join(dir,file)
  parts = file.split("-")
  f2ext = '2022Mar1'
  file2 = parts[0]+"-"+parts[1]+"-"+f2ext
  fn2=os.path.join(dir2,file2+'.json')
##### cycle thru files in fn; use same name for fn2
  classCount={
    'Folder':0,
    'Assignment':0,
    'Shape':0}
  classCount2={
    'Folder':0,
    'Assignment':0,
    'Shape':0}

  with open(fn) as jf:
    j=json.load(jf)
    features=j['features'] # this is a list of objects (each one being a dictionary)

  with open(fn2) as jf2:
    j2=json.load(jf2)
    features2=j2['features'] # this is a list of objects (each one being a dictionary)

##### how to handle streets with more than one segment?  Don't know if segments come in
    ###   the same order


# make list of matched assignments found in file 2
  file2fnd = [0]*600
  print("At initialize")
  for f in features:
        p=f['properties']
        c=p['class']
        classCount[c]+=1
        if c == 'Assignment':
            if p.get('letter') == None: continue  # skip
            # print("first:"+str(p['letter']))
            if p['letter'] == 'UNNAMED' or p['letter'] == "": continue  # skip            
            g=f['geometry']
            coord = g['coordinates']
            found = 0
            pntr = -1
            for f2 in features2:
               p2=f2['properties']
               c2=p2['class']
               if c2 == 'Assignment':
                 if p2.get('letter') == None: continue  # skip
                 pntr += 1
                 if file2fnd[pntr] == 1: continue  # already used - same name
                 # print("stuff:"+str(p2['letter']))
                 if p2['letter'] == p['letter']:
                   found = 1
                   file2fnd[pntr] = 1
                   ####  compare the two assignment shapes using shapely .equal
                   break



            if found == 0:
                print("Assignment "+p['letter']+" in File 1 was not found in File2")

  pntr = -1
  for f2 in features2:
        p2=f2['properties']
        c2=p2['class']
        classCount2[c2]+=1
        if c2 == 'Assignment':
            if p2.get('letter') == None:  continue   # skip
            pntr += 1
            if p2['letter'] == 'UNNAMED' or p2['letter'] == "": continue  # skip
            if file2fnd[pntr] == 0:
                print("Assignment "+p2['letter']+" in File 2 was not found in File1")
 

