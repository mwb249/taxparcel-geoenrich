"""
When run as a stand-alone script, the tpgeoenrich module requests a zipped shapefile from the website specified in the
config.yml file. The shapefile is joined to a csv file that has been exported from BS&A software. Finally, it is
published to the geodatabase specified in the config.yml file.
"""

import os
import logging
import yaml
import requests
import tempfile
import shutil
from zipfile import ZipFile
import arcpy

# Logging
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

# Set current working directory
cwd = os.getcwd()

# Open config file
with open(cwd + '/config.yml', 'r') as yaml_file:
    cfg = yaml.load(yaml_file, Loader=yaml.FullLoader)

field_lst = [['REVISIONDA', 'REVISIONDATE', 'Revision Date'],
             ['CVTTAXCODE', 'CVTTAXCODE', 'CVT Tax Code'],
             ['CVTTAXDESC', 'CVTTAXDESCRIPTION', 'CVT Name'],
             ['SITEADDRES', 'SITEADDRESS', 'Site Address'],
             ['SITECITY', 'SITECITY', 'Site City'],
             ['SITESTATE', 'SITESTATE', 'Site State'],
             ['SITEZIP5', 'SITEZIP5', 'Site Zip 5'],
             ['ASSESSEDVA', 'ASSESSEDVALUE', 'Assessed Value'],
             ['TAXABLEVAL', 'TAXABLEVALUE', 'Taxable Value'],
             ['NUM_BEDS', 'NUM_BEDS', 'Number of Bedrooms'],
             ['NUM_BATHS', 'NUM_BATHS', 'Number of Bathrooms'],
             ['STRUCTURE_', 'STRUCTURE_DESC', 'Structure Type'],
             ['LIVING_ARE', 'LIVING_AREA_SQFT', 'living Area']]

dropFields = ['OBJECTID', 'OBJECTID_1', 'Shapearea', 'Shapelen']


def formatpin(pnum, relatedpnum):
    """Format PIN from PNUM"""
    try:
        if relatedpnum is None:
            p = pnum
        else:
            p = relatedpnum
        p = p.split('-')
        del p[0]
        p = ''.join(p)
    finally:
        p = None
    return p


def geoenrich(resp):
    """Takes zipped response from website, joins BS&A table data, then copies to a geodatabase feature class."""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    # Save zipfile to temporary directory
    zip_name = 'taxparcels.zip'
    zip_path = os.path.join(temp_dir, zip_name)
    zip_file = open(zip_path, 'wb')
    zip_file.write(resp.content)
    zip_file.close()

    # Open the zipfile in READ mode and extract all files to temporary directory
    with ZipFile(zip_path, 'r') as zip_file:
        zip_file.extractall(temp_dir)
    os.remove(zip_path)

    # Set environment settings
    arcpy.env.workspace = temp_dir
    arcpy.env.qualifiedFieldNames = False
    arcpy.env.overwriteOutput = cfg['gis_env']['overwrite_output']

    # TODO: Pull shapefile name from directory

    # Make a layer from the feature class (shapefile)
    arcpy.MakeFeatureLayer_management('OC_Tax_Parcels__Public_.shp', 'parcel_all_lyr')

    # Format SQL expression
    cvt_list_len = len(cfg['cvt_codes'])

    if cvt_list_len > 1:
        cvt_list_tup = tuple(cfg['cvt_codes'])
        sql = "CVTTAXCODE IN {0}".format(cvt_list_tup)
    elif cvt_list_len == 1:
        sql = "CVTTAXCODE = '{0}'".format(cfg['cvt_codes'][0])
    else:
        sql = 'CVTTAXCODE = ALL'

    # Select tax parcels from requested CVTs in parcel_all_lyr, make new layer from selection
    arcpy.SelectLayerByAttribute_management("parcel_all_lyr", "NEW_SELECTION", sql)
    arcpy.MakeFeatureLayer_management('parcel_all_lyr', 'parcel_sel_lyr')

    # Create temporary geodatabase and set workspace
    gdb_name = 'temp.gdb'
    arcpy.CreateFileGDB_management(temp_dir, gdb_name)
    gdb_path = os.path.join(temp_dir, gdb_name)
    fc_path = os.path.join(gdb_path, 'parcel_fc')

    # Copy features to TEMP GDB
    arcpy.CopyFeatures_management('parcel_sel_lyr', fc_path)

    # Delete shapefile
    arcpy.Delete_management('OC_Tax_Parcels__Public_.shp')

    # Change environment workspace
    arcpy.env.workspace = gdb_path

    # Correct field names
    for f in field_lst:
        arcpy.AlterField_management('parcel_fc', f[0], f[1], f[2])

    # Delete unnecessary fields
    arcpy.DeleteField_management('parcel_fc', dropFields)

    # Make Parcel layer
    arcpy.MakeFeatureLayer_management('parcel_fc', 'parcel_lyr')

    # Convert CSV to GDB table
    arcpy.TableToTable_conversion(cfg['csv']['uri'], gdb_path, 'bsa_export')

    # Add field to bsa_export table
    arcpy.AddField_management('bsa_export', 'PIN', "TEXT", field_alias='PIN', field_length=10,
                              field_is_nullable="NULLABLE")

    expression = 'formatpin(!PNUM!, !RELATEDPNUM!)'

    # Calculate field
    arcpy.CalculateField_management('bsa_export', 'PIN', expression, 'PYTHON3')

    # Join parcel_lyr to bsa_export table
    arcpy.AddJoin_management('parcel_lyr', 'PIN', 'bsa_export', 'PIN')

    # Make a new layer with joined data
    arcpy.MakeFeatureLayer_management('parcel_lyr', 'final_lyr')

    # Change environment workspace
    arcpy.env.workspace = cfg['gis_env']['workspace']

    # Copy features to Enterprise GDB
    arcpy.CopyFeatures_management('final_lyr', cfg['gis_env']['out_fc_name'])

    # Delete layers and file geodatabase
    arcpy.Delete_management('parcel_lyr')
    arcpy.Delete_management('bsa_export')
    arcpy.Delete_management('final_lyr')
    arcpy.Delete_management(gdb_path)

    # Clear environment workspace cache
    arcpy.ClearWorkspaceCache_management()

    # Delete temporary directory
    try:
        shutil.rmtree(temp_dir)
    except OSError as e:
        print("Error: %s : %s" % (temp_dir, e.strerror))

    return 'Success'


if __name__ == "__main__":
    # Make request to get zipped tax parcel shapefile
    response = requests.get(cfg['opendata_url'], allow_redirects=True, timeout=10.0)

    # GeoEnrich requested tax parcel data, publish as a new feature class in a geodatabase
    status = geoenrich(response)

    # Output final status
    print(status)
