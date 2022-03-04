# #############################################################################
#
#  sartopo_streets_in_polygon.py - create buffer assignments for all roads
#    that are at least partially covered by a given polygon; intended
#    for evacuation purposes, where an evacuation shape is specified, and
#    buffer assignments are needed for all roads at least partially inside
#    that evacuation shape
#
#  concept:
#   Start with a repository of street data - not necessarily sartopo objects,
#     each item in the repository should contain a street name and a list
#     of vertices; probably easiest to get these from GIS data, but, could
#     also be parsed directly from sartopo objects, either from API calls
#     or from a pre-existing json/gpx/kml file
#   1. read the bounding polygon as a Shape object using the API
#          (sts.getFeatures("Shape") then find the one with the specified name)
#   2. iterate over street data, and use python Shapely module to select streets
#        that are at least partially covered by the bounding polygon
#   3. send those streets to sartopo
#       - as lines: use sts.addLine()
#       - as line assignments: use sts.addLineAssignment()
#       - as buffers or buffer assignments:
#         - build the list of buffer polygon coordinates using Shapely buffer()
#         - send to the map using sts.addPolygon() or sts.addAreaAssignment()
#       - explore use of 'save' request to save multiple objects in one request?
#
#   developed for Nevada County Sheriff's Search and Rescue
#    Copyright (c) 2020 Tom Grundy
#
#  Contact the author at nccaves@yahoo.com
#   Attribution, feedback, bug reports and feature requests are appreciated
#
#  REVISION HISTORY
#-----------------------------------------------------------------------------
#   DATE   |  AUTHOR  |  NOTES
#-----------------------------------------------------------------------------
#  9-6-20     TMG        First commit
#  9-6-20     TMG        working for lines obtained from map using API
#  9-7-20     TMG        working for buffer assignments, using kml from QGIS
#                          to do: account for multi-segment roads in kml
# 9-11-20     TMG        handles multi-segment roads, but needs improvement;
#                          splits roads at zone edges; creates assignments
#                          using queued bulk-import
# 9-23-20     TMG        fix #6: read kml straight from county GIS download
#-----------------------------------------------------------------------------

from sartopo_python import SartopoSession
import json
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import split
# from pykml import parser
# from lxml import etree
import xml.etree.ElementTree as et
import copy
import re


# mapID="QARV"
# mapID="9NKJ"
# mapID="9K3"
# mapID="5N9"
#    mapID="HV1"
##mapID="9DE"
##mapID="AGD"
##mapID="CBH"
##mapID="71K"
##mapID="6B8"
##mapID="TFK"
mapID="JFM"
# boundaryName="NEV-E252"
# boundaryRegexList=["NEV-E305","NEV-E284","NEV-E292","NEV-E290","NEV-E252","GRS-E209"]
# boundaryRegexList=["NEV-E305","NEV-E284"]
# boundaryRegexList=["NCO.*"]
boundaryRegexList=[
    "GRS-E223",
    "GRS-E224",
    "NCO-E005",
    "NCO-E006",
    "NCO-E007",
    "NCO-E008",
    "NCO-E009",
    "NCO-E031",
    "NCO-E037",
    "NCO-E038",
    "NCO-E039",
    "NCO-E040",
    "NCO-E041",
    "NCO-E042",
    "NCO-E043",
    "NCO-E044",
    "NCO-E045",
    "NCO-E046",
    "NCO-E047",
    "NCO-E048",
    "NCO-E049",
    "NCO-E050",
    "NCO-E052",
    "NCO-E054",
    "NCO-E059",
    "NCO-E060",
    "NCO-E061",
    "NCO-E097",
    "NCO-E098",
    "NCO-E099",
    "NCO-E100",
    "NCO-E102",
    "NCO-E103",
    "NCO-E153",
    "NCO-E159",
    "NCO-E160",
    "NCO-E161",
    "NCO-E162",
    "NCO-E163",
    "NCO-E192",
    "NCO-E193",
    "NCO-E196",
    "NCO-E205",
    "NCO-E325",
    "NCO-E394",
    "NCO-E396",
    "NCO-E397"
]
debugStreetNameList=[]
# debugStreetNameList=["North Bloomfield-Graniteville Road"]
boundaryCoords=None
streets={}

# sts=SartopoSession("sartopo.com",mapID,sync=False,configpath="C:\\Users\\caver\\Downloads\\sts.ini",account="caver456@gmail.com")
# sts=SartopoSession(mapID=mapID,sync=False)
sts=SartopoSession(mapID=mapID,syncTimeout=60)
sts.stop() # we just want the initial sync to get boundary ids

shapes=sts.getFeatures("Shape",timeout=60)
print("Reading map "+mapID+":  "+str(len(shapes))+" shapes found.")

# build streets dictionary
#  - option 1: use lines on sartopo map
# for shape in shapes:
#     if shape["geometry"]["type"]=="LineString":
#         streetName=shape["properties"]["title"]
#         coords=shape["geometry"]["coordinates"] # need [0] for polygons but not lines due to json structure
#         print("adding line '"+streetName+"' with "+str(len(coords))+" vertices")
#         streets[streetName]=coords
#  - option 2: use lines from a gpx or json or kml
# gpx_file=open('C:\\Users\\caver\\Documents\\nevCoRoads.gpx','r')
# gpx=gpxpy.parse(gpx_file)
# for track in gpx.tracks:
#     name=track.name
#     streets[name]=[]
#     for segment in track.segments:
#         for point in segment.points:
#             streets[name].append([point.latitude,point.longitude]) # prelim: assume there's only one segment

# this kml parsing works for KML export from QGIS or from SARTopo and is not guaranteed to work for export from other tools;
#  see the detailed parsing documentation at https://docs.python.org/3.8/library/xml.etree.elementtree.html
#  and look at the kml file itself to see what is happening
# kmlFile='C:\\Users\\caver\\Documents\\nevCoRoads.kml'
# kmlFile='C:\\Users\\caver\\Downloads\\Road_Centerlines20200912.kml'
kmlFile='C:\\Users\\steve\\Documents\\SAR Documents\\Road_Centerlines20220225.kml'
# kmlFile='C:\\Users\\caver\\Downloads\\apiTest1.kml'
# kmlFile='C:\\Users\\caver\\Downloads\\joinTest4.kml'
kml=et.parse(kmlFile)
root=kml.getroot()
ns={'kml':root.tag.split('}')[0][1:]} # determine the namespace from the kml kmlns 'non-attribute'
placemarks=root.findall('.//kml:Placemark',ns)
unnamedIndex=1
# merging multiple segments of the same street:
#  the GIS data will likely be broken into 'segments' between intersections.  Each
#  segment is its own placemark, and they do not necessarily appear in the same sequence
#  or even in the same direction in the kml file as they should in the sartopo map.
# Therefore, the next placemark parsed with the same name as an existing placemark
#  is not necessarily contiguous with the already-existing placemark.
# This parser should be able to deal with that data.
# 1. When reading a placemark, if there is already a placemark by the same name,
#  save this new placemark with an indexed name i.e. 'MyStreet_2'
# 1. determine if the start or end coords if the new placemark are 'near' the start or
#  end coordinates of the existing placemark.  If so, append all but the first point
#  of the new placemark to the existing placemark (after reversing the 
#  order of coords of the new placemark if necessary, i.e. if end of new placemark is
#  'close' to end of existing placemark).  If not, make a new placemark suffixed with
#  an index number 'MyRoad_1' or such, to be post-processed later.
# 2. For post-processing, recursively repeat until all suffixed placemarks are processed:
#  for each suffixed placemark, determine if the start or end points are 'close to'
#  the start or end points of the first placemark; if it's a match, append as above
#  (after flipping as above if necessary,i.e. end of new placemark is 'close to' end
#  of first placemark) then delete the suffixed placemark from the list of suffixed
#  placemarks to process.
for pm in placemarks:
    name=""
    try:
        # FULLNAME = 'Cement Hill Road'; FN_DISP = 'CEMENT HILL RD' - shorter name saves map clutter!
        name=pm.find(".//kml:SimpleData[@name='FN_DISP']",ns).text
    except:
        try:
            name=pm.find('.//kml:name',ns).text
        except:
            name="UNNAMED_"+str(unnamedIndex)
            unnamedIndex+=1
    if not name: # this will happen if FULLNAME exists but is blank in which case its value is None, or if it is ""
        name="UNNAMED_"+str(unnamedIndex)
        unnamedIndex+=1
    # print("  processing "+name)
    coordinates=pm.find('.//kml:coordinates',ns)
    # add [0:2] to get rid of z coord in case it exists
    streets.setdefault(name,[]).append([list(map(float,x.split(',')[0:2])) for x in coordinates.text.split()])
print("Done parsing kml file "+kmlFile+".\n"+str(len(streets))+" street segments were read.")

# reduce multi-segment streets by joining end-to-end where possible
# to do 9-10-20:
#   - if no matches, try reversing the first segment then doing the loop again;
#       if still no matches, then add it as a separate street
#   - investigate names with many suffixes
#   - investigate odd shapes e.g. Brunswick Road:131:1165:1517:1675:1740:1770:1791:1807
d=0.0001 # tolerance to detect adjacent segment endpoints - about 30 feet
unmatchedIndex=0
streetNames=list(streets.keys()) # this list may be added to at the end of each iteration
for streetName in streetNames:
    debugStreet=False
    if streetName in debugStreetNameList:
        debugStreet=True
    segments=streets[streetName]
    reduced=segments[0]
    segments=segments[1:] # this works even if segments only had one element though in that case segments would be []
    if debugStreet:
        print("  Attempting reduction on "+streetName)
        print("    "+str(len(streets[streetName]))+" original segments (KML segments may NOT be contiguous)")
        print("     First original segment: "+str(len(reduced))+" points")
        print("        "+str(reduced[0])+" --> "+str(reduced[-1]))
        if len(streets[streetName])>1:
            print("     Last original segment: "+str(len(segments[-1]))+" points")
            print("        "+str(segments[-1][0])+" --> "+str(segments[-1][-1]))
    # print("STREET:"+streetName)
    # print("FIRST:"+str(reduced))
    # print("REST:"+str(segments))
    [lastReducedLat,lastReducedLon]=[0,0]
    while len(segments)>0:
        if debugStreet:
            print("\n  Current reduced segment ("+str(len(reduced))+" points):")
            print("  "+str(reduced[0])+" --> "+str(reduced[-1]))
            print("  lastReducedLat="+str(lastReducedLat)+"  lastReducedLon="+str(lastReducedLon))
        found=False
        segCopy=copy.copy(segments) # copy, so that segments.remove calls don't interfere with this loop
        for segment in segCopy:
            # for easier explanation, define the existing ('reduced') segment as a-->b and
            #  the segment being checked as c-->d
            [firstReducedLat,firstReducedLon]=reduced[0]
            [lastReducedLat,lastReducedLon]=reduced[-1]
            firstSegmentPoint=segment[0]
            lastSegmentPoint=segment[-1]
            [firstSegmentLat,firstSegmentLon]=firstSegmentPoint
            [lastSegmentLat,lastSegmentLon]=lastSegmentPoint
            if debugStreet:
                print("    Checking the next segment ("+str(len(segment))+" points): "+str(firstSegmentPoint)+"  -->  "+str(lastSegmentPoint))
            # check for all four end-to-end possibilities:
            if abs(firstSegmentLat-lastReducedLat)<d and abs(firstSegmentLon-lastReducedLon)<d: # a-->(b=c)-->d
                if debugStreet:
                    print("      match at end of existing segment, in same order; just append it")
                # segment is adjacent and in same sequence as reduced: append (all but first point) then remove
                found=True
                reduced.extend(segment[1:])
                segments.remove(segment)
            elif abs(lastSegmentLat-lastReducedLat)<d and abs(lastSegmentLon-lastReducedLon)<d: # a-->(b=d)<--c
                if debugStreet:
                    print("      match at end of existing segment, in reverse order; needs reversing before appending")
                # segment is adjacent but reversed: reverse, append (all but first point), then remove
                found=True
                reduced.extend(segment[-2::-1]) # this gets a reversed copy of the list, without the end element, without changing it
                segments.remove(segment)
            elif abs(firstSegmentLat-firstReducedLat)<d and abs(firstSegmentLon-firstReducedLon)<d: # d<--(c=a)-->b
                if debugStreet:
                    print("      match at beginning of existing segment, in same order; needs reversing before prepending")
                found=True
                reduced[:0]=segment[2:0:-1] # prepend a reversed copy of the segment, without its first element
                segments.remove(segment)
            elif abs(lastSegmentLat-firstReducedLat)<d and abs(lastSegmentLon-firstReducedLon)<d: # c-->(d=a)-->b
                if debugStreet:
                    print("      match at beginning of existing segment, in reverse order; just prepend it")
                found=True
                reduced[:0]=segment[:-1] # prepend except for the last element
                segments.remove(segment)
            elif debugStreet:
                    print("      no match")
            if debugStreet:
                print("    --> reduced segment now has "+str(len(reduced))+" points")
    # any segments remaining were not matched at all i.e. are not end-to-end adjacent with the
    #  starting segment or segments that joined to it; but, they still may form a new group of
    #  contiguous segments; so, save them as a new street and let them go through this processing
    #  again on a future iteration of the while loop, which is effectively recursion
        if not found:
    # if len(segments)>0:
            unmatchedIndex+=1
            newStreetName=streetName+":"+str(unmatchedIndex)
            if debugStreet:
                print("    NO MATCHES.  ADDING NEW STREET "+newStreetName)
            streets[newStreetName]=segments
            streetNames.append(newStreetName)
            segments=[]

    # now store the reduced street    
    streets[streetName]=reduced
    if debugStreet:
        print("\n  Reduced "+streetName+": "+str(len(streets[streetName]))+" points")
        sts.addLine(reduced,title='REDUCED-'+streetName)

# print(json.dumps(streets,indent=3))

# print("Eskaton Circle:\n"+str(streets["Eskaton Circle"]))

# print(str(len(streets.keys()))+' streets read from '+gpx_file)

# 1. find the boundary shapes
polygons=[s for s in shapes if s['geometry']['type']=='Polygon']
boundaryShapes=[]
'''  SDL 2/27/2022  Skip to just use all shapes in the map
for boundaryRegex in boundaryRegexList:
    print("\nSearching for "+boundaryRegex+"...")
    matches=[p for p in polygons if re.search(boundaryRegex,p['properties']['title'])]
    m=len(matches)
    s='polygons'
    if m==1:
        s='polygon'
    print("   "+str(m)+" matching "+s+" found.")
    boundaryShapes=boundaryShapes+matches
'''
boundaryShapes=polygons

print("complete list of boundary shapes:"+str(len(boundaryShapes))+" "+str(boundaryShapes))
for boundaryShape in boundaryShapes:
    boundaryCoords=boundaryShape["geometry"]["coordinates"][0] # coordinate list
    boundaryPolygon=Polygon(boundaryCoords) # Shapely object
    # # 1. find the boundary shape
    # for shape in shapes:
    #     # print("---SHAPE---  title="+shape["properties"]["title"])
    #     # print(json.dumps(shape,sort_keys=True,indent=3))
    #     if shape["geometry"]["type"]=="Polygon" and shape["properties"]["title"]==boundaryName:
    #         boundaryShape=shape # sartopo object
    #         boundaryCoords=shape["geometry"]["coordinates"][0] # coordinate list
    #         # print("Coords:"+str(boundaryCoords))
    #         boundaryPolygon=Polygon(boundaryCoords) # Shapely object
    #         break

    # 2. find streets at least partially covered by the boundary shape
    #   streets is a dictionary: key = street name, val = coordinate list
    streetsToAdd1={}
    for streetName in streets.keys():
        coords=streets[streetName]
        if LineString(coords).intersects(boundaryPolygon):
            streetsToAdd1[streetName]=coords

    # growing the boundary shape twice seems to give better results -
    #  use the first grown boundary to split the streets, then only
    #  select streets that are completely within the second grown boundary

    # problem: if an intersected road segment is crossed by the boundary
    #  more than twice, one or both portions can be excluded from the results.
    streetsToAdd={}
    grownBoundary1=boundaryPolygon.buffer(0.0003) # about 30 meters
    grownBoundary2=grownBoundary1.buffer(0.0003)  # about 30 more meters
    grownBoundary3=grownBoundary1.buffer(-0.0001) # about 10 less meters (accept all lines close or inside of zone)
    for streetName in streetsToAdd1.keys():
        # print("  "+streetName+" intersects and is a candidate for inclusion")
        coords=streets[streetName]
        lines=split(LineString(coords),grownBoundary1)
        # print("    "+str(len(lines))+" line segments are inside the first grown boundary")
        for line in lines:
            print("LINES:"+str(line.coords[0])+":"+str(line.coords[-1]))
            lstrt = line.coords[0]
            lstop = line.coords[-1]
            dist = Point(line.coords[0]).distance(Point(line.coords[-1]))
            if line.within(grownBoundary3) or \
               (line.within(grownBoundary2) and dist > 0.0006):   # at or just outside and longer than about 50 meters
                streetsToAdd.setdefault(streetName,[]).append(line.coords) # allow individual segments / multiple crossings
        # print("    "+str(len(streetsToAdd[streetName]))+" of those segments are within the second grown boundary and will be included.")

    # 3. send the results to sartopo

    # add a 'results' folder if not already found
    fid=None
    folders=sts.getFeatures("Folder",timeout=60)
    # for folder in folders:
    #     print("---FOLDER---")
    #     print(json.dumps(folder,sort_keys=True,indent=3))
    boundaryName=boundaryShape['properties']['title']
    for folder in folders:
        if folder['properties']['title']==boundaryName:
            fid=folder['id']
            break
    if fid is None:
        fid=sts.addFolder(boundaryName)
    
    # move boundary shape to its zone folder
    sts.editObject(id=boundaryShape['id'],properties={'folderId':fid})

    #  lump all objects into one large 'save' API request, using 'queue' argument
    print(str(len(streetsToAdd))+" streets are at least partially covered by "+boundaryName+":")
    for streetName in streetsToAdd.keys():
        segs=streetsToAdd[streetName]
        print("  adding "+streetName+" ("+str(len(segs))+" segments)")
        for seg in segs:
            if streetName in debugStreetNameList:
                print("    "+streetName+": adding line "+str(seg))
            # as lines:
            # result=sts.addLine(streetsToAdd[streetName],streetName+".out",width=8,opacity=0.5,color='#0000FF',folderId=fid)
            # as line assignments:
            # result=sts.addLineAssignment(letter=streetName+".la",points=streetsToAdd[streetName],folderId=fid)
            # as buffer assignments:
            letter=streetName
            if 'UNNAMED' in streetName or 'STATE HIGHWAY' in streetName:
                letter=None
                if ' RAMP' in streetName:
                    continue # reduce clutter: don't add assignments for ramps
            elif 'INTERSTATE' in streetName:
                continue # reduce clutter: don't add assignments for interstates
            elif ':' in streetName:
                letter=streetName[0:streetName.index(':')] # trim multi-segment suffixes
            # result=sts.addAreaAssignment(letter=letter,points=list(LineString(seg).buffer(0.0001).exterior.coords),folderId=fid,queue=True)
            result=sts.addAreaAssignment(letter=letter,points=list(LineString(seg).buffer(0.0001).exterior.coords),folderId=fid)
            print("  "+streetName+":"+str(result))
    # sts.flush(timeout=60)

# sts.addMarker(lat=39,lon=-120,title="a",queue=True)
# sts.addMarker(lat=39.001,lon=-120.001,title="b",queue=True)
# sts.flush()

# three-vertex-centerline buffer test shape, entirely inside shape 'e3':
# {"properties":{"title":"buf1","description":"","folderId":null,"gpstype":"TRACK","stroke-width":2,"stroke-opacity":1,"stroke":"#FF0000","pattern":"solid"},"geometry":{"coordinates":[[[-119.3368561590181,37.96112666548135],[-119.26419088810952,37.89948559193528],[-119.21205461142533,37.96117000752221],[-119.21203546684448,37.96118513325123],[-119.21201043790118,37.96119333133232],[-119.21198333502517,37.96119335368434],[-119.2119582843836,37.96118519690443],[-119.21193909970961,37.961170102785964],[-119.21192870169588,37.961150369268296],[-119.21192867334575,37.96112900059819],[-119.21193901897527,37.96110924996199],[-119.26412407756902,37.899367043360144],[-119.26414140714591,37.899352897377135],[-119.26416395072032,37.899344491555986],[-119.26418880362515,37.89934290896174],[-119.26421276364351,37.89934835350702],[-119.2642327436041,37.89936012367826],[-119.33701716743222,37.96110233608887],[-119.3370305399595,37.96111879947132],[-119.33703572610682,37.9611379171178],[-119.33703206500518,37.96115725287176],[-119.33702002318752,37.961174342785185],[-119.33700113513875,37.96118700909829],[-119.24224405506062,38.00448385991809],[-119.24221840596034,38.00449076034439],[-119.24219135800698,38.00448940127205],[-119.24216702900625,38.0044799896071],[-119.24214912282795,38.004463958187536],[-119.24214036552543,38.00444374764827],[-119.24214209031858,38.004422434858675],[-119.2421540346233,38.004403264498116],[-119.24217438002746,38.00438915508298],[-119.3368561590181,37.96112666548135]]],"type":"Polygon"}}
