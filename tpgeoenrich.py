"""
When run as a stand-alone script, the tpgeoenrich module requests a zipped shapefile from the website specified in the
config.yml file. The shapefile is joined to a csv file that has been exported from BS&A software. Finally, it is
published to the geodatabase specified in the config.yml file.
"""

import os
import shutil
import tempfile
from zipfile import ZipFile
import arcpy
import requests
import yaml
from datetime import datetime
from arcgis.gis import GIS

# Tax parcel fields
# List order: Shapefile Field Name, New Field Name, New Field Alias
field_lst_fc = [['REVISIONDA', 'REVISIONDATE', 'Revision Date'],
                ['CVTTAXCODE', 'CVTTAXCODE', 'CVT Tax Code'],
                ['CVTTAXDESC', 'CVTTAXDESCRIPTION', 'CVT Name'],
                ['SITEADDRES', 'SITEADDRESS_OC', 'Site Address (OC)'],
                ['SITESTATE', 'SITESTATE', 'Site State'],
                ['ASSESSEDVA', 'ASSESSEDVALUE', 'Assessed Value'],
                ['TAXABLEVAL', 'TAXABLEVALUE', 'Taxable Value'],
                ['NUM_BEDS', 'NUM_BEDS', 'Number of Bedrooms'],
                ['NUM_BATHS', 'NUM_BATHS', 'Number of Bathrooms'],
                ['STRUCTURE_', 'STRUCTURE_DESC', 'Structure Type'],
                ['LIVING_ARE', 'LIVING_AREA_SQFT', 'Living Area']]

# BS&A table conversion
# List order: Field Name, Field Type, Field Alias, Field Length, BS&A Field Name
field_lst_tbl = [['PIN', 'TEXT', 'PIN', 10, None],
                 ['pnum', 'TEXT', 'Parcel Number', 20, 'pnum'],
                 ['neighborhoodcode', 'TEXT', 'Neighborhood Code', 5, 'ecftbl'],
                 ['classcode', 'LONG', 'Class Code', 3, 'propclass'],
                 ['schooltaxcode', 'LONG', 'School Tax Code', 5, 'schooldist'],
                 ['relatedpnum', 'TEXT', 'Related Parcel Number', 20, 'relatedpnum'],
                 ['propstreetcombined', 'TEXT', 'Site Address (RH)', 350, 'propstreetcombined'],
                 ['propaddrnum', 'DOUBLE', 'Site Address Number', None, 'propaddrnum'],
                 ['propstreetname', 'TEXT', 'Site Street Name', 350, 'propstreetname'],
                 ['propcity_RH', 'TEXT', 'Site City', 15, 'propcity'],
                 ['propzip', 'TEXT', 'Site Zip Code', 10, 'propzip'],
                 ['ownername1', 'TEXT', 'Owner Name 1', 180, 'ownername1'],
                 ['ownername2', 'TEXT', 'Owner Name 2', 180, 'ownername2'],
                 ['ownerstreetaddr', 'TEXT', 'Owner Street Address', 350, 'ownerstreetaddr'],
                 ['ownercity', 'TEXT', 'Owner City', 70, 'ownercity'],
                 ['ownerstate', 'TEXT', 'Owner State', 2, 'ownerstate'],
                 ['ownerzip', 'TEXT', 'Owner Zip', 10, 'ownerzip'],
                 ['ownercountry', 'TEXT', 'Owner Country', 90, 'ownercountry'],
                 ['exemptcode', 'TEXT', 'Taxable Status', 50, 'exemptcode'],
                 ['bsaurl', 'TEXT', 'BS&A URL', 350, None],
                 ['dataexport', 'DATE', 'Data Export', None, None]]

# Tax parcel drop fields
dropFields_fc = ['OBJECTID', 'OBJECTID_1', 'SITECITY', 'SITEZIP5', 'Shapearea', 'Shapelen']
dropFields_fc_final = ['OBJECTID', 'PIN_1']

# Final field order
final_field_order = ['pnum', 'PIN', 'relatedpnum', 'REVISIONDATE', 'CVTTAXCODE', 'CVTTAXDESCRIPTION',
                     'propstreetcombined', 'SITEADDRESS_OC', 'propaddrnum', 'propstreetname', 'propcity_RH',
                     'SITESTATE', 'propzip', 'ownername1', 'ownername2', 'ownerstreetaddr', 'ownercity', 'ownerstate',
                     'ownerzip', 'ownercountry', 'exemptcode', 'classcode', 'schooltaxcode', 'neighborhoodcode',
                     'ASSESSEDVALUE', 'TAXABLEVALUE', 'bsaurl', 'NUM_BEDS', 'NUM_BATHS', 'STRUCTURE_DESC',
                     'LIVING_AREA_SQFT', 'dataexport']


def formatpin(pnum, relatedpnum):
    """Formats a Parcel ID Number (PIN) from a BS&A PNUM."""
    try:
        if relatedpnum is None or relatedpnum.startswith('70-15-17-6'):
            p = pnum
        else:
            p = relatedpnum
        p = p.split('-')
        del p[0]
        p = ''.join(p)
    except IndexError:
        p = None
    return p


def formatbsaurl(pnum):
    """Formats a BS&A Online URL Request based on the PNUM."""
    if pnum:
        pnum_split = pnum.split('-')
        cvt_code = pnum_split[0]
    else:
        cvt_code = None
    cvt_id_dict = {'J ': '268', '70': '385', '68': '1655', 'O ': '1637'}
    url_endpoint = 'https://bsaonline.com/SiteSearch/SiteSearchDetails'
    params = {'SearchCategory': 'Parcel+Number',
              'ReferenceKey': pnum,
              'SearchText': pnum,
              'uid': cvt_id_dict[cvt_code]}
    r = requests.Request('GET', url_endpoint, params=params).prepare()
    return r.url


def shpfilename(directory):
    """Reads directory, finds first shapefile in directory, returns the file name and path as a list of values."""
    for file in os.listdir(directory):
        if file.endswith('.shp') or file.endswith('.SHP'):
            return file


def getshpfile(directory, opendata_url):
    """Requests and downloads zipped shapefile from specified open data website, unzips to temporary directory."""
    # Make request to get zipped tax parcel shapefile
    print('Downloading zipped shapefile...')
    resp = requests.get(opendata_url, allow_redirects=True, timeout=10.0)

    # Save zipfile to temporary directory
    zip_name = 'taxparcels.zip'
    zip_path = os.path.join(directory, zip_name)
    zip_file = open(zip_path, 'wb')
    zip_file.write(resp.content)
    zip_file.close()

    # Open the zipfile in READ mode and extract all files to temporary directory
    print('Unzipping...')
    with ZipFile(zip_path, 'r') as zip_file:
        zip_file.extractall(directory)

    # Delete zip file
    os.remove(zip_path)
    return 'Zipfile deleted...'


def cleanup(directory):
    """Attempts to delete directory and all files within it."""
    try:
        shutil.rmtree(directory)
    except OSError as e:
        print("Error: %s : %s" % (directory, e.strerror))
    return 'All temporary files deleted.'


def updatesummary(gis, portal_item):
    """Updates the summary field on the specified Portal item Overview page."""
    flc_item = gis.content.get(portal_item)
    now = datetime.now()
    date = now.strftime('%B %d, %Y')
    time = now.strftime('%I:%M %p')
    snippet = 'The tax parcels were last updated on {} at {}.'.format(date, time)
    flc_item.update(item_properties={'snippet': snippet})
    print('Portal item summary updated...')


def reorderfields(table, out_table, field_order, add_missing=True):
    """
    Reorders fields in input feature class / table
    :table:         input table (fc, table, layer, etc)
    :out_table:     output table (fc, table, layer, etc)
    :field_order:   order of fields (objectid, shape not necessary)
    :add_missing:   add missing fields to end if True (leave out if False)
    -> path to output table
    """
    existing_fields = arcpy.ListFields(table)
    existing_field_names = [field.name for field in existing_fields]

    existing_mapping = arcpy.FieldMappings()
    existing_mapping.addTable(table)

    new_mapping = arcpy.FieldMappings()

    def add_mapping(field_name):
        mapping_index = existing_mapping.findFieldMapIndex(field_name)

        # required fields (OBJECTID, etc) will not be in existing mappings
        # they are added automatically
        if mapping_index != -1:
            field_map = existing_mapping.fieldMappings[mapping_index]
            new_mapping.addFieldMap(field_map)

    # add user fields from field_order
    for f_name in field_order:
        if f_name not in existing_field_names:
            raise Exception("Field: {0} not in {1}".format(f_name, table))

        add_mapping(f_name)

    # add missing fields at end
    if add_missing:
        missing_fields = [f for f in existing_field_names if f not in field_order]
        for f_name in missing_fields:
            add_mapping(f_name)

    # use merge with single input just to use new field_mappings
    arcpy.Merge_management(table, out_table, new_mapping)
    return out_table


def pushtogdb(final_lyr, profile, serv_folder, serv_name, workspace, out_fc_name):
    """
    Copies the finalized layer to a geodatabase. The feature class will be reprojected, if specified in the config
    file. If a feature service is referencing the feature class, it will be stopped prior to copying features and
    restarted afterwards.
    """

    # Create connection to ArcGIS Portal
    print('Establishing connection to ArcGIS Enterprise Portal...')
    gis = GIS(profile=profile)

    # List federated GIS servers, set variable for first server in list
    print('Finding federated GIS servers...')
    gis_server = gis.admin.servers.list()[0]

    # List all services for specified folder
    services = gis_server.services.list(serv_folder)

    # Stop feature service
    service = None
    serv_stop = False
    for serv in services:
        if serv.properties.serviceName == serv_name:
            print('Stopping feature service...')
            service = serv
            serv_stop = service.stop()
            print('Feature service stopped...')

    # Change environment workspace
    arcpy.env.workspace = workspace

    # Clear environment workspace cache
    arcpy.ClearWorkspaceCache_management()

    # Output final_lyr to enterprise geodatabase feature class
    print('Copying features to geodatabase...')
    arcpy.CopyFeatures_management(final_lyr, out_fc_name)

    # Assign domains to fields
    print('Assigning domains to fields...')
    field_domain_lst = [['classcode', 'taxClassDESCR'], ['schooltaxcode', 'taxSchoolDESCR']]
    for domain in field_domain_lst:
        arcpy.AssignDomainToField_management(out_fc_name, domain[0], domain[1])

    print('Altering ObjectID alias...')
    arcpy.AlterField_management(out_fc_name, 'OBJECTID', new_field_alias='OBJECTID')

    # Clear environment workspace cache
    arcpy.ClearWorkspaceCache_management()

    # Restart feature service
    if serv_stop:
        print('Starting feature service...')
        service.start()

    # Update the Portal item summary
    updatesummary(gis, cfg_portal_item)


def geoenrich(directory, overwrite_output, cvt_codes, out_fc_proj, csv_uri):
    """Intakes a tax parcel shapefile, modifies fields, reprojects, then joins to BS&A table data. The final layer is
    copied to a geodatabase feature class."""
    # Set initial environment workspace
    print('Setting environment workspace and settings...')
    arcpy.env.workspace = directory

    # Set environment settings
    arcpy.env.qualifiedFieldNames = False
    arcpy.env.overwriteOutput = overwrite_output

    # Set variable to name of shapefile
    print('Finding shapefile...')
    shp_name = shpfilename(directory)

    # Make a layer from the shapefile
    arcpy.MakeFeatureLayer_management(shp_name, 'parcel_all_lyr')

    # Format SQL expression based on CVTs requested in config file
    print('Correcting field names and aliases...')
    cvt_list_len = len(cvt_codes)
    if cvt_list_len > 1:
        cvt_list_tup = tuple(cvt_codes)
        sql = "CVTTAXCODE IN {}".format(cvt_list_tup)
    elif cvt_list_len == 1:
        sql = "CVTTAXCODE = '{}'".format(cvt_codes[0])
    else:
        sql = 'CVTTAXCODE = ALL'

    # Select tax parcels from requested CVTs in parcel_all_lyr, make new layer from selection
    arcpy.SelectLayerByAttribute_management("parcel_all_lyr", "NEW_SELECTION", sql)
    arcpy.MakeFeatureLayer_management('parcel_all_lyr', 'parcel_sel_lyr')

    # Create temporary geodatabase and set path variables
    gdb_name = 'temp.gdb'
    arcpy.CreateFileGDB_management(directory, gdb_name)
    gdb_path = os.path.join(directory, gdb_name)
    fc_path = os.path.join(gdb_path, 'parcel_fc')

    # Copy features to temporary geodatabase
    arcpy.CopyFeatures_management('parcel_sel_lyr', fc_path)

    # Delete shapefile
    arcpy.Delete_management(shp_name)

    # Change environment workspace
    arcpy.env.workspace = gdb_path

    # Correct field names (feature class)
    for field_prop in field_lst_fc:
        arcpy.AlterField_management('parcel_fc', field_prop[0], field_prop[1], field_prop[2])

    # Delete unnecessary fields (feature class)
    arcpy.DeleteField_management('parcel_fc', dropFields_fc)

    # Modify projection if necessary
    print('Assessing coordinate system...')
    in_spatial_ref = arcpy.Describe('parcel_fc').spatialReference
    out_spatial_ref = arcpy.SpatialReference(out_fc_proj)
    if in_spatial_ref.name == 'Unknown':
        change_proj = False
        print('Could not change projection due to undefined input coordinate system')
    elif in_spatial_ref.name == out_spatial_ref.name:
        change_proj = False
        print('Input and output coordinate systems are the same')
    else:
        change_proj = True
        print('Modifying output coordinate system...')

    # Output final_lyr to enterprise geodatabase feature class
    print('Copying features to geodatabase feature class...')
    if change_proj:
        print('Changing projection, making feature layer...')
        arcpy.Project_management('parcel_fc', 'parcel_fc_proj', out_spatial_ref)
        arcpy.MakeFeatureLayer_management('parcel_fc_proj', 'parcel_lyr')
    else:
        print('Making feature layer...')
        arcpy.MakeFeatureLayer_management('parcel_fc', 'parcel_lyr')

    # Convert CSV to GDB table
    print('Finding table...')
    arcpy.TableToTable_conversion(csv_uri, gdb_path, 'bsa_export')

    # Create empty table to load bsa_export data
    arcpy.CreateTable_management(gdb_path, 'join_table')

    # Add fields from field_lst_tbl
    for field in field_lst_tbl:
        if field[1] == 'TEXT':
            arcpy.AddField_management('join_table', field[0], field[1], field_alias=field[2], field_length=field[3])
        else:
            arcpy.AddField_management('join_table', field[0], field[1], field_alias=field[2])

    # Create FieldMappings object to manage merge output fields
    field_mappings = arcpy.FieldMappings()

    # Add the target table to the field mappings class to set the schema
    field_mappings.addTable('join_table')

    # Map fields from bsa_export table
    for field in field_lst_tbl:
        if field[4] is not None:
            fld_map = arcpy.FieldMap()
            fld_map.addInputField('bsa_export', field[4])
            # Set name of new output field
            field_name = fld_map.outputField
            field_name.name, field_name.type, field_name.aliasName = field[0], field[1], field[2]
            fld_map.outputField = field_name
            # Add output field to field mappings object
            field_mappings.addFieldMap(fld_map)

    # Append the bsa_export data into the join_table
    arcpy.Append_management('bsa_export', 'join_table', schema_type='NO_TEST', field_mapping=field_mappings)

    # Create expressions for field calculations
    pin_exp = 'formatpin(!PNUM!, !RELATEDPNUM!)'
    bsa_url_exp = 'formatbsaurl(!PNUM!)'
    data_export_exp = 'datetime.now()'

    # Calculate fields
    print('Calculating fields...')
    arcpy.CalculateField_management('join_table', 'PIN', pin_exp, 'PYTHON3')
    arcpy.CalculateField_management('join_table', 'BSAURL', bsa_url_exp, 'PYTHON3')
    arcpy.CalculateField_management('join_table', 'DATAEXPORT', data_export_exp, 'PYTHON3')

    # Join parcel_lyr to bsa_export table
    print('Joining table to parcel layer...')
    arcpy.AddJoin_management('parcel_lyr', 'PIN', 'join_table', 'PIN')

    # Reorder fields
    print('Reordering fields...')
    arcpy.CopyFeatures_management('parcel_lyr', 'parcel_fc_join')
    reorderfields('parcel_fc_join', 'parcel_fc_ordered', final_field_order)
    arcpy.DeleteField_management('parcel_fc_ordered', dropFields_fc_final)
    arcpy.MakeFeatureLayer_management('parcel_fc_ordered', 'final_lyr')

    # Copy to geodatabase
    pushtogdb('final_lyr', cfg_profile, cfg_serv_folder, cfg_serv_name, cfg_workspace, cfg_out_fc_name)

    # Delete temporary layers and temporary file geodatabase
    print('Deleting temporary layers...')

    arcpy.Delete_management(r"'parcel_lyr';'bsa_export';'join_table';'final_lyr'")
    arcpy.Delete_management(gdb_path)

    # Clear environment workspace cache
    arcpy.ClearWorkspaceCache_management()

    return 'Successfully published feature class!'


if __name__ == "__main__":
    # Set current working directory
    cwd = os.getcwd()

    # Open config file
    with open(cwd + '/config.yml', 'r') as yaml_file:
        cfg = yaml.load(yaml_file, Loader=yaml.FullLoader)

    # Set variables based on values from config file
    cfg_profile = cfg['webgis']['profile']
    cfg_serv_folder = cfg['webgis']['serv_folder']
    cfg_serv_name = cfg['webgis']['serv_name']
    cfg_portal_item = cfg['webgis']['portal_item']
    cfg_opendata_url = cfg['opendata_url']
    cfg_workspace = cfg['gis_env']['workspace']
    cfg_overwrite_output = cfg['gis_env']['overwrite_output']
    cfg_out_fc_name = cfg['gis_env']['out_fc_name']
    cfg_out_fc_proj = cfg['gis_env']['out_fc_proj']
    cfg_cvt_codes = cfg['cvt_codes']
    cfg_csv_uri = cfg['csv_uri']

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    # Make request to get zipped tax parcel shapefile
    print(getshpfile(temp_dir, cfg_opendata_url))

    # GeoEnrich requested tax parcel data, publish as a new feature class in a geodatabase
    print(geoenrich(temp_dir, cfg_overwrite_output, cfg_cvt_codes, cfg_out_fc_proj, cfg_csv_uri))

    # Cleanup temporary files
    print(cleanup(temp_dir))
