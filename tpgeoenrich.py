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
from copy import deepcopy
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


def create_tp_service(target_gis_cfg):
    """A function that creates an empty hosted feature service, with the tax parcel geoenrich schema, in the target
    GIS."""

    gis_conn = conn_portal(target_gis_cfg)


def format_pin(row):
    """Formats a Parcel ID Number (PIN) from a BS&A PNUM."""
    pnum = row['pnum']
    relatedpnum = row['relatedpnum']
    try:
        if pd.isna(relatedpnum) or relatedpnum.startswith('70-15-17-6'):
            pin = pnum
        else:
            pin = relatedpnum
        pin = pin.split('-')
        del pin[0]
        pin = ''.join(pin)
    except IndexError:
        pin = None
    return pin


def format_bsaurl(row):
    """Formats a BS&A Online URL Request based on the PNUM."""
    pnum = row['pnum']
    if pd.isna(pnum):
        cvt_code = None
    else:
        pnum_split = pnum.split('-')
        cvt_code = pnum_split[0]
    cvt_id_dict = {'J ': '268', '70': '385', '68': '1655', 'O ': '1637'}
    url_endpoint = 'https://bsaonline.com/SiteSearch/SiteSearchDetails'
    params = {'SearchCategory': 'Parcel+Number',
              'ReferenceKey': pnum,
              'SearchText': pnum,
              'uid': cvt_id_dict[cvt_code]}
    r = requests.Request('GET', url_endpoint, params=params).prepare()
    return r.url


def find_acres_recorded(row):
    """..."""
    legal_desc = row['legaldesc']
    reg_exp = r'(?<! BLDG)(?<! NO)(?<! NO\.)(?<! SEC)(?<! EXC [NEWS])' \
              r' (\d*\.?\d+)' \
              r'(?! APT )(?! ALL )(?! ALSO )(?! AND )(?! AS )' \
              r'(?=\s*A)'
    matches = re.findall(reg_exp, legal_desc)
    a_record = float(matches[-1]) if matches else None
    return a_record


def get_sdf(source_gis, source_gis_cfg, cvt_codes_cfg):
    """..."""

    # Format SQL expression based on CVTs requested in config file
    cvt_list_len = len(cvt_codes_cfg)
    if cvt_list_len > 1:
        cvt_list_tup = tuple(cvt_codes_cfg)
        sql = "CVTTAXCODE IN {}".format(cvt_list_tup)
    elif cvt_list_len == 1:
        sql = "CVTTAXCODE = '{}'".format(cvt_codes_cfg[0])
    else:
        sql = 'CVTTAXCODE = ALL'

    # Query FeatureLayer, return a Spatially Enabled DataFrame containing the CVT's tax parcels
    print('Querying feature layer, returning spatially enabled dataframe...')
    sdf = source_gis.content.get(source_gis_cfg['item_id']).layers[source_gis_cfg['lyr_num']]\
        .query(where=sql, out_sr=source_gis_cfg['projection'], as_df=True)
    return sdf


def update_summary(gis, portal_item):
    """Updates the summary field on the specified Portal item Overview page."""
    flc_item = gis.content.get(portal_item)
    now = datetime.now()
    date = now.strftime('%B %d, %Y')
    time = now.strftime('%I:%M %p')
    snippet = 'The tax parcels were last updated on {} at {}.'.format(date, time)
    flc_item.update(item_properties={'snippet': snippet})
    print('Updated target feature layer collection summary...')


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


def update_target(gis_conn, target_gis_cfg, joined_dataframe):
    """
    Copies the finalized layer to a geodatabase. The feature class will be reprojected, if specified in the config
    file. If a feature service is referencing the feature class, it will be stopped prior to copying features and
    restarted afterwards.
    """

    # Query target feature layer, return necessary fields and dataframe
    print('Querying target feature layer, returning dataframe...')
    target_lyr = gis_conn.content.get(target_gis_cfg['item_id']).layers[target_gis_cfg['lyr_num']]
    target_df = target_lyr.query(out_fields=['PIN', 'REVISIONDATE', 'GlobalID'],
                                 gdb_version=target_gis_cfg['gdb_version'], return_geometry=False,
                                 return_all_records=True, as_df=True)

    # Create Template feature
    template_fset = target_lyr.query(gdb_version=target_gis_cfg['gdb_version'], result_record_count=1)
    template_feature = deepcopy(template_fset.features[0])

    # Create empty lists for adds, updates, and deletes
    add_lst, update_lst, delete_lst = ([] for _ in range(3))

    # Features to add
    add_rows = pd.merge(left=joined_dataframe, right=target_df, how='outer', on='PIN', indicator=True)\
        .loc[lambda x: x['_merge'] == 'left_only']
    for pin in add_rows['PIN']:
        try:
            row_joined = joined_dataframe.loc[joined_dataframe['PIN'] == pin]
            feature = template_feature
            # TODO: Iterate through field mapping list
            feature.attributes['GlobalID'] = None
            # TODO: Update geometry
            add_lst.append(feature)
        except Exception as e:
            print('Exception: {}'.format(e))
            continue
    # TODO: Add features not found in target that are in source (based on PIN)

    # Features to update
    overlap_rows = pd.merge(left=joined_dataframe, right=target_df, how='inner', on='PIN')
    for pin in overlap_rows['PIN']:
        try:
            row_joined = joined_dataframe.loc[joined_dataframe['PIN'] == pin]
            row_target = target_df.loc[target_df['PIN'] == pin]
            # Update feature if revision dates do not match
            if row_joined['REVISIONDATE'] != row_target['REVISIONDATE']:
                feature = template_feature
                # TODO: Iterate through field mapping list
                feature.attributes['GlobalID'] = row_target['GlobalID']
                # TODO: Update geometry
                update_lst.append(feature)
        except Exception as e:
            print('Exception: {}'.format(e))
            continue

    # Features to delete
    delete_rows = pd.merge(left=joined_dataframe, right=target_df, how='outer', on='PIN', indicator=True)\
        .loc[lambda x: x['_merge'] == 'right_only']
    for pin in delete_rows['PIN']:
        try:
            delete_lst.append(pin)
        except Exception as e:
            print('Exception: {}'.format(e))
            continue

    # Edit target feature layer: adds, updates, and deletes
    target_lyr.edit_features(adds=add_lst, updates=update_lst, deletes=delete_lst,
                             gdb_version=target_gis_cfg['gdb_version'], use_global_ids=True)

    # Update the Portal item summary
    update_summary(gis_conn, target_gis_cfg['item_id'])


def geoenrich(sdf_source, csv_uri):
    """Intakes a tax parcel as an ArcGIS FeatureSet, converts it to a Spatially Enabled DataFrame, modifies fields,
    reprojects, and joins data exported from a BS&A table. The function returns a geoenriched Spatially Enabled
    DataFrame."""

    # Read CSV into Pandas DataFrame
    print('Loading table into Pandas DataFrame...')
    df_export = pd.read_csv(csv_uri)

    # Rename fields using field_lst_tbl
    print('Renaming fields...')
    for field in field_lst_tbl:
        df_export.rename(columns={field[1]: field[0]}, inplace=True)

    # Field calculations
    print('Calculating new fields...')
    sdf_source['acres'] = sdf_source.SHAPE.geom.area / 43560
    df_export['PIN'] = df_export.apply(format_pin, axis=1)
    df_export['bsaurl'] = df_export.apply(format_bsaurl, axis=1)
    df_export['dataexport'] = datetime.now()
    df_export['acresrecorded'] = df_export.apply(find_acres_recorded, axis=1)

    # Join Features to Table
    print('Joining DataFrames...')
    sdf_joined = sdf_source.set_index('PIN').join(df_export.set_index('PIN'), how='left')

    return sdf_joined


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
    source_sdf = get_sdf(source_conn, cfg_source_gis, cfg_cvt_codes)

    # Geoenrich tax parcel features
    joined_sdf = geoenrich(source_sdf, cfg_csv_uri)

    # Create connection to target GIS
    print('Connecting to target GIS...')
    target_conn = conn_portal(cfg_target_gis)

    # Update target feature layer
    update_target(target_conn, cfg_target_gis, joined_sdf)

    print('Script completed successfully!')
