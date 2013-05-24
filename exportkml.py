import arcpy, os, csv, zipfile, shutil
import os.path

# Set path to the root folder for input data
rootDir = arcpy.GetParameterAsText(0)

# Input variables
inputDir = rootDir + "data\\"
outputDir = rootDir + "output\\"
baseDir = inputDir + "Maptiles\\"

arcpy.env.workspace = outputDir

# Read header.kml file into string
headerPath = os.path.join(inputDir, "header.kml")
headerFile = open(headerPath, "r")
headerStr = headerFile.read()
headerFile.close()


# Read the Species Nomenclature Translation and Model Code List
# (Copied from old script)
csvname="%sspp_name_synonyms.csv" %(inputDir)
synonyms_file = csv.reader(csvname)
f = open(csvname, 'rb')
reader = csv.reader(f)
csvheaders = reader.next()
column = {}
for h in csvheaders:
    column[h] = []
for row in reader:
   for h, v in zip(csvheaders, row):
     column[h].append(v)
New_sp_names = column['Correct name']
all_sp_codes = column['species codes']

# Start iterating through all the model code values
sp_temps = range(1,1087)
for sp_temp in sp_temps:
##    if (sp_temp == 5):
##        break
##    else:
        # Create a proper 4-digit code for the species id
    	sp_code = str(sp_temp)
    	lspcode = len(sp_code)
        new_sp_code = (4-lspcode)*'0' + sp_code

        # Set up veriables for the response zone files
        zoneDirPath = os.path.join(inputDir, "spp_data", new_sp_code)
        zoneName = "Response Zone " + new_sp_code
        zoneKML = zoneName + ".kml"
        zoneKMLPath = os.path.join(outputDir, zoneKML)
        zoneKMZPath = os.path.join(outputDir, zoneName + ".kmz")
        zoneFCPath = os.path.join(zoneDirPath, "response_zone_" + new_sp_code + ".shp")
        zoneRefLayer = os.path.join(inputDir, "reflyrs", "ref_lyr_response_zone_kml.lyr")

        if os.path.exists(zoneDirPath):
            # Create a feature layer for the response zone and apply the preset symbology
            arcpy.MakeFeatureLayer_management(zoneFCPath, zoneName)
            arcpy.ApplySymbologyFromLayer_management(zoneName, zoneRefLayer)

            # Export the zone layer to KML/KMZ
            composite = 'NO_COMPOSITE'
            clamped = 'CLAMPED_TO_GROUND'
            arcpy.LayerToKML_conversion(zoneName, zoneKMZPath, '', composite, '', '', '', clamped)

            # Create a new kml document and start writing to it
            outputFile = open(zoneKMLPath, "w")
            outputFile.write(headerStr)

            # Unzip the zone kmz generated previously
            zoneZipfile = zipfile.ZipFile(zoneKMZPath)
            zoneZipfile.extractall(outputDir)


            # Read the doc.kml from the zone.kmz
            zoneDocPath = os.path.join(outputDir, "doc.kml")
            zoneDocFile = open(zoneDocPath, "r")
            zoneDocStr = zoneDocFile.read()

            # Extract only the <Document></Document> section of the the output
            zoneDocIndex1 = zoneDocStr.find("<Document")
            zoneDocIndex2 = zoneDocStr.find("</Document>")

            # Write the extracted text to the final kml
            outputFile.write(zoneDocStr[zoneDocIndex1:zoneDocIndex2 + 11])

            # Clean up files
            zoneDocFile.close()
            zoneZipfile.close()
            os.remove(zoneDocPath)
            os.remove(zoneKMZPath)


            # --- START PROCESSING POINTS FILE --- #

            # Get the species name from the reference csv file
            nf = 0
            try:
          		sp_index = all_sp_codes.index(sp_code)
            except ValueError:
        		nf = 1
        		sp_name = "Unknown"

            # Only start processing the points shapefile if the species names finds a match
            if nf == 0:

                # Set up variables for the points data
                sp_name = New_sp_names[sp_index]
                pointsDirPath = os.path.join(inputDir, "common data")
                pointsName = "Species Points " + new_sp_code
                pointsKMLPath = os.path.join(outputDir, pointsName + ".kml")
                pointsKMZPath = os.path.join(outputDir, pointsName + ".kmz")
                pointsFCPath = os.path.join(pointsDirPath, "corrected_CO_data4_merged_and_filtered.shp")
                pointsRefLayer = os.path.join(inputDir, "reflyrs", "ref_lyr_BP.lyr")

                # Build the definition query for the species points
                defQuery = """ "sp_name" = '%s' """ %(sp_name)

                # Create a feature layer for the points and apply the preset symbology
                arcpy.MakeFeatureLayer_management(pointsFCPath, pointsName, defQuery)
                arcpy.ApplySymbologyFromLayer_management(pointsName, pointsRefLayer)
                pointsCount = arcpy.GetCount_management(pointsName)

                # Only create points.kml if there are matching points in the shapefile
                if pointsCount > 0:

                    # Export the points layer to KML/KMZ
                    composite = 'NO_COMPOSITE'
                    clamped = 'CLAMPED_TO_GROUND'
                    arcpy.LayerToKML_conversion(pointsName, pointsKMZPath, '', composite, '', '', '', clamped)

                    # Unzip the points kmz generated
                    pointsZipfile = zipfile.ZipFile(pointsKMZPath)
                    pointsZipfile.extractall(outputDir)

                    # Read the doc.kml from the points.kmz
                    pointsDocPath = os.path.join(outputDir, "doc.kml")
                    pointsDocFile = open(pointsDocPath, "r")
                    pointsDocStr = pointsDocFile.read()

                    # Modify the path to the PNG symbol to be in Maptiles subdirectory
                    symbolIndex = pointsDocStr.find("Layer0_Symbol")
                    pointsDocStr = pointsDocStr[:symbolIndex] + "Maptiles/" + pointsDocStr[symbolIndex:]

                    # Extract only the <Document></Document> section of the the output
                    pointsDocIndex1 = pointsDocStr.find("<Document")
                    pointsDocIndex2 = pointsDocStr.find("</Document>")

                    # Write the extracted text to the final kml
                    outputFile.write(pointsDocStr[pointsDocIndex1:pointsDocIndex2 + 11])

                    # Clean up files
                    pointsDocFile.close()
                    pointsZipfile.close()
                    os.remove(pointsDocPath)
                    os.remove(pointsKMZPath)


            # --- START PROCESSING BASE LAYERS --- #

            # Get all reference to all the files and folders in the Maptile source folder
            base = os.walk(baseDir)
            (root, dirs, files) = base.next()
            for dir in dirs:
                # Read the doc.kml from each pre-render Maptile subdirectory
                docPath = os.path.join(root, dir, "doc.kml")
                docFile = open(docPath, "r")
                docStr = docFile.read()

                # Extract only the <Document></Document> section of the the output
                docIndex1 = docStr.find("<Document")
                docIndex2 = docStr.find("</Document>")

                # Write the extracted text to the final kml
                outputFile.write(docStr[docIndex1:docIndex2 + 11])
                docFile.close()

            # Write the final closing KML tags and close out the file.
            outputFile.write("\n</Folder>")
            outputFile.write("\n</kml>")
            outputFile.close()


            # -- START ZIPPING UP FILES --- #

            # Create a zip file of the results in the same directory as the script and prepare to write
            zoneZipName = os.path.join(outputDir, zoneName)
            zoneZipPath = os.path.join(outputDir, zoneName + ".zip")
            shutil.make_archive(zoneZipName, "zip", inputDir, "Maptiles")

            # Start appending to the existing zip file
            zoneZipFile = zipfile.ZipFile(zoneZipPath, 'a', zipfile.ZIP_DEFLATED)

            # Write the final KML file to the root of the zip file
            zoneZipFile.write(zoneKMLPath, zoneKML)

            # Search for the PNG file created by the points layer if it's available
            pngList = arcpy.ListRasters("*","PNG")
            for pngFile in pngList:
                # Zip the png file into the Maptiles subdirectory
                pngRelPath = "Maptiles/" + pngFile
                pngAbsPath = os.path.join(outputDir, pngFile)
                zoneZipFile.write(pngAbsPath, pngRelPath)
                os.remove(pngAbsPath)

            # Close out zip file
            os.remove(zoneKMLPath)
            zoneZipFile.close()