"""


"""

import logging
import os
import yaml
from arcgis import GIS
import csv
# import pyodbc

# Logging
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

# Directories
cwd = os.getcwd()

# Open config file
with open(cwd + '/config.yml', 'r') as yaml_file:
    cfg = yaml.load(yaml_file)

# Connect to WebGIS
gis = GIS(cfg['webgis']['portal'], cfg['webgis']['user'], cfg['webgis']['password'])

# Assign variable to tax parcel feature layer
fl_tax_parcels = gis.content.get(cfg['fservice']['pull_url']).layers[cfg['fservice']['pull_layer']]

# TODO: create method to work with multiple CVTs, arrays in YAML...?

# Query tax parcel layer, return feature dataset for necessary municipalities
fset_cvt_parcels = fl_tax_parcels.query(where="CVTTAXCODE IS '" + cfg['cvt_code'] + "'")

# # Create connection to MS SQL Server database
# db_details = {
#  'server': cfg['db']['instance'],
#  'database': cfg['db']['database'],
#  'username': cfg['db']['user'],
#  'password': cfg['db']['password']
#  }
# connect_string = 'DRIVER={{ODBC Driver 13 for SQL Server}};SERVER={server};PORT=1443; DATABASE={database};' \
#                  'UID={username};PWD={password})'.format(**db_details)
# conn = pyodbc.connect(connect_string)
#
# # Execute SQL query
# cursor = conn.cursor()
# cursor.execute('SELECT * FROM db_name.Table')
#
# # Test print query
# for row in cursor:
#     print(row)

# Open CSV
parcel_tbl = csv.DictReader(open(cwd + '/parcel_export.csv'))
agency_codes = {rows['agency_code']: rows['city_desc'] for rows in parcel_tbl}

# TODO: Join MS SQL query results to fset_cvt_parcels table.

# TODO: Overwrite existing feature service using joined data.

if __name__ == "__main__":
    pass
