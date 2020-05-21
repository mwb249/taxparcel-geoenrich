"""


"""

import logging
import os
import yaml
from arcgis import GIS

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
fl_tax_parcels = gis.content.get(cfg['fservice']['url']).layers[cfg['fservice']['layer']]

# TODO: create method to work with multiple CVTs, arrays in YAML...?

# Query tax parcel layer, return feature dataset for necessary municipalities
fset_cvt_parcels = fl_tax_parcels.query(where="CVTTAXCODE IS '" + cfg['cvt_code'] + "'")


def enrich():
    """

    """


if __name__ == "__main__":
    enrich()
