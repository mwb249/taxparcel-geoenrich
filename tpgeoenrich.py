"""
When run as a stand-alone script, the tpgeoenrich module requests a zipped shapefile from the website specified in the
config.yml file. The shapefile is joined to a csv file that has been exported from BS&A software. Finally, it is
published to the geodatabase specified in the config.yml file.
"""

import sys
import os
import requests
import yaml
import re
import pandas as pd
from datetime import datetime
from arcgis.gis import GIS

# Suppress all warnings
if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

# Tax parcel fields
# List order: Shapefile Field Name, New Field Name, New Field Alias
field_lst_fc = [['SITEADDRESS', 'SITEADDRESS_OC', 'Site Address (OC)']]

# BS&A table conversion
# List order: Field Name, Field Type, Field Alias, Field Length, BS&A Field Name
field_lst_tbl = [['pnum', 'Parcels.pnum'],
                 ['neighborhoodcode', 'Parcels.ecftbl'],
                 ['classcode', 'Parcels.propclass'],
                 ['schooltaxcode', 'Parcels.schooldist'],
                 ['relatedpnum', 'ParcelMaster.relatedpnum'],
                 ['propstreetcombined', 'ParcelMaster.propstreetcombined'],
                 ['propaddrnum', 'ParcelMaster.propaddrnum'],
                 ['propstreetname', 'ParcelMaster.propstreetname'],
                 ['propcity_RH', 'ParcelMaster.propcity'],
                 ['propzip', 'TEXT', 'ParcelMaster.propzip'],
                 ['ownername1', 'ParcelMaster.ownername1'],
                 ['ownername2', 'ParcelMaster.ownername2'],
                 ['ownerstreetaddr', 'ParcelMaster.ownerstreetaddr'],
                 ['ownercity', 'ParcelMaster.ownercity'],
                 ['ownerstate', 'ParcelMaster.ownerstate'],
                 ['ownerzip', 'ParcelMaster.ownerzip'],
                 ['ownercountry', 'ParcelMaster.ownercountry'],
                 ['exemptcode', 'Parcels.exemptcode'],
                 ['legaldesc', 'ParcelReadonly.legalDescription']]
# Tax parcel drop fields
dropFields_fc = ['SITECITY', 'SITEZIP5']
dropFields_fc_final = ['OBJECTID', 'PIN_1']

# Final field order
final_field_order = ['pnum', 'PIN', 'relatedpnum', 'REVISIONDATE', 'CVTTAXCODE', 'CVTTAXDESCRIPTION',
                     'propstreetcombined', 'SITEADDRESS_OC', 'propaddrnum', 'propstreetname', 'propcity_RH',
                     'SITESTATE', 'propzip', 'ownername1', 'ownername2', 'ownerstreetaddr', 'ownercity', 'ownerstate',
                     'ownerzip', 'ownercountry', 'exemptcode', 'classcode', 'schooltaxcode', 'neighborhoodcode',
                     'ASSESSEDVALUE', 'TAXABLEVALUE', 'bsaurl', 'NUM_BEDS', 'NUM_BATHS', 'STRUCTURE_DESC',
                     'LIVING_AREA_SQFT', 'dataexport']


def format_pin(pnum, relatedpnum):
    """Formats a Parcel ID Number (PIN) from a BS&A PNUM."""

    try:
        if relatedpnum or relatedpnum.startswith('70-15-17-6'):
            p = pnum
        else:
            p = relatedpnum
        p = p.split('-')
        del p[0]
        p = ''.join(p)
    except IndexError:
        p = None
    return p


def format_bsaurl(pnum):
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


def find_acres_recorded(legal_desc):
    """..."""
    reg_exp = r'(?<! BLDG)(?<! NO)(?<! NO\.)(?<! SEC)(?<! EXC [NEWS])' \
              r' (\d*\.?\d+)' \
              r'(?! APT )(?! ALL )(?! ALSO )(?! AND )(?! AS )' \
              r'(?=\s*A)'
    matches = re.findall(reg_exp, legal_desc)
    a_record = float(matches[-1]) if matches else None
    return a_record


def get_featureset(source_gis, source_gis_cfg, cvt_codes_cfg):
    """..."""
    # Connect to ArcGIS Online and create a tax parcel FeatureLayer object
    print('Connecting to source GIS and getting feature layer...')
    fl_taxparcel = source_gis.content.get(source_gis_cfg['item_id']).layers[source_gis_cfg['lyr_num']]

    # Format SQL expression based on CVTs requested in config file
    cvt_list_len = len(cvt_codes_cfg)
    if cvt_list_len > 1:
        cvt_list_tup = tuple(cvt_codes_cfg)
        sql = "CVTTAXCODE IN {}".format(cvt_list_tup)
    elif cvt_list_len == 1:
        sql = "CVTTAXCODE = '{}'".format(cvt_codes_cfg[0])
    else:
        sql = 'CVTTAXCODE = ALL'

    # Query FeatureLayer, return a FeatureSet containing the CVT's tax parcels
    print('Querying feature layer, returning feature set...')
    fset_taxparcel = fl_taxparcel.query(where=sql)
    return fset_taxparcel


def update_summary(gis, portal_item):
    """Updates the summary field on the specified Portal item Overview page."""
    flc_item = gis.content.get(portal_item)
    now = datetime.now()
    date = now.strftime('%B %d, %Y')
    time = now.strftime('%I:%M %p')
    snippet = 'The tax parcels were last updated on {} at {}.'.format(date, time)
    flc_item.update(item_properties={'snippet': snippet})
    print('Portal item summary updated...')


def conn_portal(webgis_config):
    """Creates connection to ArcGIS Online or an ArcGIS Enterprise Portal."""
    w_gis = None
    try:
        if None in (webgis_config['url'], webgis_config['profile']):
            w_gis = GIS()
        elif webgis_config['profile']:
            w_gis = GIS(profile=webgis_config['profile'])
        else:
            w_gis = GIS(webgis_config['url'], webgis_config['username'], webgis_config['password'])
    except Exception as e:
        print('Error: {}'.format(e))
        print('Exiting script: not able to connect to ArcGIS Online or ArcGIS Enterprise Portal..')
        exit()
    return w_gis


def update_target(gis_conn, source_data):
    """
    Copies the finalized layer to a geodatabase. The feature class will be reprojected, if specified in the config
    file. If a feature service is referencing the feature class, it will be stopped prior to copying features and
    restarted afterwards.
    """

    # Change environment workspace
    arcpy.env.workspace = gis_env_config['workspace']

    # Clear environment workspace cache
    arcpy.ClearWorkspaceCache_management()

    # Delete existing feature class
    if arcpy.Exists(gis_env_config['out_fc_name']):
        fc_path = os.path.join(gis_env_config['workspace'], gis_env_config['out_fc_name'])
        if arcpy.TestSchemaLock(fc_path):
            print('Removing existing {} feature class...'.format(gis_env_config['out_fc_name']))
            arcpy.Delete_management(gis_env_config['out_fc_name'])
        else:
            print('Unable to obtain exclusive schema lock '
                  'on the existing {} feature class...'.format(gis_env_config['out_fc_name']))
            cleanup(directory, gdb_path)
            print('Exiting script: Did not update {}.'.format(gis_env_config['out_fc_name']))
            exit()

    # Output final_lyr to enterprise geodatabase feature class
    print('Copying features to geodatabase...')
    arcpy.CopyFeatures_management(final_lyr, gis_env_config['out_fc_name'])

    # Assign domains to fields
    print('Assigning domains to fields...')
    field_domain_lst = [['classcode', 'taxClassDESCR'], ['schooltaxcode', 'taxSchoolDESCR']]
    for domain in field_domain_lst:
        arcpy.AssignDomainToField_management(gis_env_config['out_fc_name'], domain[0], domain[1])

    print('Altering ObjectID alias...')
    arcpy.AlterField_management(gis_env_config['out_fc_name'], 'OBJECTID', new_field_alias='OBJECTID')

    # Clear environment workspace cache
    arcpy.ClearWorkspaceCache_management()

    # Restart feature service
    if f_serv_status:
        print('Starting feature service...')
        f_serv.start()

    # Update the Portal item summary
    print('Updating feature service summary...')
    update_summary(gis, webgis_config['portal_item'])


def geoenrich(featureset, target_gis_config, csv_uri):
    """Intakes a tax parcel as an ArcGIS FeatureSet, converts it to a Spatially Enabled DataFrame, modifies fields,
    reprojects, and joins data exported from a BS&A table. The function returns a geoenriched Spatially Enabled
    DataFrame."""

    # FeatureSet to Spatially Enabled DataFrame
    print('Converting FeatureSet to Spatially Enabled DataFrame...')
    sdf_source = featureset.sdf

    # Modify projection if necessary
    print("Assessing the DataFrame spatial reference...")
    in_spatial_ref = sdf_source.spatial.sr
    in_spatial_ref = in_spatial_ref['wkid']
    out_spatial_ref = target_gis_config['projection']
    print('DataFrame spatial reference = WKID: {}'.format(in_spatial_ref))
    print('Output spatial reference = WKID: {}'.format(out_spatial_ref))
    # TODO: Update code with correct 'unknown' string
    if in_spatial_ref == 'Unknown':
        change_proj = False
        print('Could not change projection due to undefined input coordinate system')
    elif in_spatial_ref == out_spatial_ref:
        change_proj = False
        print('Input and output coordinate systems are the same')
    else:
        change_proj = True
        print('Modifying output coordinate system...')

    if change_proj:
        print('Reprojecting DataFrame...')
        sdf_source.spatial.project(out_spatial_ref)

    # Read CSV into Pandas DataFrame
    print('Loading table into Pandas DataFrame...')
    export_table = pd.read_csv(csv_uri)

    # Add fields from field_lst_tbl
    for field in field_lst_tbl:
        export_table.rename(columns={field[1]: field[0]}, inplace=True)

    # export_table['PIN'] = format_pin(export_table['pnum'], export_table['relatedpnum'])
    # export_table['bsaurl'] = format_bsaurl(export_table['Parcels.pnum'])
    # export_table['dataexport'] = datetime.now()
    # export_table['acresrecorded'] = find_acres_recorded(export_table['legalDescription'])
    #
    # print('Joining DataFrames...')
    # sdf_source.set_index('PIN').join(export_table.set_index('PIN'))
    #
    # # Calculate Acres field
    # sdf_source['acres'] = sdf_source.SHAPE.geom.get_area('PLANAR', 'ACRES')

    return export_table


if __name__ == "__main__":
    # Set current working directory
    cwd = os.getcwd()

    # Open config file
    with open(cwd + '/config.yml', 'r') as yaml_file:
        cfg = yaml.load(yaml_file, Loader=yaml.FullLoader)

    # Set variables based on values from config file
    cfg_source_gis = cfg['source_gis']
    cfg_target_gis = cfg['target_gis']
    cfg_cvt_codes = cfg['cvt_codes']
    cfg_csv_uri = cfg['csv_uri']

    # Create connection to source GIS
    print('Connecting to source GIS...')
    source_conn = conn_portal(cfg_source_gis)

    # Query FeatureLayer, return FeatureSet
    fset = get_featureset(source_conn, cfg_source_gis, cfg_cvt_codes)

    # Geoenrich tax parcel features
    source_dataframe = geoenrich(fset, cfg_target_gis, cfg_csv_uri)

    # Create connection to target GIS
    print('Connecting to target GIS...')
    target_conn = conn_portal(cfg_target_gis)

    # Update target feature layer
    update_target(target_conn, source_dataframe)

    print('Script completed successfully!')
