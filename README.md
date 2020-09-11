Short demo video using the 9-11-2020 commit:

[![](http://img.youtube.com/vi/nPBtIBolm6k/0.jpg)](http://www.youtube.com/watch?v=nPBtIBolm6k "evacStreetImportPrelim")

# sartopo_streets_in_polygon
Create buffer assignments for all roads that are at least partially covered by a given polygon; intended for evacuation purposes, where an evacuation shape is specified, and buffer assignments are needed for all roads at least partially inside that evacuation shape

This repository will probably go away and the code will be rolled into a different project.  This repository is only for development work.

#  concept:
   Start with a repository of street data - not necessarily sartopo objects,
     each item in the repository should contain a street name and a list
     of vertices; probably easiest to get these from GIS data, but, could
     also be parsed directly from sartopo objects, either from API calls
     or from a pre-existing json/gpx/kml file
   1. read the bounding polygon as a Shape object using the API
          (sts.getFeatures("Shape") then find the one with the specified name)
   2. iterate over street data, and use python Shapely module to select streets
        that are at least partially covered by the bounding polygon
   3. send those streets to sartopo; there are some possibilities:
       - api/v0/geodata/buffer : specify centerline and width
       - api/v1/Shape : specify polygon coordinates
       - api/v0/save : specify multiple polygon objects in one API call


