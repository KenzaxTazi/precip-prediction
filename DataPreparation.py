# Data Preparation

import os
import calendar
import datetime
import xarray as xr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn import preprocessing
from sklearn.model_selection import KFold
from sklearn.model_selection import train_test_split

import FileDownloader as fd


# Filepaths and URLs
mask_filepath = 'Data/ERA5_Upper_Indus_mask.nc'


def download_data(mask_filepath, xarray=False, ensemble=False): # TODO include variables in pathname 
    """ 
    Downloads data for prepearation or analysis

    Inputs
        mask_filepath: string
        xarray: boolean
        ensemble: boolean 
    
    Returns 
        df: DataFrame of data, or
        ds: DataArray of data
    """

    #nao_url = 'https://www.psl.noaa.gov/data/correlation/nao.data'
    n34_url =  'https://psl.noaa.gov/data/correlation/nina34.data'
    #n4_url =  'https://psl.noaa.gov/data/correlation/nina4.data'

    path = 'Data/'

    now = datetime.datetime.now()
    if ensemble == False:
        filename = 'combi_data' + '_' + now.strftime("%m-%Y")+'.csv' 
    else:
        filename = 'combi_data_ensemble' + '_' + now.strftime("%m-%Y")+'.csv'

    filepath = path + filename
    print(filepath)

    if not os.path.exists(filepath):

        # Indices
        #nao_df = fd.update_url_data(nao_url, 'NAO')
        n34_df = fd.update_url_data(n34_url, 'N34')
        #n4_df = fd.update_url_data(n4_url, 'N4')
        ind_df = n34_df.astype('float64') #.join([nao_df, n4_df])
        
        '''
        # Temperature
        temp_filepath = fd.update_cds_data(variables=['2m_temperature'], area=[40, 65, 20, 85], qualifier='temp')
        temp_da = xr.open_dataset(temp_filepath)
        if 'expver' in list(temp_da.dims):
            temp_da = temp_da.sel(expver=1)
        temp_mean_da = temp_da.mean(dim=['longitude', 'latitude'], skipna=True) 
        multiindex_df = temp_mean_da.to_dataframe()
        temp_df = multiindex_df.reset_index()

        # CGTI
        
        z200_filepath = fd.update_cds_data(variables=['geopotential'], pressure_level='200', area=[40, 60, 35,70], qualifier='z200')
        z200_da = xr.open_dataset(z200_filepath)
        if 'expver' in list(z200_da.dims):
            z200_da = z200_da.sel(expver=1)
        cgti_da = z200_da.mean(dim=['longitude', 'latitude'], skipna=True) 
        multiindex_df = cgti_da.to_dataframe()
        cgti_df = multiindex_df.reset_index()
        cgti_df = cgti_df.rename(columns={"z":"CGTI"})
        '''
        # Orography, humidity and precipitation
        if ensemble == False:
            cds_filepath = fd.update_cds_data()
        else:
            cds_filepath = fd.update_cds_data(product_type='monthly_averaged_ensemble_members')

        masked_da = apply_mask(cds_filepath, mask_filepath)
        multiindex_df = masked_da.to_dataframe()
        cds_df = multiindex_df.reset_index()

        # Combine
        df_combined1 = pd.merge_ordered(cds_df, ind_df, on='time')
        # df_combined2 = pd.merge_ordered(df_combined1, temp_df, on='time')
        # df_combined3 = pd.merge_ordered(df_combined2, cgti_df, on='time')
        df_clean = df_combined1.drop(columns=['expver_x', 'expver_y']).dropna()
        df_clean['time'] = df_clean['time'].astype('int')
        df_clean = df_clean.astype('float64')
        df_clean.to_csv(filepath)

        if xarray == True:
            if ensemble == True:
                df_multi = df_clean.set_index(['time', 'longitude', 'latitude', 'number'])
            else:
                df_multi = df_clean.set_index(['time', 'longitude', 'latitude'])
            ds = df_multi.to_xarray()
            return ds
        else:    
            return df_clean
    
    else:
        df = pd.read_csv(filepath)
        df_clean = df.drop(columns=['Unnamed: 0'])

        if xarray == True:
            if ensemble == True:
                df_multi = df_clean.set_index(['time', 'longitude', 'latitude', 'number'])
            else:
                df_multi = df_clean.set_index(['time', 'longitude', 'latitude'])
            ds = df_multi.to_xarray()
            return ds
        else:    
            return df_clean


def apply_mask(data_filepath, mask_filepath):
    """
    Opens NetCDF files and applies Upper Indus Basin mask to ERA 5 data.
    Inputs:
        Data filepath, NetCDF
        Mask filepath, NetCDF
    Return:
        A Data Array
    """
    da = xr.open_dataset(data_filepath)
    if 'expver' in list(da.dims):
        print('expver found')
        da = da.sel(expver=1)

    mask = xr.open_dataset(mask_filepath)
    mask_da = mask.overlap

    # slice in case step has not been performed at download stage
    sliced_da = da.sel(latitude=slice(38, 30), longitude=slice(71.25, 82.75))    
    
    UIB = sliced_da.where(mask_da > 0, drop=True)

    return UIB


def cumulative_monthly(da):
    """ Multiplies monthly averages by the number of day in each month """
    x, y, z = np.shape(da.values)
    times = np.datetime_as_string(da.time.values)
    days_in_month = []
    for t in times:
        year = t[0:4]
        month = t[5:7]
        days = calendar.monthrange(int(year), int(month))[1]
        days_in_month.append(days)
    dim = np.array(days_in_month)
    dim_mesh = np.repeat(dim, y*z).reshape(x, y, z) 
        
    return da * dim_mesh


def point_data_prep():
    """ 
    Outputs test and training data for total precipitation as a function of time from an ensemble of models for a single location

    Inputs
        da: DataArray 

    Outputs
        x_train: training feature vector, numpy array
        y_train: training output vector, numpy array
        dy_train: training standard deviation vector, numpy array
        x_test: testing feature vector, numpy array
        y_test: testing output vector, numpy array
        dy_test: testing standard deviation vector, numpy array

    """

    da = download_data(mask_filepath, xarray=True, ensemble=True)
    
    std_da = da.std(dim='number')
    mean_da = da.mean(dim='number')

    gilgit_mean = mean_da.interp(coords={'longitude':74.4584, 'latitude':35.8884 }, method='nearest')
    gilgit_std = std_da.interp(coords={'longitude':74.4584, 'latitude':35.8884 }, method='nearest')

    multi_index_df_mean = gilgit_mean.to_dataframe()
    df_mean= multi_index_df_mean.reset_index()
    df_mean_clean = df_mean.dropna()
    df_mean_clean['time'] = df_mean_clean['time'].astype('int')

    multi_index_df_std = gilgit_std.to_dataframe()
    df_std = multi_index_df_std.reset_index()
    df_std_clean = df_std.dropna()
    df_std_clean['time'] = df_std_clean['time'].astype('int')

    y = df_mean_clean['tp'].values*1000
    dy = df_std_clean['tp'].values*1000

    x_prime = df_mean_clean['time'].values.reshape(-1, 1)
    x = (x_prime - x_prime[0])/ (1e9*60*60*24*365)
    
    x_train = x[0:400]
    y_train = y[0:400]
    dy_train = dy[0:400]

    x_test = x[400:-2]
    y_test = y[400:-2]
    dy_test = dy[400:-2]

    return x_train, y_train, dy_train, x_test, y_test, dy_test


def multivariate_data_prep(number=None):
    """ 
    Outputs test and training data for total precipitation as a function of time, 2m dewpoint temperature, 
    angle of sub-gridscale orography, orography, slope of sub-gridscale orography, total column water vapour,
    Nino 3.4, Nino 4 and NAO index for a single point.

    Inputs
        None

    Outputs
        x_train: training feature vector, numpy array 
        y_train: training output vector, numpy array
        x_test: testing feature vector, numpy array
        y_test: testing output vector, numpy array
    """
    if number == None:
        da = download_data(mask_filepath, xarray=True)
    else:
        da = download_data(mask_filepath, xarray=True, ensemble=True)
        da = da.sel(number=number).drop('number')

    gilgit = da.interp(coords={'longitude':74.4584, 'latitude':35.8884 }, method='nearest')
    multiindex_df = gilgit.to_dataframe()
    df_clean = multiindex_df.reset_index()
    df = df_clean.drop(columns=['latitude', 'longitude'])

    df['time'] = df['time'].astype('int')
    df['time'] = (df['time'] - df['time'].min())/ (1e9*60*60*24*365)
    df['tp'] = df['tp']*1000  # to mm
    df_clean = df.dropna()

    # Remove last 10% of time for testing
    test_df = df_clean[ df_clean['time']> df_clean['time'].max()*0.9]
    xtest = test_df.drop(columns=['tp']).values
    ytest = test_df['tp'].values

    # Training and validation data
    tr_df = df_clean[ df_clean['time']< df_clean['time'].max()*0.9]
    xtr = tr_df.drop(columns=['tp']).values
    ytr = tr_df['tp'].values

    xtrain, xval, ytrain, yval = kfold_split(xtr, ytr)
    
    return xtrain, xval, xtest, ytrain, yval, ytest


def gp_area_prep(mask_filepath, number=None):
    """ 
    Outputs test and training data for total precipitation as a function of time, 2m dewpoint temperature, 
    angle of sub-gridscale orography, orography, slope of sub-gridscale orography, total column water vapour,
    Nino 3.4, Nino 4 and NAO index for a given area.

    Inputs
        mask_da: mask for area of interest, DataArray

    Outputs
        x_train: training feature vector, numpy array
        y_train: training output vector, numpy array
        x_test: testing feature vector, numpy array
        y_test: testing output vector, numpy array
    """
    if number == None:
        df = download_data(mask_filepath)
    else:
        df = download_data(mask_filepath, ensemble=True)
        df = df[df['number']== number].drop('number')
    
    df['time'] = df['time'].astype('int')
    df['time'] = (df['time'] - df['time'].min())/ (1e9*60*60*24*365)
    df['tp'] = df['tp']*1000  # to mm
    df_clean = df.dropna()

    # Remove last 10% of time for testing
    test_df = df_clean[ df_clean['time']> df_clean['time'].max()*0.9]
    xtest = test_df.drop(columns=['tp']).values
    ytest = test_df['tp'].values

    # Training and validation data
    tr_df = df_clean[ df_clean['time']< df_clean['time'].max()*0.9]
    xtr = tr_df.drop(columns=['tp']).values
    ytr = tr_df['tp'].values
    
    xtrain, xval, ytrain, yval = kfold_split(xtr, ytr)
    
    return xtrain, xval, xtest, ytrain, yval, ytest


def normalise(df):
    """ Normalise dataframe """

    features = list(df)
    for f in features:
        df[f] = df[f]/df[f].max()

    return df


def kfold_split(x, y, dy=None, folds=5):
    """ 
    Split values into training, validation and test sets.
    The training and validation set are prepared for k folding.

    Inputs
        x: array of features
        y: array of target values
        dy: array of uncertainty on target values
        folds: number of kfolds

    Outputs
        xtrain: feature training set
        xvalidation: feature validation set

        ytrain: target training set
        yvalidation: target validation set

        dy_train: uncertainty training set
        dy_validation: uncertainty validation set
    """
    # Remove test set without shuffling
    
    kf = KFold(n_splits=folds)
    for train_index, test_index in kf.split(x):
        xtrain, xval = x[train_index], x[test_index]
        ytrain, yval = y[train_index], y[test_index]

    return  xtrain, xval, ytrain, yval,



    

