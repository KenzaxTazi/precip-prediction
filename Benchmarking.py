# Trend comparison

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import datetime
import glob
import seaborn as sns
import cftime 
from scipy import stats

import DataDownloader as dd
import DataPreparation as dp
import GPModels as gpm
import Correlation as corr
import Timeseries as tims
import PDF as pdf

model_filepath = 'Models/model_2021-01-01/08/21-22-35-56'


def select_coords(dataset, lat=None, lon=None):
    """ Interpolate dataset at given coordinates """
    timeseries = dataset.interp(coords={"lon": lon, "lat": lat}, method="nearest")
    timeseries = timeseries.sel(time= slice(1990, 2005))
    return timeseries

def select_basin(dataset, location):
    """ Interpolate dataset at given coordinates """  
    mask_filepath = dp.find_mask(location)
    basin = dd.apply_mask(dataset, mask_filepath) 
    basin = basin.sel(time= slice(1990, 2005))  
    return basin

def model_prep(location, model_filepath, minyear=1990, maxyear=2005):
    """ Prepares model outputs for comparison """

    model = gpm.restore_model(model_filepath)

    xtr, ytr = dp.areal_model_eval(location, minyear=minyear, maxyear=maxyear)
    y_gpr, y_std = model.predict_y(xtr)
 
    # to mm/day
    y_gpr_t = dp.inverse_log_transform(y_gpr) * 1000
    y_std_t = dp.inverse_log_transform(y_std) * 1000

    model_ds = xr.Dataset( 
        data_vars= dict(
            tp = (["lon", "lat", "time"], y_gpr_t),
            tp_std_t = (["lon", "lat", "time"], y_std_t)),
        coords = dict(
            lon = (["lon", "lat"], xtr[2]), 
            lat = (["lon", "lat"], xtr[1]),
            time = xtr[0]))

    model_ds.assign_attrs(plot_legend="ERA5")

    return model_ds

def dataset_stats(datasets):
    """ Print mean, standard deviations and slope for datasets """

    for ds in datasets:

        tp = ds.tp.values
        if np.shape(tp)[1]>1:
            ds = dp.average_basin_values(ds)
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(ds.time.values, ds.tp.values)
        #print(ds.plot_legend) # TODO
        print('mean = ', np.mean(ds.tp.values),'mm/day')
        print('std = ', np.std(ds.tp.values), 'mm/day')
        print('slope = ', slope, 'mm/day/month')

def single_location_comparison(model_filepath, lat, lon):
    """ Plots model outputs for given coordinates over time """
    
    era5_ds = dd.collect_ERA5()
    cmip_ds = dd.collect_CMIP5()
    cordex_ds = dd.collect_CORDEX()
    cru_ds = dd.collect_CRU()
    #aphro_ds = dd.collect_APHRO()
 
    era5_ts = select_coords(era5_ds, lat, lon)
    cmip_ts = select_coords(cmip_ds, lat, lon)
    cordex_ts = select_coords(cordex_ds, lat, lon)
    cru_ts = select_coords(cru_ds, lat, lon)
    #aphro_ts = select_coords(aphro_ds, lat, lon)

    timeseries = [era5_ts, cmip_ts, cordex_ts, cru_ts] #, aphro_ts]

    xtr, y_gpr_t, y_std_t = model_prep([lat, lon], model_filepath)

    tims.benchmarking_plot(timeseries, xtr, y_gpr_t, y_std_t)
    dataset_stats(timeseries, xtr, y_gpr_t, y_std_t)
    corr.dataset_correlation(timeseries, y_gpr_t)
    pdf.benchmarking_plot(timeseries, y_gpr_t)


def basin_comparison(model_filepath, location):
    """ Plots model outputs for given coordinates over time """
    
    era5_ds = dd.collect_ERA5()
    cmip_ds = dd.collect_CMIP5()
    cordex_ds = dd.collect_CORDEX()
    cru_ds = dd.collect_CRU()
    #aphro_ds = dd.collect_APHRO()
 
    era5_bs = select_basin(era5_ds, location)
    cmip_bs = select_basin(cmip_ds, location)
    cordex_bs = select_basin(cordex_ds, location)
    cru_bs = select_basin(cru_ds, location)
    #aphro_bs = select_basin(aphro_ds, location)

    model_bs = model_prep(location, model_filepath)

    basins = [model_bs, era5_bs, cmip_bs, cordex_bs, cru_bs] #, aphro_ts]

    dataset_stats(basins)

    tims.benchmarking_plot(basins, xtr, y_gpr_t, y_std_t)
    
    corr.dataset_correlation(basins, y_gpr_t)
    pdf.benchmarking_plot(basins, y_gpr_t)





























