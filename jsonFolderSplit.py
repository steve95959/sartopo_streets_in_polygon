# jsonFolderSplit.py - read a SARTopo geojson file that contains
#   objects grouped into folders, and split it into one file per folder.
#   Each generated file will have a folder and all the objects that
#   were in that folder in the original file.  This is done for two reasons:
#   1) as of May 2021, the import checkbox list in SARTopo is not grouped
#       by folder, like the export checkbox is (feature request submitted 5-17-2021)
#   2) the import checkbox list can become very laggy and glitchy if the file
#       has thousands of objects

import json
import os

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

fn='C:\\Users\\caver\\Downloads\\Marin\\ZHMarinStreetsInPolygons.json'
dir='C:\\Users\\caver\\Downloads\\Marin\\ZHMarinStreetsInPolygons'

prefix=''
suffix='-2021Aug22'

classCount={
    'Folder':0,
    'Assignment':0,
    'Shape':0}

folders={}

with open(fn) as jf:
    j=json.load(jf)
    features=j['features'] # this is a list of objects (each one being a dictionary)

    # pass 1: get folders
    for f in features:
        p=f['properties']
        c=p['class']
        classCount[c]+=1
        if c=='Folder':
            folderName=p['title']
            id=f['id']
            folders[id]=folderName # storing id as keys will make matching faster in pass 2

    for fid in folders:
        folderName=folders[fid]
        # slash in folder name causes exception; replace slashes here
        folderName=folderName.replace('/','.')
        outFileName=os.path.join(dir,prefix+folderName+suffix+'.json')
        print('writing '+outFileName)
        with open(outFileName,'w') as f2:
            j={
                'type':'FeatureCollection',
                'features':[x for x in features if x['properties'].get('folderId',None)==fid]+[x for x in features if x['id']==fid]
            }
            json.dump(j,f2)

print(json.dumps(classCount,indent=3))