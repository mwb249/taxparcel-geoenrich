# Tax Parcel Geoenrich

Tax Parcel Geoenrich is a Python module that automates the process of downloading and enriching openly available 
geospatial data. Out of the box it enriches public tax parcel data with reports exported from the 
[BS&A Assessing/Equalization](https://www.bsasoftware.com/solutions/assessing-property-tax/assessingequalization/) 
application. The result is saved as an ArcGIS geodatabase feature class.

Tax Parcel Geoenrich is designed as a stand-alone script that can be scheduled to run at specific intervals using Cron 
or Windows Task Scheduler. It makes use of the 
[ArcPy site package](https://pro.arcgis.com/en/pro-app/arcpy/get-started/what-is-arcpy-.htm) and 
[ArcGIS API for Python](https://developers.arcgis.com/python/). For that reason, Tax Parcel Geoenrich is required to 
run on a machine that has a licensed installation of Esri 
[ArcGIS Pro](https://www.esri.com/en-us/arcgis/products/arcgis-pro/overview) or 
[ArcGIS Enterprise](https://enterprise.arcgis.com/en/) software.

## Installation

### Requirements
Tax Parcel Geoenrich uses the ArcPy site package and it can only be run on a machine that has a licensed version 
of Esri ArcGIS Pro or ArcGIS Server (the back-end server software component of ArcGIS Enterprise) installed. The 
installation instructions are Windows OS centric, however, it is possible to run Tax Parcel GeoEnrich from a Linux 
machine that has ArcGIS Server installed. 

### Download Tax Parcel Geoenrich
Download and install [Git](https://git-scm.com/downloads).

Use the Git command line interface (CLI) to download the latest release of Tax Parcel Geoenrich. To do this, open the 
Git CLI and change the working directory to the folder where the Tax Parcel Geoenrich files will be stored.
```bash
cd /c/Users/<user>/<python_scripts>
```
Clone the latest version of Tax Parcel Geoenrich to the local machine.
```bash
git clone https://github.com/mwb249/taxparcel-geoenrich.git
```
The output should look something like this:
```bash
Cloning into 'taxparcel-geoenrich'...
remote: Enumerating objects: 36, done.
remote: Counting objects: 100% (36/36), done.
remote: Compressing objects: 100% (28/28), done.
remote: Total 36 (delta 16), reused 24 (delta 7), pack-reused 0
Unpacking objects: 100% (36/36), done.
```
You can close the Git CLI.

### Create Python Environment
In order to use the ArcPy site package and the ArcGIS API for Python, you will need to create a cloned Python 
environment based on the ArcGIS Pro conda environment that comes installed with ArcGIS Pro or ArcGIS Enterprise. Click 
[here](https://enterprise.arcgis.com/en/server/latest/publish-services/windows/deploying-custom-python-packages.htm) to 
learn more about deploying custom Python packages using ArcGIS software.

Open the Windows Command Prompt as an Administrator.

Change the working directory to the ArcGIS Python scripts folder. This will be slightly different depending on if you 
are using Tax Parcel Geoenrich with ArcGIS Pro or ArcGIS Server.

ArcGIS Server:
```bash
cd <install_dir>\ArcGIS\Server\framework\runtime\ArcGIS\bin\Python\Scripts
```
ArcGIS Pro:
```bash
cd C:\Program Files\ArcGIS\Pro\bin\Python\Scripts
```
Use conda to clone the default Python environment, giving it a new name. Again, the path will be different depending 
on an ArcGIS Pro or ArcGIS Server installation.

ArcGIS Server:
```bash
conda create --clone arcgispro-py3 --prefix "<install_dir>\ArcGIS\Server\framework\runtime\ArcGIS\bin\Python\envs\taxparcel-geoenrich"
```
ArcGIS Pro:
```bash
conda create --clone arcgispro-py3 --prefix "C:\Program Files\ArcGIS\Pro\bin\Python\envs\taxparcel-geoenrich"
```
It will take a few minutes to create the new environment.

Once the environment is created, activate it, then update the environment and install the PyYAML package.
```bash
proswap taxparcel-geoenrich
conda update --all
conda install -y pyyaml
```

### Secure Your *ArcGIS Enterprise Portal* Credentials
Tax Parcel Geoenrich uses the ```profile``` parameter when connecting to a Web GIS. Creating a profile stores all the 
authorization credentials (except the password) in the user's home directory in an unencrypted config file named 
```.arcgisprofile```. The password is stored in an OS specific password manager through the keyring Python module. More 
information can be found 
[here](https://developers.arcgis.com/python/guide/working-with-different-authentication-schemes/#Storing-your-credentials-locally).

If necessary, reopen the Windows Command Prompt and change the working directory to the ArcGIS Python scripts folder.

Activate the taxparcel-geoenrich Python environment.
```bash
proswap taxparcel-geoenrich
```
Open a Python Shell.
```bash
python
```
You should see a Python Prompt: ```>>>```

Run the following commands in the Python Prompt, replace the GIS parameters with your own.
```python
from arcgis.gis import GIS
GIS('https://gis.someportal.com/portal', 'some_username', 'some_password', profile='new_profile_name')
```
The output should look something like this:
```
GIS @ https://gis.indtwp.com/portal version:5.1
```
Use the ```exit()``` command to close out of the Python Prompt.

### Input Your Configuration Settings
Browse to the directory where you downloaded *Tax Parcel Geoenrich* and right-click on ```config.example.yml```. Create 
 a copy of the file and name the copy, ```config.yml```.

Right-click on ```config.yml``` and click *Open with...*, choose a text editor (*Notepad* or *Notepad++* work fine).

### Setup Windows Task Scheduler
Windows Task Scheduler can be used to set the script to run at a frequency of your choice. If the output feature class 
exists in the geodatabase, it will be overwritten each time the script runs.
1. Open Windows *Task Scheduler*.
2. Click Action > Create Task and name the task.
3. Click the *Actions* tab and click New.
4. Set Action to Start a Program.
5. Browse to the location of your Python 3 environment
    - ArcGIS Server:
    ```
    <install_dir>\ArcGIS\Server\framework\runtime\ArcGIS\bin\Python\envs\taxparcel-geoenrich\python.exe
    ```
    - ArcGIS Pro:
    ```
    C:\Program Files\ArcGIS\Pro\bin\Python\envs\taxparcel-geoenrich\python.exe
    ```
6. In the Add arguments text box, type the name of the script: ```tpgeoenrich.py```.
7. In the Start in text box, type the path to the folder where your script is located and click OK.
8. Click the *Triggers* tab, click New, and set a schedule for your task.
9. Click OK.

### Updating Tax Parcel Geoenrich to the Latest Version
To update Tax Parcel Geoenrich to the latest version, open the Git CLI, change the working directory to the folder 
where the Tax Parcel Geoenrich is located, and run the Git pull command. This will update the script and other 
associated files while leaving your config file in place.
```bash
git pull
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](https://choosealicense.com/licenses/mit/)