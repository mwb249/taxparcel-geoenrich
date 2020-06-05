# Tax Parcel Geoenrich

Tax Parcel Geoenrich is a Python module that automates the process of downloading and enriching openly available 
geospatial data. Out of the box it enriches public tax parcel data with reports exported from the 
[BS&A Assessing/Equalization](https://www.bsasoftware.com/solutions/assessing-property-tax/assessingequalization/) 
application. The result is saved as an ArcGIS geodatabase feature class.

Tax Parcel Geoenrich is designed as a stand-alone script that can be scheduled to run at specific intervals using Cron 
or Windows Task Scheduler. It makes use of the 
[ArcPy site package](https://pro.arcgis.com/en/pro-app/arcpy/get-started/what-is-arcpy-.htm) and 
[ArcGIS API for Python](https://developers.arcgis.com/python/). For that reason, Tax Parcel Geoenrich is required to 
run on a machine that has a licensed installation of Esri's 
[ArcGIS Pro](https://www.esri.com/en-us/arcgis/products/arcgis-pro/overview) or 
[ArcGIS Enterprise](https://enterprise.arcgis.com/en/) software.

## Installation

### Requirements
Because Tax Parcel Geoenrich uses the ArcPy site package, it can only be run on a machine that has a licensed version 
of Esri's ArcGIS Pro or ArcGIS Server (the back-end server software component of ArcGIS Enterprise) installed. The 
installation instructions are Windows OS centric, however, it is possible to run Tax Parcel GeoEnrich from a Linux 
machine with components ArcGIS Server installed. 

### Download Tax Parcel Geoenrich
Download and install [Git](https://git-scm.com/downloads).

Use the Git command line interface (CLI) to download the latest release of Tax Parcel Geoenrich. To do this, open the 
Git CLI and change the working directory to the folder where Tax Parcel Geoenrich script will be stored.
```bash
cd /c/Users/<user>/<python_scripts>
```
Clone the Tax Parcel Geoenrich to the local machine.
```bash
git clone https://github.com/mwb249/taxparcel-geoenrich.git
```
The output should look like this:
```bash
Cloning into 'taxparcel-geoenrich'...
remote: Enumerating objects: 36, done.
remote: Counting objects: 100% (36/36), done.
remote: Compressing objects: 100% (28/28), done.
remote: Total 36 (delta 16), reused 24 (delta 7), pack-reused 0
Unpacking objects: 100% (36/36), done.
```

### Create Python Environment
In order to use the ArcPy site package and the ArcGIS API for Python, you will need to create a cloned environment 
based on the ArcGIS Pro conda environment that is installed with ArcGIS Pro or ArcGIS Enterprise. Click 
[here](https://enterprise.arcgis.com/en/server/latest/publish-services/windows/deploying-custom-python-packages.htm) to 
learn more about deploying custom Python packages using ArcGIS software.

Open the Windows Command Prompt as an Administrator.

Change the working directory to the ArcGIS Python scripts folder.

ArcGIS Server
```bash
cd <install_dir>\ArcGIS\Server\framework\runtime\ArcGIS\bin\Python\Scripts
```
ArcGIS Pro
```bash
cd C:\Program Files\ArcGIS\Pro\bin\Python\Scripts
```

Use conda to clone the default Python environment, giving it a new name.

ArcGIS Server
```bash
conda create --clone arcgispro-py3 --prefix "<install_dir>\ArcGIS\Server\framework\runtime\ArcGIS\bin\Python\envs\taxparcel-geoenrich"
```
ArcGIS Pro
```bash
conda create --clone arcgispro-py3 --prefix "C:\Program Files\ArcGIS\bin\Python\envs\taxparcel-geoenrich"
```
It will take a few minutes to create the environment.

Once the environment is created, activate it to install some additional modules.
```bash
proswap taxparcel-geoenrich
```
Use the requirements.txt file to install additional required modules
```bash
conda install --file C:/Users/<user>/<python_scripts>/taxparcel-geoenrich/requirements.txt
```

## Usage

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)