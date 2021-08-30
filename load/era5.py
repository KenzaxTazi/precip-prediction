"""
ERA5 reanalysis is downloaded via the Copernicus Data store.

Variables
    Total precipitation (tp) in m/day
"""

import calendar
import datetime
import os
import urllib
import numpy as np
import xarray as xr
import pandas as pd
import ftplib
import cdsapi

import DataDownloader as dd
import LocationSel as ls


def update_cds_monthly_data(
    dataset_name="reanalysis-era5-single-levels-monthly-means",
    product_type="monthly_averaged_reanalysis",
    variables=[
        "geopotential",
        "2m_dewpoint_temperature",
        "angle_of_sub_gridscale_orography",
        "slope_of_sub_gridscale_orography",
        "total_column_water_vapour",
        "total_precipitation",
    ],
    area=[40, 70, 30, 85],
    pressure_level=None,
    path="Data/ERA5/",
    qualifier=None):
    """
    Imports the most recent version of the given monthly ERA5 dataset as a netcdf from the CDS API.

    Inputs:
        dataset_name: str
        prduct_type: str
        variables: list of strings
        pressure_level: str or None
        area: list of scalars
        path: str
        qualifier: str

    Returns: local filepath to netcdf.
    """
    if type(area) == str:
        qualifier = area
        area = ls.basin_extent(area)
        
    now = datetime.datetime.now()

    if qualifier == None:
        filename = (
            dataset_name + "_" + product_type + "_" + now.strftime("%m-%Y") + ".nc"
        )
    else:
        filename = (
            dataset_name
            + "_"
            + product_type
            + "_"
            + qualifier
            +"_"
            + now.strftime("%m-%Y")
            + ".nc"
        )

    filepath = path + filename

    # Only download if updated file is not present locally
    if not os.path.exists(filepath):

        current_year = now.strftime("%Y")
        years = np.arange(1979, int(current_year) + 1, 1).astype(str)
        months = np.arange(1, 13, 1).astype(str)

        c = cdsapi.Client()

        if pressure_level == None:
            c.retrieve(
                "reanalysis-era5-single-levels-monthly-means",
                {
                    "format": "netcdf",
                    "product_type": product_type,
                    "variable": variables,
                    "year": years.tolist(),
                    "time": "00:00",
                    "month": months.tolist(),
                    "area": area,
                },
                filepath,
                
            )
        else:
            c.retrieve(
                "reanalysis-era5-single-levels-monthly-means",
                {   
                    "format": "netcdf",
                    "product_type": product_type,
                    "variable": variables,
                    "pressure_level": pressure_level,
                    "year": years.tolist(),
                    "time": "00:00",
                    "month": months.tolist(),
                    "area": area,
                },
                filepath,
            )

    return filepath


def update_cds_hourly_data(
    dataset_name="reanalysis-era5-pressure-levels",
    product_type="reanalysis",
    variables=["geopotential"],
    pressure_level="200",
    area=[90, -180, -90, 180],
    path="Data/ERA5/",
    qualifier=None):
    """
    Imports the most recent version of the given hourly ERA5 dataset as a netcdf from the CDS API.

    Inputs:
        dataset_name: str
        prduct_type: str
        variables: list of strings
        area: list of scalars
        pressure_level: str or None
        path: str
        qualifier: str

    Returns: local filepath to netcdf.
    """
    now = datetime.datetime.now()

    if qualifier == None:
        filename = (
            dataset_name + "_" + product_type + "_" + now.strftime("%m-%Y") + ".nc"
        )
    else:
        filename = (
            dataset_name
            + "_"
            + product_type
            + "_"
            + now.strftime("%m-%Y")
            + "_"
            + qualifier
            + ".nc"
        )

    filepath = path + filename

    # Only download if updated file is not present locally
    if not os.path.exists(filepath):

        current_year = now.strftime("%Y")
        years = np.arange(1979, int(current_year) + 1, 1).astype(str)
        months = np.arange(1, 13, 1).astype(str)
        days = np.arange(1, 32, 1).astype(str)

        c = cdsapi.Client()

        if pressure_level == None:
            c.retrieve(
                dataset_name,
                {
                    "format": "netcdf",
                    "product_type": product_type,
                    "variable": variables,
                    "year": years.tolist(),
                    "time": "00:00",
                    "month": months.tolist(),
                    "day": days.tolist(),
                    "area": area,
                },
                filepath,
            )
        else:
            c.retrieve(
                dataset_name,
                {
                    "format": "netcdf",
                    "product_type": product_type,
                    "variable": variables,
                    "pressure_level": pressure_level,
                    "year": years.tolist(),
                    "time": "00:00",
                    "month": months.tolist(),
                    "day": days.tolist(),
                    "area": area,
                },
                filepath,
            )

    return filepath



def collect_ERA5(location, minyear, maxyear):
    """ Downloads data from ERA5 for a given location"""
    era5_ds= dd.download_data(location, xarray=True) 

    if type(location) == str:
        loc_ds = ls.select_basin(era5_ds, location)
    else:
        lat, lon = location
        loc_ds = era5_ds.interp(coords={"lon": lon, "lat": lat}, method="nearest")

    tim_ds = loc_ds.sel(time= slice(minyear, maxyear))
    ds = tim_ds.assign_attrs(plot_legend="ERA5") # in mm/day   
    return ds


def gauge_download(station, minyear, maxyear):
    """ 
    Download and format ERA5 data 
    
    Args:
        station (str): station name (capitalised)
    
    Returns
       ds (xr.DataSet): ERA values for precipitation
    """

    all_station_dict = {'Arki':[31.154, 76.964], 'Banjar': [31.65, 77.34], 'Banjar IMD': [31.637, 77.344],  
                'Berthin':[31.471, 76.622], 'Bhakra':[31.424, 76.417], 'Barantargh': [31.087, 76.608], 
                'Bharmaur': [32.45, 76.533], 'Bhoranj':[31.648, 76.698], 'Bhuntar': [31.88, 77.15], 
                'Churah': [32.833, 76.167], 'Dadahu':[30.599, 77.437], 'Daslehra': [31.4, 76.55], 
                'Dehra': [31.885, 76.218], 'Dhaula Kuan': [30.517, 77.479], 'Ganguwal': [31.25, 76.486], 
                'Ghanauli': [30.994, 76.527], 'Ghumarwin': [31.436, 76.708], 'Hamirpur': [31.684, 76.519], 
                'Janjehl': [31.52, 77.22], 'Jogindernagar': [32.036, 76.734], 'Jubbal':[31.12, 77.67], 
                'Kalatop': [32.552, 76.018], 'Kalpa': [31.54, 78.258], 'Kandaghat': [30.965, 77.119], 
                'Kangra': [32.103, 76.271], 'Karsog': [31.383, 77.2], 'Kasol': [31.357, 76.878], 
                'Kaza': [32.225, 78.072], 'Kotata': [31.233, 76.534], 'Kothai': [31.119, 77.485],
                'Kumarsain': [31.317, 77.45], 'Larji': [31.80, 77.19], 'Lohard': [31.204, 76.561], 
                'Mashobra': [31.13, 77.229], 'Nadaun': [31.783, 76.35], 'Nahan': [30.559, 77.289], 
                'Naina Devi': [31.279, 76.554], 'Nangal': [31.368, 76.404], 'Olinda': [31.401, 76.385],
                'Pachhad': [30.777, 77.164], 'Palampur': [32.107, 76.543], 'Pandoh':[31.67,77.06], 
                'Paonta Sahib': [30.47, 77.625], 'Rakuna': [30.605, 77.473], 'Rampur': [31.454,77.644],
                'Rampur IMD': [31.452, 77.633], 'Rohru':[31.204, 77.751], 'Sadar-Bilarspur':[31.348, 76.762], 
                'Sadar-Mandi': [31.712, 76.933], 'Sainj': [31.77, 77.31] , 'Salooni':[32.728, 76.034],
                'Sarkaghat': [31.704, 76.812], 'Sujanpur':[31.832, 76.503], 'Sundernargar': [31.534, 76.905], 
                'Suni':[31.238,77.108], 'Suni IMD':[31.23, 77.164], 'Swaghat': [31.713, 76.746], 
                'Theog': [31.124, 77.347]}
    
    # Load data
    era5_beas_da = dd.download_data('beas', xarray=True)
    beas_ds = era5_beas_da[['tp']]
    
    # Interpolate at location
    lat, lon = all_station_dict[station]
    loc_ds = beas_ds.interp(coords={"lon": lon, "lat": lat}, method="nearest")
    tim_ds = loc_ds.sel(time= slice(minyear, maxyear))

    return tim_ds