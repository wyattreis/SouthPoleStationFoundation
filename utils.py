# -------------------------------------------------------------------------------
# Name          South Pole Station Settlement Utilies
# Description:  Collection of utilities to visulaize the historic settlement at 
#               the South Pole Station as recorded by surveys at monitoring 
#               points. Utilities also include analysis to project future 
#               settlement using existing patterns.
# Author:       Wyatt Reis
#               US Army Corps of Engineers
#               Cold Regions Research and Engineering Laboratory (CRREL)
#               Wyatt.K.Reis@usace.army.mil
# Created:      October 2023
# Updated:      April 2024
#
# -------------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import scipy.stats as stats
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt

# import survey data from the excel
def read_xl(xlfile, sheet):
    if sheet == 'SURVEY DATA':
        data = pd.read_excel(
            xlfile,
            engine='openpyxl',
        sheet_name='SURVEY DATA',
        skiprows=[0,2,3], 
        nrows=36)
    # rename second 2010/11/2 survey to 2010/11/3
        data_clean = data.dropna(axis=1, how='all').drop(columns=["DESCRIPTION", "Shims\nNote 13", "Delta"]).rename(columns={"MONITOR\nPOINT":"MONITOR_POINT", "2010-11-02 00:00:00.1":'2010-11-03 00:00:00'}).set_index('MONITOR_POINT').rename_axis('date', axis=1)
        data_clean.columns = pd.to_datetime(data_clean.columns).astype(str)
    
    else:
        data = pd.read_excel(
            xlfile,
            engine='openpyxl',
            sheet_name=sheet,
            skiprows=[0,2,3], 
            nrows=36)
        
        data_clean = data.dropna(axis=1, how='all').drop(columns=["DESCRIPTION", "Shims", "Delta"]).rename(columns={"MONITOR\nPOINT":"MONITOR_POINT"}).set_index('MONITOR_POINT').rename_axis('date', axis=1)
        data_clean.columns = pd.to_datetime(data_clean.columns).astype(str)
    return data_clean

# import beam information and label location
def read_beamInfo():
    beamfile = 'https://raw.githubusercontent.com/wyattreis/SouthPoleStationFoundation/main/SP_BeamArrowLabels.csv'
    beamInfo = pd.read_csv(beamfile)
    beamLength = beamInfo[['MP_W_S', 'MP_E_N', 'beamName', 'beamLength']].dropna()
    MPlocations = beamInfo[['MP_W_S', 'mpX', 'mpY']].rename(columns={"MP_W_S":"MONITOR_POINT"}).dropna().set_index('MONITOR_POINT')

    # Convert the beam length file to long format and make index the east or south Monitoring Point for each beam
    beamLength_long = pd.melt(beamLength, id_vars=['beamName', 'beamLength']).rename(columns={'value':'MONITOR_POINT', 'variable':'beamEnd'})
    beamLength_long.set_index('MONITOR_POINT', inplace = True)
    beamLength_sort = beamLength_long.drop(columns=['beamEnd']).sort_values('beamName').set_index('beamName')
    beamLength_sort = beamLength_sort[~beamLength_sort.index.duplicated(keep='first')]
    return beamInfo, beamLength, MPlocations, beamLength_long, beamLength_sort

# Calculate the cumulative settlement in feet for each column by survey data
def calc_settlement(survey_clean, truss_clean, shim_clean, MPlocations):
    survey_long = survey_clean.T
    survey_long['dummy']= 1
    firstValue = survey_long.groupby('dummy').first()
    firstValue = firstValue.to_numpy()[0]

    #create an elevation of lug dateframe
    elevation =  survey_long.drop(columns=["dummy"])
    elevation.index = pd.to_datetime(elevation.index)

    #create an elevation of the grade beams using the 12.31' listed in the SPS As-builts Sheet A5.1 minues 1' between top of column and survey point (11.31' below survey point)
    truss_2017 = truss_clean[['2017-12-01']]
    shim_2017 = shim_clean[['2017-12-01']]
    height = shim_2017.add(12.31).sub(truss_2017)
    height_gradeBeam_lug = pd.Series(height['2017-12-01'].values, index=height.index)

    #gradeBeamElev = elevation.sub(11.31).transpose() #assuming lugs are 1' below top of column
    #gradeBeamElev = survey_clean.add(truss_clean).sub(shim_clean.div(12)).sub(12.31).dropna(axis=1, how='all') # Using the shimpack data to 
    gradeBeamElev = survey_clean.sub(height_gradeBeam_lug, axis = 0)
    gradeBeamElevPlot = gradeBeamElev
    gradeBeamElevPlot.columns = gradeBeamElevPlot.columns.astype(str)
    gradeBeamElevPlot = MPlocations.join(gradeBeamElevPlot)

    settlement = survey_long.drop(columns=["dummy"]).apply(lambda row: firstValue - row, axis=1)
    settlement.index = pd.to_datetime(settlement.index)
    settlement_points = pd.DataFrame.transpose(settlement)

    # Calculate the change in settlement in inches for each monitoring point - skip 2010/11/02 surveys, like in excel workbook
    settlement_delta = settlement.drop(['2010-11-02', '2010-11-03'], axis = 0).diff().mul(12)
    settlement_delta_MP = pd.DataFrame.transpose(settlement_delta)

    # Calculate the annual settlement rate for each column 
    diffDays = pd.DataFrame(index=settlement_delta.index)
    diffDays["diffDays"] = settlement_delta.index.to_series().diff().dt.days

    settlement_rate = settlement_delta.iloc[:,:].div(diffDays.diffDays, axis=0).mul(365).round(3)
    return elevation, gradeBeamElev, gradeBeamElevPlot, settlement, settlement_points, settlement_delta, settlement_delta_MP, settlement_rate

# Cumulative Settlement Forecasting
def calc_forecast_settlement(settlement, nsurvey, nyears):
    settlement_clean = settlement.drop("2022-01-07", axis=0)
    settlementInterp = settlement_clean.iloc[(len(settlement_clean.index)-(nsurvey)):(len(settlement_clean.index))]
    currentYear = settlementInterp.index.year[-1]

    starting_settlement = settlementInterp.iloc[-1]

    projList = []
    for year in range(nyears):
        projYear = (currentYear + year+1).astype(str)
        projYear = pd.to_datetime(projYear + '-01-01') 
        projList.append(projYear)

    settlementExtrap = pd.DataFrame(columns=settlementInterp.columns, index = [projList]).reset_index().set_index('level_0')
    settlementExtrap.index = settlementExtrap.index.map(dt.datetime.toordinal)
    settlementInterp.index = settlementInterp.index.map(dt.datetime.toordinal)

    x_endpoints = list([settlementInterp.index[0], settlementInterp.index[nsurvey-1]]) + settlementExtrap.index.tolist()
    x_enddates = pd.DataFrame(x_endpoints[1:])
    deltaDays = [x - x_endpoints[1] for x in x_endpoints[1:]]

    df_regression = settlementInterp.apply(lambda x: stats.linregress(settlementInterp.index, x), result_type='expand').rename(index={0: 'slope', 1: 
                                                                                    'intercept', 2: 'rvalue', 3:
                                                                                    'p-value', 4:'stderr'})

    settlementProj = pd.DataFrame(index=x_enddates[0])
    for column in df_regression.columns:   
        slope = df_regression.loc['slope', column]  
        projected_data = [starting_settlement[column] + slope * val for val in deltaDays]
        settlementProj[column] = projected_data
        
    settlementProj.index.names = ['date']
    settlementProj.index = settlementProj.index.map(dt.datetime.fromordinal)
    settlementProj = settlementProj.apply(pd.to_numeric, errors='ignore').round(3)


    settlementProj_trans = settlementProj
    settlementProj_trans.index = settlementProj_trans.index.strftime('%Y-%m-%d') 
    settlementProj_trans = pd.DataFrame.transpose(settlementProj_trans).iloc[:,1:]

    return settlementProj, settlementProj_trans

def calc_forecast_elevation(elevation, truss_clean, nsurvey, nyears):
    elev_clean = elevation.drop("2022-01-07", axis=0)
    elevInterp = elev_clean.iloc[(len(elev_clean.index)-(nsurvey)):(len(elev_clean.index))]
    currentYear = elevInterp.index.year[-1]

    starting_elev = elevInterp.iloc[-1]

    projList = []
    for year in range(nyears):
        projYear = (currentYear + year+1).astype(str)
        projYear = pd.to_datetime(projYear + '-01-01') 
        projList.append(projYear)

    elevExtrap = pd.DataFrame(columns=elevInterp.columns, index = [projList]).reset_index().set_index('level_0')
    elevExtrap.index = elevExtrap.index.map(dt.datetime.toordinal)
    elevInterp.index = elevInterp.index.map(dt.datetime.toordinal)

    x_endpoints = list([elevInterp.index[0], elevInterp.index[nsurvey-1]]) + elevExtrap.index.tolist()
    x_enddates = pd.DataFrame(x_endpoints[1:])
    deltaDays = [x - x_endpoints[1] for x in x_endpoints[1:]]

    df_regression = elevInterp.apply(lambda x: stats.linregress(elevInterp.index, x), result_type='expand').rename(index={0: 'slope', 1: 
                                                                                    'intercept', 2: 'rvalue', 3:
                                                                                    'p-value', 4:'stderr'})

    elevProj = pd.DataFrame(index=x_enddates[0])
    for column in df_regression.columns:   
        slope = df_regression.loc['slope', column]  
        projected_data = [starting_elev[column] + slope * val for val in deltaDays]
        elevProj[column] = projected_data

    elevProj.index.names = ['date']
    elevProj.index = elevProj.index.map(dt.datetime.fromordinal)
    elevProj = elevProj.apply(pd.to_numeric, errors='ignore').round(3)

    elevProj_trans = elevProj
    elevProj_trans.index = elevProj_trans.index.strftime('%Y-%m-%d') 
    elevProj_trans = pd.DataFrame.transpose(elevProj_trans)#.iloc[:,1:]

    currentTruss = truss_clean.iloc[:,-1]
    elevFloorProj = elevProj_trans.add(currentTruss, axis="index")

    elevGradeBeamProj = elevProj_trans.sub(11.31)

    return elevProj, elevProj_trans, elevFloorProj, elevGradeBeamProj

# Calculate differental settlement
def calc_differental_settlement(beamLength_long, beamLength_sort, survey_clean, beamInfo, settlementProj_trans, elevFloorProj, floorElevPlot):
    # Merge the beam file and the settlement file
    beamSettlement = beamLength_long.join(survey_clean)

    # Merge the beam file and the projected settlement file
    beamSettlementProj = beamLength_long.join(settlementProj_trans)

    # Group by beamName, difference, and convert to inches, keep only the differenced values
    beamDiff = beamSettlement.set_index(['beamName']).sort_values(by=['beamName', 'beamEnd']).drop(columns=['beamEnd', 'beamLength']).groupby(['beamName']).diff().mul(12)
    beamDiff = beamDiff[~beamDiff.index.duplicated(keep='last')]
    beamDiff.columns = pd.to_datetime(beamDiff.columns).astype(str)
    beamDiffplot = beamInfo[['beamName', 'beamX', 'beamY']].dropna().set_index(['beamName']).join(beamDiff)
    beamDiff = beamDiffplot.drop(columns=['beamX', 'beamY'])

    # Projected beam settlement differences 
    beamDiffProj = beamSettlementProj.set_index(['beamName']).sort_values(by=['beamName', 'beamEnd']).drop(columns=['beamEnd', 'beamLength']).groupby(['beamName']).diff().mul(12)
    beamDiffProj = beamDiffProj[~beamDiffProj.index.duplicated(keep='last')]
    beamDiffProj.columns = pd.to_datetime(beamDiffProj.columns).astype(str)

    # Calculate the slope for each beam, transpose for plotting 
    beamSlope = beamLength_sort.join(beamDiff)
    beamSlope.iloc[:,1:] = beamSlope.iloc[:,1:].div(beamSlope.beamLength, axis=0)
    beamSlopeplot = beamInfo[['beamName', 'beamX', 'beamY']].dropna().set_index(['beamName']).join(beamSlope)
    beamSlope = beamSlopeplot.drop(columns=['beamX', 'beamY', 'beamLength'])

    # Calculate the projected slope for each beam 
    beamSlopeProj = beamLength_sort.join(beamDiffProj)
    beamSlopeProj.iloc[:,1:] = beamSlopeProj.iloc[:,1:].div(beamSlopeProj.beamLength, axis=0)
    beamSlopeProj= beamSlopeProj.drop(columns=['beamLength'])

    # Floor settlement differences 
    floorElevAll = beamLength_long.join(floorElevPlot).join(elevFloorProj.iloc[:,1:])
    floorDiffElev = floorElevAll.set_index(['beamName']).sort_values(by=['beamName', 'beamEnd']).drop(columns=['beamEnd', 'beamLength', 'mpX', 'mpY']).groupby(['beamName']).diff().mul(12)
    floorDiffElev = floorDiffElev[~floorDiffElev.index.duplicated(keep='last')].abs()
    floorDiffElev.columns = pd.to_datetime(floorDiffElev.columns).astype(str)

    floorElevProj = beamLength_long.join(elevFloorProj)
    floorDiffProj = floorElevProj.set_index(['beamName']).sort_values(by=['beamName', 'beamEnd']).drop(columns=['beamEnd', 'beamLength']).groupby(['beamName']).diff().mul(12)
    floorDiffProj = floorDiffProj[~floorDiffProj.index.duplicated(keep='last')].abs()
    floorDiffProj.columns = pd.to_datetime(floorDiffProj.columns).astype(str)

    return beamDiff, beamDiffProj, beamDiffplot, beamSlope, beamSlopeplot, beamSlopeProj, floorDiffElev, floorDiffProj

# Create dataframes for planview plotting 
# (lug and floor elevations, lug to truss measurement, differential settlement)
def calc_plan_dataframe(survey_clean, truss_clean, shim_clean, MPlocations, beamLength_long, beamLength_sort, beamInfo, gradeBeamElev):
    # Lug elevation for each survey date
    lugElevPlot = MPlocations.join(survey_clean)

    # Shim height for each survey date
    shimElevPlot = MPlocations.join(shim_clean.mul(12)).dropna(axis=1, how='all')

    # Lug to truss height for each survey date (shim stack)
    lugFloorPlot = MPlocations.join(truss_clean).dropna(axis=1, how='all')

    # Calculate floor elevation for each survey date
    floorElev = survey_clean.add(truss_clean)
    floorElev_clean = floorElev.dropna(axis=1, how='all')
    floorElevPlot = MPlocations.join(floorElev_clean)

    # Calculate the elevation difference of the floor at each column
    floorSettlement = beamLength_long.join(floorElev_clean)
    floorDiff = floorSettlement.set_index(['beamName']).sort_values(by=['beamName', 'beamEnd']).drop(columns=['beamEnd', 'beamLength']).groupby(['beamName']).diff().mul(12)
    floorDiff = floorDiff[~floorDiff.index.duplicated(keep='last')]
    floorDiff.columns = pd.to_datetime(floorDiff.columns).astype(str)
    floorDiffplot = beamInfo[['beamName', 'beamX', 'beamY']].dropna().set_index(['beamName']).join(floorDiff)

    # Calculate the floor slope between columns 
    floorSlope = beamLength_sort.join(floorDiff)
    floorSlope.iloc[:,1:] = floorSlope.iloc[:,1:].div(floorSlope.beamLength, axis=0)
    floorSlopeplot = beamInfo[['beamName', 'beamX', 'beamY']].dropna().set_index(['beamName']).join(floorSlope)

    gradeBeamDiff = beamLength_long.join(gradeBeamElev).set_index(['beamName']).sort_values(by=['beamName', 'beamEnd']).drop(columns=['beamEnd', 'beamLength']).groupby(['beamName']).diff().mul(12)
    gradeBeamDiff = gradeBeamDiff[~gradeBeamDiff.index.duplicated(keep='last')]
    gradeBeamDiff.columns = pd.to_datetime(gradeBeamDiff.columns).astype(str)

    return lugElevPlot, lugFloorPlot, floorElevPlot, floorDiff, floorDiffplot, floorSlope, floorSlopeplot, shimElevPlot, gradeBeamDiff

# Create dataframe for 3D plotting
def calc_3d_dataframe(beamInfo, settlement_points, settlementProj_trans, beamSlopeColor, beamSlopeProjColor):
    beamStart = beamInfo[['MP_W_S', 'beamName']].set_index('MP_W_S')
    settlementStart = beamStart.join(settlement_points).set_index('beamName')
    settlementStart.columns = pd.to_datetime(settlementStart.columns).astype(str)
    settlementProjStart = beamStart.join(settlementProj_trans).set_index('beamName')
    settlementStart = settlementStart.join(settlementProjStart)

    beamEnd = beamInfo[['MP_E_N', 'beamName']].set_index('MP_E_N')
    settlementEnd = beamEnd.join(settlement_points).set_index('beamName')
    settlementEnd.columns = pd.to_datetime(settlementEnd.columns).astype(str)
    settlementProjEnd = beamEnd.join(settlementProj_trans).set_index('beamName')
    settlementEnd = settlementEnd.join(settlementProjEnd)

    settlement3D = settlementStart.join(settlementEnd, lsuffix='_start', rsuffix='_end')

    beamInfo3D = beamInfo.loc[:, ['beamName','MP_W_S','startX', 'startY', 'endX','endY','labelX', 'labelY']].set_index('beamName')
    beamInfo3D = beamInfo3D.join(settlement3D)
    beamInfo3D = beamInfo3D[beamInfo3D.index.notnull()]
    beamInfo3D = beamInfo3D.join(beamSlopeColor).join(beamSlopeProjColor)
    return settlementStart, beamInfo3D

# Create dataframe for 3D plotting floor elevations
def calc_3d_floorElev(beamInfo, floorElevPlot, elevFloorProj, floorDiffColor, beamSlopeProjColor):
    beamStart = beamInfo[['MP_W_S', 'beamName']].set_index('MP_W_S')
    elevationFloorStart = beamStart.join(floorElevPlot.drop(columns=['mpX', 'mpY'])).set_index('beamName')
    elevationFloorStart.columns = pd.to_datetime(elevationFloorStart.columns).astype(str)
    elevationFloorProjStart = beamStart.join(elevFloorProj.iloc[:,1:]).set_index('beamName')
    # elevationFloorStart = elevationFloorStart.join(elevationFloorProjStart)

    beamEnd = beamInfo[['MP_E_N', 'beamName']].set_index('MP_E_N')
    elevationFloorEnd = beamEnd.join(floorElevPlot.drop(columns=['mpX', 'mpY'])).set_index('beamName')
    elevationFloorEnd.columns = pd.to_datetime(elevationFloorEnd.columns).astype(str)
    elevationFloorProjEnd = beamEnd.join(elevFloorProj.iloc[:,1:]).set_index('beamName')
    # elevationFloorEnd = elevationFloorEnd.join(elevationFloorProjEnd)

    elevFloor3D = elevationFloorStart.join(elevationFloorEnd, lsuffix='_start', rsuffix='_end')

    elevFloorInfo3D = beamInfo.loc[:, ['beamName','MP_W_S','startX', 'startY', 'endX','endY','labelX', 'labelY']].set_index('beamName')
    elevFloorInfo3D = elevFloorInfo3D.join(elevFloor3D)
    elevFloorInfo3D = elevFloorInfo3D[elevFloor3D.index.notnull()]
    elevFloorInfo3D = elevFloorInfo3D.join(floorDiffColor)#.join(beamSlopeProjColor)
    return elevationFloorStart, elevFloorInfo3D

# Create dataframe for 3D plotting floor elevations
def calc_3d_gradeBeamElev(beamInfo, gradeBeamElev, elevGradeBeamProj, beamDiffColor, beamSlopeProjColor):
    beamStart = beamInfo[['MP_W_S', 'beamName']].set_index('MP_W_S')
    elevationGBStart = beamStart.join(gradeBeamElev).set_index('beamName')
    elevationGBStart.columns = pd.to_datetime(elevationGBStart.columns).astype(str)
    elevationFloorProjStart = beamStart.join(elevGradeBeamProj.iloc[:,1:]).set_index('beamName')
    #elevationGBStart = elevationGBStart.join(elevationFloorProjStart)

    beamEnd = beamInfo[['MP_E_N', 'beamName']].set_index('MP_E_N')
    elevationGBEnd = beamEnd.join(gradeBeamElev).set_index('beamName')
    elevationGBEnd.columns = pd.to_datetime(elevationGBEnd.columns).astype(str)
    elevationFloorProjEnd = beamEnd.join(elevGradeBeamProj.iloc[:,1:]).set_index('beamName')
    #elevationGBEnd = elevationGBEnd.join(elevationFloorProjEnd)

    elevGB3D = elevationGBStart.join(elevationGBEnd, lsuffix='_start', rsuffix='_end')

    elevGBInfo3D = beamInfo.loc[:, ['beamName','MP_W_S','startX', 'startY', 'endX','endY','labelX', 'labelY']].set_index('beamName')
    elevGBInfo3D = elevGBInfo3D.join(elevGB3D)
    elevGBInfo3D = elevGBInfo3D[elevGB3D.index.notnull()]
    elevGBInfo3D = elevGBInfo3D.join(beamDiffColor)#.join(beamSlopeProjColor)
    return elevationGBStart, elevGBInfo3D

def calc_plane_error(floorElevPlot, gradeBeamElevPlot):
    pods = ['A', 'B']
    slopes_dict_floor = {'Pod': [], 'Survey_date': [], 'X': [], 'Y': [], 'Max': []}
    error_fitFloor = pd.DataFrame()
    error_meanFloor = pd.DataFrame()
    error_stdFloor = pd.DataFrame()

    for pod in pods:
        df = floorElevPlot[[pod in s for s in floorElevPlot.index]]

        # Calculate the error from the mean plane - floor elevations
        mean_pod = df.iloc[:, 2:].mean()
        error_pod = df.iloc[:, 2:] - mean_pod
        error_meanFloor = pd.concat([error_meanFloor, error_pod])

        error_fitFloor_sub = pd.DataFrame()
        for col in df.columns[2:]:
            # Extract coordinates
            xs = df['mpX']
            ys = df['mpY']
            zs = df[col]

            # Fit plane 
            tmp_A = []
            tmp_b = []
            for i in range(len(xs)):
                tmp_A.append([xs[i], ys[i], 1])
                tmp_b.append(zs[i])
            b = np.matrix(tmp_b).T
            A = np.matrix(tmp_A)
            fit = (A.T * A).I * A.T * b
            errors = b - A * fit
            
            error_fitFloor_sub[col] = np.array(errors).flatten()

            # Extract X and Y slopes (the first two elements of 'fit')
            x_slope = abs(fit[0, 0])
            y_slope = abs(fit[1, 0])
            max_slope = np.sqrt(x_slope**2 + y_slope**2)
            
            # Store the slopes in the dictionary
            slopes_dict_floor['X'].append(x_slope)
            slopes_dict_floor['Y'].append(y_slope)
            slopes_dict_floor['Max'].append(max_slope)
            slopes_dict_floor['Survey_date'].append(col)
            slopes_dict_floor['Pod'].append(pod)

        # Combine the errors for each pod into one DF
        error_fitFloor_sub['MP'] = df.index
        error_fitFloor_sub = error_fitFloor_sub.set_index('MP')#.drop("2022-01-07", axis=1).mul(12)
        error_fitFloor = pd.concat([error_fitFloor, error_fitFloor_sub])

        #Calculate the standard deviation of the pod
        pod_std_mean = error_pod.std()
        pod_std_fit = error_fitFloor_sub.std()
        error_stdFloor[f'Pod {pod} - Mean'] = pod_std_mean
        error_stdFloor[f'Pod {pod} - Fitted'] = pod_std_fit

    # Remove the 2022 survey from the data frames
    error_meanFloor = error_meanFloor.drop("2022-01-07", axis=1).mul(12)
    error_fitFloor = error_fitFloor.drop("2022-01-07", axis=1).mul(12)
    error_stdFloor = error_stdFloor.drop("2022-01-07", axis=0).mul(12)
    slopes_fitFloor = pd.DataFrame(slopes_dict_floor)
    slopes_fitFloor = slopes_fitFloor[~(slopes_fitFloor['Survey_date'] == "2022-01-07")]
    slopes_fitFloor.iloc[:, 2:] *= 100
  
    ###########################################################################################################
    slopes_dict_GB = {'Pod': [], 'Survey_date': [], 'X': [], 'Y': [], 'Max': []}
    error_fitGradeBeam = pd.DataFrame()
    error_meanGradeBeam = pd.DataFrame()
    error_stdGradeBeam = pd.DataFrame()

    for pod in pods:
        df = gradeBeamElevPlot[[pod in s for s in gradeBeamElevPlot.index]]

        # Calculate the error from the mean plane - floor elevations
        mean_pod = df.iloc[:, 2:].mean()
        error_pod = df.iloc[:, 2:] - mean_pod
        error_meanGradeBeam = pd.concat([error_meanGradeBeam, error_pod])

        error_fitGB_sub = pd.DataFrame()
        for col in df.columns[2:]:
            # Extract coordinates
            xs = df['mpX']
            ys = df['mpY']
            zs = df[col]

            # Fit plane 
            tmp_A = []
            tmp_b = []
            for i in range(len(xs)):
                tmp_A.append([xs[i], ys[i], 1])
                tmp_b.append(zs[i])
            b = np.matrix(tmp_b).T
            A = np.matrix(tmp_A)
            fit = (A.T * A).I * A.T * b
            errors = b - A * fit
            
            error_fitGB_sub[col] = np.array(errors).flatten()

            # Extract X and Y slopes (the first two elements of 'fit')
            x_slope = abs(fit[0, 0])
            y_slope = abs(fit[1, 0])
            max_slope = np.sqrt(x_slope**2 + y_slope**2)
            
            # Store the slopes in the dictionary
            slopes_dict_GB['X'].append(x_slope)
            slopes_dict_GB['Y'].append(y_slope)
            slopes_dict_GB['Max'].append(max_slope)
            slopes_dict_GB['Survey_date'].append(col)
            slopes_dict_GB['Pod'].append(pod)

        # Combine the errors for each pod into one DF
        error_fitGB_sub['MP'] = df.index
        error_fitGB_sub = error_fitGB_sub.set_index('MP')#.drop("2022-01-07", axis=1).mul(12)
        error_fitGradeBeam = pd.concat([error_fitGradeBeam, error_fitGB_sub])

        #Calculate the standard deviation of the pod
        pod_std_mean = error_pod.std()
        pod_std_fit = error_fitGB_sub.std()
        error_stdGradeBeam[f'{pod}-pod - Mean'] = pod_std_mean
        error_stdGradeBeam[f'{pod}-pod - Fitted'] = pod_std_fit

    # Remove the 2022 survey from the data frames
    error_meanGradeBeam = error_meanGradeBeam.drop("2022-01-07", axis=1).mul(12)
    error_fitGradeBeam = error_fitGradeBeam.drop("2022-01-07", axis=1).mul(12)
    error_stdGradeBeam = error_stdGradeBeam.drop("2022-01-07", axis=0).mul(12)
    slopes_fitGradeBeam = pd.DataFrame(slopes_dict_GB)
    slopes_fitGradeBeam = slopes_fitGradeBeam[~(slopes_fitGradeBeam['Survey_date'] == "2022-01-07")]
    slopes_fitGradeBeam.iloc[:, 2:] *= 100
  
    return error_meanFloor, error_fitFloor, error_stdFloor, slopes_fitFloor, error_meanGradeBeam, error_fitGradeBeam, error_stdGradeBeam, slopes_fitGradeBeam

def calc_GradeBeam_profiles(gradeBeamElevPlot):
    #A Pod Grade Beams
    # Grade Beam A3-4 - A2-1
    GBelev_A3_4_A2_1 = gradeBeamElevPlot.loc[gradeBeamElevPlot.index.isin(['A3-4', 'A3-1', 'A2-5', 'A2-3', 'A2-1'])].copy()
    GBelev_A3_4_A2_1.sort_values(by='mpX', inplace=True)
    startX = gradeBeamElevPlot.loc['A3-4', 'mpX']
    GBelev_A3_4_A2_1['plotX'] = gradeBeamElevPlot['mpX'] - startX
    GBelev_A3_4_A2_1['long_beam'] = 'A3-4 - A2-1'

    # Grade Beam A3-3 - A2-2
    GBelev_A3_3_A2_2 = gradeBeamElevPlot.loc[gradeBeamElevPlot.index.isin(['A3-3', 'A3-2', 'A2-6', 'A2-4', 'A2-2'])].copy()
    GBelev_A3_3_A2_2.sort_values(by='mpX', inplace=True)
    startX = gradeBeamElevPlot.loc['A3-3', 'mpX']
    GBelev_A3_3_A2_2['plotX'] = gradeBeamElevPlot['mpX'] - startX
    GBelev_A3_3_A2_2['long_beam'] = 'A3-3 - A2-2'

    # Grade Beam A1-2 - A2-1
    GBelev_A1_2_A2_1 = gradeBeamElevPlot.loc[gradeBeamElevPlot.index.isin(['A1-2', 'A1-1', 'A2-2', 'A2-1'])].copy()
    GBelev_A1_2_A2_1.sort_values(by='mpY', inplace=True)
    startX = gradeBeamElevPlot.loc['A1-2', 'mpY']
    GBelev_A1_2_A2_1['plotX'] = gradeBeamElevPlot['mpY'] - startX
    GBelev_A1_2_A2_1['long_beam'] = 'A1-2 - A2-1'

    # Grade Beam A1-3 - A2-3
    GBelev_A1_3_A2_3 = gradeBeamElevPlot.loc[gradeBeamElevPlot.index.isin(['A1-3', 'A1-4', 'A2-4', 'A2-3'])].copy()
    GBelev_A1_3_A2_3.sort_values(by='mpY', inplace=True)
    startX = gradeBeamElevPlot.loc['A1-3', 'mpY']
    GBelev_A1_3_A2_3['plotX'] = gradeBeamElevPlot['mpY'] - startX
    GBelev_A1_3_A2_3['long_beam'] = 'A1-3 - A2-3'

    # Grade Beam A4-2 - A3-31
    GBelev_A4_2_A3_1 = gradeBeamElevPlot.loc[gradeBeamElevPlot.index.isin(['A4-2', 'A4-1', 'A3-2', 'A3-1'])].copy()
    GBelev_A4_2_A3_1.sort_values(by='mpY', inplace=True)
    startX = gradeBeamElevPlot.loc['A4-2', 'mpY']
    GBelev_A4_2_A3_1['plotX'] = gradeBeamElevPlot['mpY'] - startX
    GBelev_A4_2_A3_1['long_beam'] = 'A4-2 - A3-1'

    # Grade Beam A4-2 - A3-31
    GBelev_A4_3_A3_4 = gradeBeamElevPlot.loc[gradeBeamElevPlot.index.isin(['A4-3', 'A4-4', 'A3-3', 'A3-4'])].copy()
    GBelev_A4_3_A3_4.sort_values(by='mpY', inplace=True)
    startX = gradeBeamElevPlot.loc['A4-2', 'mpY']
    GBelev_A4_3_A3_4['plotX'] = gradeBeamElevPlot['mpY'] - startX
    GBelev_A4_3_A3_4['long_beam'] = 'A4-3 - A3-4'

    #B Pod Grade Beams
    # Grade Beam B3-4 - B2-4
    GBelev_B3_4_B2_4 = gradeBeamElevPlot.loc[gradeBeamElevPlot.index.isin(['B3-2', 'B3-1', 'B2-2', 'B2-3', 'B2-4'])].copy()
    GBelev_B3_4_B2_4.sort_values(by='mpX', inplace=True)
    startX = gradeBeamElevPlot.loc['B3-2', 'mpX']
    GBelev_B3_4_B2_4['plotX'] = gradeBeamElevPlot['mpX'] - startX
    GBelev_B3_4_B2_4['long_beam'] = 'B3-2 - B2-4'

    # Grade Beam B3-3 - B2-1
    GBelev_B3_3_B2_1 = gradeBeamElevPlot.loc[gradeBeamElevPlot.index.isin(['B3-3', 'B3-4', 'B2-6', 'B2-5', 'B2-1'])].copy()
    GBelev_B3_3_B2_1.sort_values(by='mpX', inplace=True)
    startX = gradeBeamElevPlot.loc['B3-3', 'mpX']
    GBelev_B3_3_B2_1['plotX'] = gradeBeamElevPlot['mpX'] - startX
    GBelev_B3_3_B2_1['long_beam'] = 'B3-3 - B2-1'

    # Grade Beam B1-2 - B2-4
    GBelev_B1_2_B2_4 = gradeBeamElevPlot.loc[gradeBeamElevPlot.index.isin(['B1-2', 'B1-1', 'B2-1', 'B2-4'])].copy()
    GBelev_B1_2_B2_4.sort_values(by='mpY', inplace=True)
    startX = gradeBeamElevPlot.loc['B1-2', 'mpY']
    GBelev_B1_2_B2_4['plotX'] = gradeBeamElevPlot['mpY'] - startX
    GBelev_B1_2_B2_4['long_beam'] = 'B1-2 - B2-4'

    # Grade Beam B1-3 - B2-3
    GBelev_B1_3_B2_3 = gradeBeamElevPlot.loc[gradeBeamElevPlot.index.isin(['B1-3', 'B1-4', 'B2-5', 'B2-3'])].copy()
    GBelev_B1_3_B2_3.sort_values(by='mpY', inplace=True)
    startX = gradeBeamElevPlot.loc['B1-3', 'mpY']
    GBelev_B1_3_B2_3['plotX'] = gradeBeamElevPlot['mpY'] - startX
    GBelev_B1_3_B2_3['long_beam'] = 'B1-3 - B2-3'

    # Grade Beam B4-2 - B3-1
    GBelev_B4_2_B3_1 = gradeBeamElevPlot.loc[gradeBeamElevPlot.index.isin(['B4-2', 'B4-1', 'B3-4', 'B3-1'])].copy()
    GBelev_B4_2_B3_1.sort_values(by='mpY', inplace=True)
    startX = gradeBeamElevPlot.loc['B4-2', 'mpY']
    GBelev_B4_2_B3_1['plotX'] = gradeBeamElevPlot['mpY'] - startX
    GBelev_B4_2_B3_1['long_beam'] = 'B4-2 - B3-1'

    # Grade Beam B4-3 - B3-2
    GBelev_B4_3_B3_2 = gradeBeamElevPlot.loc[gradeBeamElevPlot.index.isin(['B4-3', 'B4-4', 'B3-3', 'B3-2'])].copy()
    GBelev_B4_3_B3_2.sort_values(by='mpY', inplace=True)
    startX = gradeBeamElevPlot.loc['B4-3', 'mpY']
    GBelev_B4_3_B3_2['plotX'] = gradeBeamElevPlot['mpY'] - startX
    GBelev_B4_3_B3_2['long_beam'] = 'B4-3 - B3-2'

    # Grade Beam DF
    df_GradeBeams = pd.concat([GBelev_A3_4_A2_1, GBelev_A3_3_A2_2, GBelev_A1_2_A2_1, GBelev_A1_3_A2_3, GBelev_A4_2_A3_1, GBelev_A4_3_A3_4,
                            GBelev_B3_4_B2_4, GBelev_B3_3_B2_1, GBelev_B1_2_B2_4, GBelev_B1_3_B2_3, GBelev_B4_2_B3_1, GBelev_B4_3_B3_2])
    df_GradeBeams = df_GradeBeams.drop(columns=['mpX', 'mpY'])
    columns = ['long_beam', 'plotX'] + [col for col in df_GradeBeams.columns if col not in ['long_beam', 'plotX']]
    df_GradeBeams = df_GradeBeams[columns]

    # Grade Beam Elevation differences
    gradeBeam_diff = df_GradeBeams.groupby('long_beam').apply(lambda x: x.iloc[:, 2:].max() - x.iloc[:, 2:].min()).mul(12)

    return df_GradeBeams, gradeBeam_diff

# Line styles for beam plots
def plot_beamStyles(beamInfo, beamDiff, beamSlope, beamSlopeProj, floorDiffElev):
    #---------BEAM Plotting Styles--------------------------------
    # Calculate the direction of arrow of each beam
    beamDirLabels = beamInfo[['beamName','beamDir']].set_index(['beamName'])
    beamDir = pd.DataFrame(np.where(beamDiff >= 0, 0, 180), index = beamDiff.index, columns = beamDiff.columns)
    beamDir = beamDirLabels.join(beamDir).dropna()

    # Add 90 degrees to the vertical columns, leave horizontal columns as is
    cols = beamDir.columns[1:]
    for col in cols:
        beamDir.loc[beamDir['beamDir'] != 'h', col] -= 90
    
    beamDir = beamDir.drop(columns=['beamDir'])
    beamDir.columns = pd.to_datetime(beamDir.columns).astype(str)

    # Create dataframe for conditional text color for differental settlement values
    conditions = [abs(beamDiff)>0, abs(beamDiff)==0]
    choices = ['triangle-right', 'circle-open']
    beamSymbol = pd.DataFrame(np.select(conditions, choices, default='x'), index = beamDiff.index, columns = beamDiff.columns)#.replace('nan','x')

    # Create dataframe for conditional text color for differental settlement values
    conditions = [abs(beamDiff)<1.5, (abs(beamDiff)>=1.5) & (abs(beamDiff)<2), abs(beamDiff)>=2]
    choices = ['black', 'orange', 'red']
    beamDiffColor = pd.DataFrame(np.select(conditions, choices, default='blue'), index = beamDiff.index, columns = beamDiff.columns)#.replace('nan','blue')

    # Create dataframe for conditional text color for differental settlement slope values
    conditions = [abs(beamSlope)<(1/32), (abs(beamSlope)>=(1/32)) & (abs(beamSlope)<(1/16)), (abs(beamSlope)>=(1/16)) & (abs(beamSlope)<(1/8)), abs(beamDiff)>=(1/8)]
    choices = ['black','gold', 'orange', 'red']
    beamSlopeColor = pd.DataFrame(np.select(conditions, choices, default='blue'), index = beamDiff.index, columns = beamDiff.columns)#.replace('nan','blue')
    
    # Create dataframe for conditional text color for differental settlement slope values
    conditions = [abs(beamSlopeProj)<(1/32), ((abs(beamSlopeProj)>=(1/32)) & (abs(beamSlopeProj)<(1/16))), ((abs(beamSlopeProj)>=(1/16)) & (abs(beamSlopeProj)<(1/8))), abs(beamSlopeProj)>=(1/8)]
    choices = ['green','teal', 'blue', 'purple']
    beamSlopeProjColor = pd.DataFrame(np.select(conditions, choices, default='blue'), index = beamSlopeProj.index, columns = beamSlopeProj.columns)#.replace('nan','blue')
    return beamDirLabels, beamDir, beamSymbol, beamDiffColor, beamSlopeColor, beamSlopeProjColor

# Line styles for floor plots
def plot_floorStyles(beamDirLabels, beamInfo, floorDiff, floorDiffplot, floorSlope, floorSlopeplot, gradeBeamDiff):
    #-----------FLOOR ANNOTATIONS------------------------------
    # Calculate the direction of arrow of the floor
    floorDir = pd.DataFrame(np.where(floorDiff >= 0, 0, 180), index = floorDiff.index, columns = floorDiff.columns)
    floorDir = beamDirLabels.join(floorDir).dropna()

    # Add 90 degrees to the vertical columns, leave horizontal columns as is - for the floor
    cols = floorDir.columns[1:]
    for col in cols:
        floorDir.loc[floorDir['beamDir'] != 'h', col] -= 90
        
    floorDir = floorDir.drop(columns=['beamDir'])
    floorDir.columns = pd.to_datetime(floorDir.columns).astype(str)

    # Create dataframe for conditional marker symbol for floor differental settlement
    conditions = [abs(floorDiff.round(2))>0, abs(floorDiff.round(2))==0]
    choices = ['triangle-right','circle-open']
    floorSymbol = pd.DataFrame(np.select(conditions, choices, default='x'), index = floorDiff.index, columns = floorDiff.columns)#.replace('nan','x')
    floorSymbolplot = beamInfo[['beamName', 'arrowX', 'arrowY']].dropna().set_index(['beamName']).join(floorSymbol)

    # Create dataframe for conditional text color for floor differental settlement values
    conditions = [abs(floorDiff)<1.5, (abs(floorDiff)>=1.5) & (abs(floorDiff)<2), abs(floorDiff)>=2]
    choices = ['black', 'orange', 'red']
    floorDiffColor = pd.DataFrame(np.select(conditions, choices, default='blue'), index = floorDiff.index, columns = floorDiff.columns)#.replace('nan','blue')
    floorDiffColorplot = floorDiffplot.join(floorDiffColor, rsuffix='_color')

    conditions = [abs(gradeBeamDiff)<1.5, (abs(gradeBeamDiff)>=1.5) & (abs(gradeBeamDiff)<2), abs(gradeBeamDiff)>=2]
    choices = ['black', 'orange', 'red']
    gradeBeamDiffColor = pd.DataFrame(np.select(conditions, choices, default='blue'), index = gradeBeamDiff.index, columns = gradeBeamDiff.columns)#.replace('nan','blue')

    # Create dataframe for conditional text color for differental settlement slope values
    conditions = [abs(floorSlope)<(1/32), ((abs(floorSlope)>=(1/32)) & (abs(floorSlope)<(1/16))), ((abs(floorSlope)>=(1/16)) & (abs(floorSlope)<(1/8))), abs(floorSlope)>=(1/8)]
    choices = ['black','gold', 'orange', 'red']
    floorSlopeColor = pd.DataFrame(np.select(conditions, choices, default='blue'), index = floorSlope.index, columns = floorSlope.columns)#.replace('nan','blue')
    floorSlopeColorplot = floorSlopeplot.join(floorSlopeColor, rsuffix='_color')
    return floorDir, floorSymbolplot, floorDiffColor, floorDiffColorplot, floorSlopeColorplot, gradeBeamDiffColor
    
# Plot annotations
def plot_annotations():
    #----------PLOT NOTES AND ANNOTATIONS-----------------------
    beamDiffAnno = list([
        dict(text="Differental Settlement less than 1.5 inches",
             x=1, xref="paper", xanchor="right",
             y=1.09, yref="paper", yanchor="bottom",
             align="right", 
             showarrow=False, 
             font = dict(
                 color = 'black')),
        dict(text="Differental Settlement between 1.5 and 2.0 inches",
             x=1, xref="paper", xanchor="right",
             y=1.05, yref="paper", yanchor="bottom",
             align="right", 
             showarrow=False, 
             font = dict(
                 color = 'orange')),
        dict(text="Differental Settlement greater than 2.0 inches",
             x=1, xref="paper", xanchor="right",
             y=1.01, yref="paper", yanchor="bottom",
             align="right", 
             showarrow=False, 
             font = dict(
                 color = 'red')),
       dict(text="Note: Arrows point in the direction of increased settlement.",
            x=1, xref="paper", xanchor="right",
            y=-0.15, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False, 
            font = dict(
                color = 'black')
           )
    ])

    beamSlopeAnno = list([
       dict(text="Differental Slope less than 1/32 inch per foot",
            x=1, xref="paper", xanchor="right",
            y=1.13, yref="paper", yanchor="bottom",
            align="right",
            showarrow=False, 
            font = dict(
                color = 'black')
           ),
       dict(text="Differental Slope between 1/32 and 1/16 inch per foot",
            x=1, xref="paper", xanchor="right",
            y=1.09, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False,
            font = dict(
                color = 'gold')
           ),
       dict(text="Differental Slope between 1/16 and 1/8 inch per foot", 
            x=1, xref="paper", xanchor="right",
            y=1.05, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False, 
            font = dict(
                color = 'orange')
           ),
       dict(text="Differental Slope greater than 1/8 inch per foot",
            x=1, xref="paper", xanchor="right",
            y=1.01, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False, 
            font = dict(
                color = 'red')
           ),
       dict(text="Note: Arrows point in the direction of increased settlement.",
            x=1, xref="paper", xanchor="right",
            y=-0.15, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False, 
            font = dict(
                color = 'black')
           )
   ])
    
    diffAnno = list([
        dict(text="Differental Floor Elevation less than 1.5 inches",
             x=1, xref="paper", xanchor="right",
             y=1.09, yref="paper", yanchor="bottom",
             align="right", 
             showarrow=False, 
             font = dict(
                 color = 'black')),
        dict(text="Differental Floor Elevation between 1.5 and 2.0 inches",
             x=1, xref="paper", xanchor="right",
             y=1.05, yref="paper", yanchor="bottom",
             align="right", 
             showarrow=False, 
             font = dict(
                 color = 'orange')),
        dict(text="Differental Floor Elevation greater than 2.0 inches",
             x=1, xref="paper", xanchor="right",
             y=1.01, yref="paper", yanchor="bottom",
             align="right", 
             showarrow=False, 
             font = dict(
                 color = 'red')),
       dict(text="Note: Arrows point in the direction of lower elevation.",
            x=1, xref="paper", xanchor="right",
            y=-0.2, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False, 
            font = dict(
                color = 'black')
           )
    ])

    slopeAnno = list([
       dict(text="Differental Floor Slope less than 1/32 inch per foot",
            x=1, xref="paper", xanchor="right",
            y=1.13, yref="paper", yanchor="bottom",
            align="right",
            showarrow=False, 
            font = dict(
                color = 'black')
           ),
       dict(text="Differental Floor Slope between 1/32 and 1/16 inch per foot",
            x=1, xref="paper", xanchor="right",
            y=1.09, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False,
            font = dict(
                color = 'gold')
           ),
       dict(text="Differental Floor Slope between 1/16 and 1/8 inch per foot", 
            x=1, xref="paper", xanchor="right",
            y=1.05, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False, 
            font = dict(
                color = 'orange')
           ),
       dict(text="Differental Floor Slope greater than 1/8 inch per foot",
            x=1, xref="paper", xanchor="right",
            y=1.01, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False, 
            font = dict(
                color = 'red')
           ),
       dict(text="Note: Arrows point in the direction of lower elevation. Slopes are rounded, arrows show difference in elevation.",
            x=1, xref="paper", xanchor="right",
            y=-0.2, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False, 
            font = dict(
                color = 'black')
           )
   ])
    
    plot3dAnno = list([
        dict(text="<span style='color:black'>Observed Beam Slope less than 1/32 in/ft</span>",
                x=0.6, xref="paper", xanchor="right",
                y=-0.05, yref="paper", yanchor="bottom",
                align="right",
                showarrow=False, 
                font = dict(
                    size = 14,
                    color = 'grey')
            ),
        dict(text="<span style='color:gold'>Observed Beam Slope between 1/32 and 1/16 in/ft</span>",
                x=1, xref="paper", xanchor="right",
                y=-0.05, yref="paper", yanchor="bottom",
                align="right",
                showarrow=False, 
                font = dict(
                    size = 14,
                    color = 'grey')
            ),
        dict(text="<span style='color:orange'>Observed Beam Slope between 1/16 and 1/8 in/ft</span>",
                x=.6, xref="paper", xanchor="right",
                y=-0.08, yref="paper", yanchor="bottom",
                align="right",
                showarrow=False, 
                font = dict(
                    size = 14,
                    color = 'grey')
            ),
        dict(text="<span style='color:red'>Observed Beam Slope greater than 1/8 in/ft</span>",
                x=1, xref="paper", xanchor="right",
                y=-0.08, yref="paper", yanchor="bottom",
                align="right",
                showarrow=False, 
                font = dict(
                    size = 14,
                    color = 'grey')
            )])

    plot3dAnnoDiff = list([
        dict(text="Differental less than 1.5 inches",
                x=0.6, xref="paper", xanchor="right",
                y=-0.05, yref="paper", yanchor="bottom",
                align="right",
                showarrow=False, 
                font = dict(
                    size = 14,
                    color = 'black')
            ),
        dict(text="Differental between 1.5 and 2.0 inches",
                x=1, xref="paper", xanchor="right",
                y=-0.05, yref="paper", yanchor="bottom",
                align="right",
                showarrow=False, 
                font = dict(
                    size = 14,
                    color = 'orange')
            ),
        dict(text="Differental greater than 2.0 inches",
                x=.6, xref="paper", xanchor="right",
                y=-0.08, yref="paper", yanchor="bottom",
                align="right",
                showarrow=False, 
                font = dict(
                    size = 14,
                    color = 'red')
            )
    ])

    # column: color - assign each monitor point a specifc color
    color_dict = {
    'A1-1': '#1b9e77', 'A1-2': '#d95f02', 'A1-3': '#7570b3', 'A1-4': '#e7298a',
    'A2-1': '#1b9e77', 'A2-2': '#d95f02', 'A2-3': '#7570b3', 'A2-4': '#e7298a', 'A2-5': '#66a61e','A2-6': '#e6ab02',
    'A3-1': '#1b9e77', 'A3-2': '#d95f02', 'A3-3': '#7570b3', 'A3-4': '#e7298a',
    'A4-1': '#1b9e77', 'A4-2': '#d95f02', 'A4-3': '#7570b3', 'A4-4': '#e7298a',
    'B1-1': '#1b9e77', 'B1-2': '#d95f02', 'B1-3': '#7570b3', 'B1-4': '#e7298a',
    'B2-1': '#1b9e77', 'B2-2': '#d95f02', 'B2-3': '#7570b3', 'B2-4': '#e7298a', 'B2-5': '#66a61e','B2-6': '#e6ab02',
    'B3-1': '#1b9e77', 'B3-2': '#d95f02', 'B3-3': '#7570b3', 'B3-4': '#e7298a',
    'B4-1': '#1b9e77', 'B4-2': '#d95f02', 'B4-3': '#7570b3', 'B4-4': '#e7298a'}

    color_dictBeams = {
        'A1-1 - A2-2':'#006666', 'A1-2 - A1-1':'#009999', 'A1-3 - A1-2':'#00CCCC', 'A1-3 - A1-4':'#00FFFF',
        'A1-4 - A1-1':'#33FFFF', 'A1-4 - A2-4':'#65FFFF', 'A2-2 - A2-1':'#99FFFF', 'A2-3 - A2-1':'#B2FFFF',
        'A2-4 - A2-2':'#CBFFFF', 'A2-4 - A2-3':'#E5FFFF', 'A2-5 - A2-3':'#FFE5CB', 'A2-6 - A2-4':'#FFCA99',
        'A2-6 - A2-5':'#F100F1', 'A3-1 - A2-5':'#FF8E33', 'A3-2 - A2-6':'#FF6E00', 'A3-2 - A3-1':'#CC5500',
        'A3-3 - A3-2':'#993D00', 'A3-3 - A3-4':'#662700', 'A3-4 - A3-1':'#3D87FF', 'A4-1 - A3-2': '#2400D8',
        'A4-2 - A4-1':'#2857FF', 'A4-3 - A4-2':'#D8152F', 'A4-3 - A4-4':'#FF7856', 'A4-4 - A3-3':'#FF3D3D','A4-4 - A4-1':'#A50021', 
        'B1-1 - B2-1':'#006666', 'B1-2 - B1-1':'#009999', 'B1-3 - B1-2':'#65FFFF',
        'B1-3 - B1-4':'#00FFFF', 'B1-4 - B1-1':'#33FFFF', 'B1-4 - B2-5':'#00CCCC', 'B2-1 - A3-3':'#99FFFF',
        'B2-1 - B2-4':'#B2FFFF', 'B2-2 - B2-3':'#CBFFFF', 'B2-3 - B2-4':'#E5FFFF', 'B2-4 - A3-4':'#FFE5CB',
        'B2-5 - B2-1':'#FFCA99', 'B2-5 - B2-3':'#FFAD65', 'B2-6 - B2-2':'#500050', 'B2-6 - B2-5':'#BB00BB',
        'B3-1 - B2-2':'#CC5500', 'B3-2 - B3-1':'#993D00', 'B3-3 - B3-2':'#662700', 'B3-3 - B3-4':'#3D87FF',
        'B3-4 - B2-6':'#2400D8', 'B3-4 - B3-1':'#2857FF', 'B4-1 - B3-4':'#FFE5CB', 'B4-2 - B4-1':'#FF7856',
        'B4-3 - B4-2':'#FF3D3D', 'B4-3 - B4-4':'#A50021', 'B4-4 - B3-3':'#99FFFF', 'B4-4 - B4-1':'#D8152F'}

    # Identify the monitor point groupings based on the pod
    maps = {'A1':['A1-1', 'A1-2', 'A1-3', 'A1-4'],
        'A2':['A2-1', 'A2-2', 'A2-3', 'A2-4', 'A2-5','A2-6'],
        'A3':['A3-1', 'A3-2', 'A3-3', 'A3-4'],
        'A4':['A4-1', 'A4-2', 'A4-3', 'A4-4'],
       'B1':['B1-1', 'B1-2', 'B1-3', 'B1-4'],
        'B2':['B2-1', 'B2-2', 'B2-3', 'B2-4', 'B2-5','B2-6'],
        'B3':['B3-1', 'B3-2', 'B3-3', 'B3-4'],
        'B4':['B4-1', 'B4-2', 'B4-3', 'B4-4']}
    
    mapsPods = {'A':['A1-1', 'A1-2', 'A1-3', 'A1-4', 
                     'A2-1', 'A2-2', 'A2-3', 'A2-4', 'A2-5','A2-6',
                     'A3-1', 'A3-2', 'A3-3', 'A3-4',
                     'A4-1', 'A4-2', 'A4-3', 'A4-4'],
                'B':['B1-1', 'B1-2', 'B1-3', 'B1-4', 
                     'B2-1', 'B2-2', 'B2-3', 'B2-4', 'B2-5','B2-6',
                     'B3-1', 'B3-2', 'B3-3', 'B3-4',
                     'B4-1', 'B4-2', 'B4-3', 'B4-4']}
    
    mapsBeams = {'A':['A1-1 - A2-2','A1-2 - A1-1','A1-3 - A1-2','A1-3 - A1-4',
                      'A1-4 - A1-1','A1-4 - A2-4','A2-2 - A2-1','A2-3 - A2-1',
                      'A2-4 - A2-2','A2-4 - A2-3','A2-5 - A2-3','A2-6 - A2-4',
                      'A2-6 - A2-5','A3-1 - A2-5','A3-2 - A2-6','A3-2 - A3-1',
                      'A3-3 - A3-2','A3-3 - A3-4','A3-4 - A3-1','A4-1 - A3-2',
                      'A4-2 - A4-1','A4-3 - A4-2','A4-3 - A4-4','A4-4 - A3-3','A4-4 - A4-1'],
                'B':['B1-1 - B2-1','B1-2 - B1-1','B1-3 - B1-2','B1-3 - B1-4',
                     'B1-4 - B1-1','B1-4 - B2-5','B2-1 - B2-4','B2-2 - B2-3',
                     'B2-3 - B2-4','B2-5 - B2-1','B2-5 - B2-3','B2-6 - B2-2',
                     'B2-6 - B2-5','B3-1 - B2-2','B3-2 - B3-1','B3-3 - B3-2',
                     'B3-3 - B3-4','B3-4 - B2-6','B3-4 - B3-1','B4-1 - B3-4',
                     'B4-2 - B4-1','B4-3 - B4-2','B4-3 - B4-4','B4-4 - B3-3','B4-4 - B4-1'],
                'A-B':['B2-1 - A3-3', 'B2-4 - A3-4']}
    
    mapsGradeBeams = {'A':['A1-2 - A2-1', 'A1-3 - A2-3', 'A3-3 - A2-2', 
                           'A3-4 - A2-1', 'A4-2 - A3-1', 'A4-3 - A3-4'],
                    'B':['B1-2 - B2-4', 'B1-3 - B2-3', 'B3-2 - B2-4',
                         'B3-3 - B2-1', 'B4-2 - B3-1', 'B4-3 - B3-2']}
    
    return beamDiffAnno, beamSlopeAnno, diffAnno, plot3dAnnoDiff, slopeAnno, plot3dAnno, color_dict, color_dictBeams, maps, mapsBeams, mapsPods, mapsGradeBeams

# Plot Cumulative Settlement
def plot_cumulative_settlement(settlement, settlementProj, color_dict, maps):
    df = settlement 

    # plotly figure
    fig = go.Figure()

    for column in df:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[column],
                name= column,
                mode = 'lines+markers',
                marker_color = color_dict[column]
            ))

    for column in settlementProj:
            fig.add_trace(go.Scatter(
                x=settlementProj.index,
                y=settlementProj[column],
                name= column + ' Projection',
                mode = 'lines+markers',
                marker_color = color_dict[column],
                line = dict(
                    width = 1.5,
                    dash = 'dash'),
                marker = dict(
                    size=7.5,
                    symbol='star'),
            ))
            
    fig.update_layout(xaxis_title="Survey Date",
                    yaxis_title="Cumulative Settlement [ft]")

    # groups and trace visibilities
    group = []
    vis = []
    visList = []
    for m in maps.keys():
        for col in df.columns:
            if col in maps[m]:
                vis.append(True)
            else:
                vis.append(False)
        group.append(m)
        visList.append(vis)
        vis = []

    # buttons for each group
    buttons = []
    for i, g in enumerate(group):
        button =  dict(label=g,
                    method = 'restyle',
                        args = ['visible',visList[i]])
        buttons.append(button)

    # buttons
    buttons = [{'label': 'All Points',
                    'method': 'restyle',
                    'args': ['visible', [True, True, True, True, True, True]]}] + buttons

                

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
        height = 600
    )
    return fig

def plot_elev_timeseries(floorElevPlot, color_dict, maps):
    df = floorElevPlot.drop(columns=['mpX', 'mpY']).transpose() 

    # plotly figure
    fig = go.Figure()

    for column in df:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[column],
                name= column,
                mode = 'lines+markers',
                marker_color = color_dict[column]
            ))
            
    fig.update_layout(xaxis_title="Survey Date",
                    yaxis_title="Elevation [ft]")

    # groups and trace visibilities
    group = []
    vis = []
    visList = []
    for m in maps.keys():
        for col in df.columns:
            if col in maps[m]:
                vis.append(True)
            else:
                vis.append(False)
        group.append(m)
        visList.append(vis)
        vis = []

    # buttons for each group
    buttons = []
    for i, g in enumerate(group):
        button =  dict(label=g,
                    method = 'restyle',
                        args = ['visible',visList[i]])
        buttons.append(button)

    # buttons
    buttons = [{'label': 'All Points',
                    'method': 'restyle',
                    'args': ['visible', [True, True, True, True, True, True]]}] + buttons

                

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
        height = 600
    )
    return fig

# Plot Delta Settlement
def plot_delta_settlement(settlement_delta, color_dict, maps):
     # Plot Change in Settlement between each survey
    df = settlement_delta #change based on dataframe to plot

    # plotly figure
    fig = go.Figure()

    for column in df:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[column],
            name= column,
            mode = 'lines+markers',
            marker_color = color_dict[column]
        ))

    fig.update_layout(xaxis_title="Survey Date",
                 yaxis_title="Settlement Change [in]")

    # groups and trace visibilities
    group = []
    vis = []
    visList = []
    for m in maps.keys():
        for col in df.columns:
            if col in maps[m]:
                vis.append(True)
            else:
                vis.append(False)
        group.append(m)
        visList.append(vis)
        vis = []

    # buttons for each group
    buttons = []
    for i, g in enumerate(group):
        button =  dict(label=g,
                    method = 'restyle',
                        args = ['visible',visList[i]])
        buttons.append(button)

    buttons = [{'label': 'All Points',
                    'method': 'restyle',
                    'args': ['visible', [True, True, True, True, True, True]]}] + buttons

                        

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
        height = 600
    )
    return fig

# Plot settlement rate between each survey
def plot_settlementRate(settlement_rate, color_dict, maps):
    df = settlement_rate

    fig = go.Figure()

    for column in df:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[column],
                name= column,
                mode = 'lines+markers',
                marker_color = color_dict[column]
            ))

    fig.update_layout(
            xaxis_title="Survey Date",
            yaxis_title="Settlement [in/year]",
            yaxis= dict(range=[0,6])
        )

    # groups and trace visibilities
    group = []
    vis = []
    visList = []
    for m in maps.keys():
        for col in df.columns:
            if col in maps[m]:
                vis.append(True)
            else:
                vis.append(False)
        group.append(m)
        visList.append(vis)
        vis = []

    # buttons for each group
    buttons = []
    for i, g in enumerate(group):
        button =  dict(label=g,
                    method = 'restyle',
                        args = ['visible',visList[i]])
        buttons.append(button)

    buttons = [{'label': 'All Points',
                    'method': 'restyle',
                    'args': ['visible', [True, True, True, True, True, True]]}] + buttons

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
    )
    return fig

# Plot settlement rate between each survey
def floorDifferential(floorDiffElev, floorElevPlot, color_dictBeams, mapsBeams):
    last_column = floorElevPlot.columns[-1]
    date_break = pd.to_datetime(last_column, format='%Y-%m-%d')

    df = floorDiffElev.transpose()
    df= df.drop('2022-01-07').drop(['B2-1 - A3-3', 'B2-4 - A3-4'], axis = 1)
    df.index = pd.to_datetime(df.index)

    # Split the data based on the date condition
    before_date = df[df.index <= date_break]
    after_date = df[df.index >= date_break]

    plotGroups = {}
    greater2 = df.columns[df.gt(2).any()]
    df_filtered = df[greater2]
    group_A = [col for col in df_filtered.columns if 'A' in col]
    group_B = [col for col in df_filtered.columns if 'B' in col]
    plotGroups['All > 2"'] = df_filtered.columns.tolist()
    plotGroups['A Pod > 2"'] = group_A
    plotGroups['B Pod > 2"'] = group_B


    fig = go.Figure()

    for column in df:
            # Define line style based on date condition
            line_style = ['solid' if date < date_break else 'dash' for date in df.index]

            # Add trace for the solid line (before the break date)
            fig.add_trace(go.Scatter(
                x=before_date.index,
                y=before_date[column],
                name= column,
                mode='lines+markers',
                line=dict(dash='solid'),  # Solid line
                marker_color=color_dictBeams[column]
            ))

            # Add trace for the dashed line (after the break date)
            fig.add_trace(go.Scatter(
                x=after_date.index,
                y=after_date[column],
                name=column,
                mode='lines+markers',
                line=dict(dash='dash'),  # Dashed line
                marker_color=color_dictBeams[column],
                marker = dict(
                        size=7.5,
                        symbol='star')
            ))
            
    fig.add_shape(
            type='line',
            x0=df.index.min(),  # Start x position (use the min index)
            x1=df.index.max(),  # End x position (use the max index)
            y0=2,  # Start y position
            y1=2,  # End y position (horizontal line at y=2)
            line=dict(
                color='red',
                width=5,
                dash='dash',  # Dashed line
            )
        )

    fig.update_layout(
            xaxis_title="Survey Date",
            yaxis_title="Differential Floor Elevation [in]",
            # #yaxis= dict(range=[0,6]),
            # font=dict(
            #     size=26,  # Set the font size here
            #     color="Black"
            # )
        )

    # Initialize visibility lists
    visList = []

    # Create visibility lists for each group based on filtered columns
    for group_name in plotGroups.keys():
        vis = [[True]*2 if col in plotGroups[group_name] else [False]*2 for col in df.columns]
        visFlat = [item for sublist in vis for item in sublist]
        visList.append(visFlat)

    # Create buttons for each group
    buttons = []
    for i, group_name in enumerate(plotGroups.keys()):
        button = dict(
            label=group_name,
            method='restyle',
            args=['visible', visList[i]]
        )
        
        buttons.append(button)

    # Add "All Points" button
    buttons = [{'label': 'All Points',
                'method': 'restyle',
                'args': ['visible', [True] * len(df.columns)]}] + buttons

    # Update layout with buttons
    fig.update_layout(
        updatemenus=[
            dict(
                type="dropdown",
                direction="down",
                buttons=buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom"
            )
        ]
    )
    return fig

# Plot differental settlement in plan view
def plot_DiffSettlement_plan(beamDiffplot, beamInfo, beamDiffColor, beamSymbol, beamDir, beamDiffAnno):
    df = beamDiffplot

    #create a figure from the graph objects (not plotly express) library
    fig = go.Figure()

    buttons = []
    dates = []
    i = 0

    # Plot the beam locations as lines
    for (startX, endX, startY, endY) in zip(beamInfo['startX'], beamInfo['endX'], beamInfo['startY'], beamInfo['endY']):
        fig.add_trace(go.Scatter(
            x=[startX, endX],
            y=[startY, endY],
            mode='lines',
            line = dict(
                color = 'black',
                width = 1.5,
                dash = 'solid'),
            hoverinfo='skip',
            showlegend=False
        ))

    # Plot the Marker Point (MP) labels in grey
    fig.add_trace(go.Scatter(
        x=beamInfo['labelX'],
        y=beamInfo['labelY'],
        text=beamInfo['MP_W_S'],
        mode = 'text',
        textfont = dict(
            size = 12,
            color = 'grey'),
        hoverinfo='skip',
        showlegend=False
    ))

    # Create a list to store the visibility lists for each dataframe
    all_args = []
    vis = []
    visList = []


    #iterate through columns in dataframe (not including the year column)
    for column in df.columns[2:]:
        # Beam Differental Settlement
        fig.add_trace(go.Scatter(
            x=df['beamX'],
            y=df['beamY'],
            text=abs(df[column].values.round(2)),
            mode = 'text',
            #name = column, 
            textfont = dict(
                size = 16,
                color = beamDiffColor[column].values
                ),
            hoverinfo='skip',
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (column==df.columns[len(df.columns)-1])
        ))
            
            # Beam Differental Settlement Arrow - pointing in direction of low end 
        fig.add_trace(go.Scatter(
            x=beamInfo['arrowX'],
            y=beamInfo['arrowY'],
            mode = 'markers',
            #name = column,
            marker=dict(
                color='red',
                size=10,
                symbol=beamSymbol[column].values,
                angle=beamDir[column].values),
            hoverinfo='skip',
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (column==df.columns[len(df.columns)-1])
        ))
            

    # groups and trace visibilities
    vis = []
    visList = []

    for  i, col in enumerate(df.columns[2:]):
        vis = [True]*(len(df.index)+2) + ([False]*i*2 + [True]*2 + [False]*(len(df.columns)-2-(i+1))*2)
        visList.append(vis)
        vis = []


    # buttons for each group
    buttons = []
    for idx, col in enumerate(df.columns[2:]):
        buttons.append(
            dict(
                label = col,
                method = "update",
                args=[{"visible": visList[idx]}])
        )

    buttons = [{'label': 'Select Survey Date',
                    'method': 'restyle',
                    'args': ['visible', [False]*152]}] + buttons

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
        annotations = beamDiffAnno,
        height = 600
        #title = 'Differental Settlement [in] between Monitoring Points'
    )

    # Set axes ranges
    fig.update_xaxes(range=[-25, 415])
    fig.update_yaxes(range=[-15, 140])
    return fig

# Plot differental settlement slope in plan view
def plot_SlopeSettlement_plan(beamSlopeplot, beamInfo, beamSlopeColor, beamSymbol, beamDir, beamSlopeAnno):
    df = beamSlopeplot

    #create a figure from the graph objects (not plotly express) library
    fig = go.Figure()

    buttons = []
    dates = []
    i = 0

    # Plot the beam locations as lines
    for (startX, endX, startY, endY) in zip(beamInfo['startX'], beamInfo['endX'], beamInfo['startY'], beamInfo['endY']):
        fig.add_trace(go.Scatter(
            x=[startX, endX],
            y=[startY, endY],
            mode='lines',
            line = dict(
                color = 'black',
                width = 1.5,
                dash = 'solid'),
            hoverinfo='skip',
            showlegend=False
        ))

    # Plot the Marker Point (MP) labels in grey
    fig.add_trace(go.Scatter(
        x=beamInfo['labelX'],
        y=beamInfo['labelY'],
        text=beamInfo['MP_W_S'],
        mode = 'text',
        textfont = dict(
            size = 12,
            color = 'grey'),
        hoverinfo='skip',
        showlegend=False
    ))

    # Create a list to store the visibility lists for each dataframe
    all_args = []
    vis = []
    visList = []


    #iterate through columns in dataframe (not including the year column)
    for column in df.columns[3:]:
        # Beam Differental Settlement
        fig.add_trace(go.Scatter(
            x=df['beamX'],
            y=df['beamY'],
            text=abs(df[column].values.round(2)),
            mode = 'text',
            #name = column, 
            textfont = dict(
                size = 16,
                color = beamSlopeColor[column].values),
            hoverinfo='skip',
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (column==df.columns[len(df.columns)-1])
        ))
            
            # Beam Differental Settlement Arrow - pointing in direction of low end 
        fig.add_trace(go.Scatter(
            x=beamInfo['arrowX'],
            y=beamInfo['arrowY'],
            mode = 'markers',
            #name = column,
            marker=dict(
                color='red',
                size=10,
                symbol=beamSymbol[column].values,
                angle=beamDir[column].values),
            hoverinfo='skip',
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (column==df.columns[len(df.columns)-1])
        ))
            

    # groups and trace visibilities
    vis = []
    visList = []

    for  i, col in enumerate(df.columns[3:]):
        vis = [True]*(len(df.index)+2) + ([False]*i*2 + [True]*2 + [False]*(len(df.columns)-(i+1))*2)
        visList.append(vis)
        vis = []


    # buttons for each group
    buttons = []
    for idx, col in enumerate(df.columns[3:]):
        buttons.append(
            dict(
                label = col,
                method = "update",
                args=[{"visible": visList[idx]}])
        )

    buttons = [{'label': 'Select Survey Date',
                    'method': 'restyle',
                    'args': ['visible', [False]*152]}] + buttons

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
        annotations = beamSlopeAnno,
        height = 600
        #title = 'Differental Slope [in/ft]'
    )

    # Set axes ranges
    fig.update_xaxes(range=[-25, 415])
    fig.update_yaxes(range=[-15, 140])
    return fig

# Plot the lug elevations
def plot_lugElev_plan(lugElevPlot, beamInfo):
    df = lugElevPlot

    #create a figure from the graph objects (not plotly express) library
    fig = go.Figure()

    buttons = []
    dates = []
    i = 0

    # Plot the beam locations as lines
    for (startX, endX, startY, endY) in zip(beamInfo['startX'], beamInfo['endX'], beamInfo['startY'], beamInfo['endY']):
        fig.add_trace(go.Scatter(
            x=[startX, endX],
            y=[startY, endY],
            mode='lines',
            line = dict(
                color = 'black',
                width = 1.5,
                dash = 'solid'),
            hoverinfo='skip',
            showlegend=False
        ))

    # Plot the Marker Point (MP) labels in grey
    fig.add_trace(go.Scatter(
        x=beamInfo['labelX'],
        y=beamInfo['labelY'],
        text=beamInfo['MP_W_S'],
        mode = 'text',
        textfont = dict(
            size = 10,
            color = 'grey'),
        hoverinfo='skip',
        showlegend=False
    ))

    # Create a list to store the visibility lists for each dataframe
    all_args = []
    vis = []
    visList = []

    #create custom color scale, red to blue through white
    custom_colors = ['#0000FF', '#FFFFFF', '#FF0000']

    #iterate through columns in dataframe (not including the year column)
    for column in df.columns[2:]: 
        # Floor Elevation 
        fig.add_trace(go.Scatter(
            mode = 'markers',
            x=df['mpX'],
            y=df['mpY'],
            text=df.index,
            name="",
            marker=dict(
                color = df[column].values,
                colorscale=custom_colors,
                colorbar=dict(title='Lug Elevation (ft)'),
                size = 10,
                line=dict(
                    color='black',
                    width=1.5
                )           
            ),
            hovertemplate=
            "<b>%{text}</b><br>" +
            "Lug Elev.: %{marker.color:,} ft" ,
            hoverlabel=dict(
                bgcolor = "white"
            ),
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (column==df.columns[len(df.columns)-1])
        ))
            

    # groups and trace visibilities
    vis = []
    visList = []

    for  i, col in enumerate(df.columns[2:]):
        vis = [True]*(54) + ([False]*i + [True] + [False]*((54)-2-(i+1)))
        visList.append(vis)
        vis = []


    # buttons for each group
    buttons = []
    for idx, col in enumerate(df.columns[2:]):
        buttons.append(
            dict(
                label = col,
                method = "update",
                args=[{"visible": visList[idx]}])
        )

    buttons = [{'label': 'Select Survey Date',
                    'method': 'restyle',
                    'args': ['visible', [False]]}] + buttons

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
    )

    # Set axes ranges
    fig.update_xaxes(range=[-25, 415])
    fig.update_yaxes(range=[-15, 140])
    return fig

# Lug to Floor Height at monitoring points (measurement of shims)
def plot_lugFloorHeight_plan(lugFloorPlot, beamInfo):
    df = lugFloorPlot

    fig = go.Figure()

    buttons = []
    dates = []
    i = 0

    # Plot the beam locations as lines
    for (startX, endX, startY, endY) in zip(beamInfo['startX'], beamInfo['endX'], beamInfo['startY'], beamInfo['endY']):
        fig.add_trace(go.Scatter(
            x=[startX, endX],
            y=[startY, endY],
            mode='lines',
            line = dict(
                color = 'black',
                width = 1.5,
                dash = 'solid'),
            hoverinfo='skip',
            showlegend=False
        ))

    # Plot the Marker Point (MP) labels in grey
    fig.add_trace(go.Scatter(
        x=beamInfo['labelX'],
        y=beamInfo['labelY'],
        text=beamInfo['MP_W_S'],
        mode = 'text',
        textfont = dict(
            size = 10,
            color = 'grey'),
        hoverinfo='skip',
        showlegend=False
    ))

    # Create a list to store the visibility lists for each dataframe
    all_args = []
    vis = []
    visList = []

    #create custom color scale, red to blue through white
    custom_colors = ['#0000FF', '#FFFFFF', '#FF0000']

    #iterate through columns in dataframe (not including the year column)
    for column in df.columns[2:]: 
        # Floor Elevation 
        fig.add_trace(go.Scatter(
            mode = 'markers',
            x=df['mpX'],
            y=df['mpY'],
            text=df.index,
            name="",
            marker=dict(
                color = df[column].values,
                colorscale=custom_colors,
                colorbar=dict(title='Lug to Floor Height (ft)'),
                size = 10,
                line=dict(
                    color='black',
                    width=1.5
                )           
            ),
            hovertemplate=
            "<b>%{text}</b><br>" +
            "Lug to Floor<br>Height: %{marker.color:,} ft" ,
            hoverlabel=dict(
                bgcolor = "white"
            ),
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (column==df.columns[len(df.columns)-1])
        ))
            

    # groups and trace visibilities
    vis = []
    visList = []

    for  i, col in enumerate(df.columns[2:]):
        vis = [True]*(54) + ([False]*i + [True] + [False]*((54)-2-(i+1)))
        visList.append(vis)
        vis = []


    # buttons for each group
    buttons = []
    for idx, col in enumerate(df.columns[2:]):
        buttons.append(
            dict(
                label = col,
                method = "update",
                args=[{"visible": visList[idx]}])
        )

    buttons = [{'label': 'Select Survey Date',
                    'method': 'restyle',
                    'args': ['visible', [False]]}] + buttons

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
    )

    # Set axes ranges
    fig.update_xaxes(range=[-25, 415])
    fig.update_yaxes(range=[-15, 140])
    return fig

# Lug to Floor Height at monitoring points (measurement of shims)
def plot_shimHeight_plan(shimElevPlot, beamInfo):
    df = shimElevPlot

    fig = go.Figure()

    buttons = []
    dates = []
    i = 0

    # Plot the beam locations as lines
    for (startX, endX, startY, endY) in zip(beamInfo['startX'], beamInfo['endX'], beamInfo['startY'], beamInfo['endY']):
        fig.add_trace(go.Scatter(
            x=[startX, endX],
            y=[startY, endY],
            mode='lines',
            line = dict(
                color = 'black',
                width = 1.5,
                dash = 'solid'),
            hoverinfo='skip',
            showlegend=False
        ))

    # Plot the Marker Point (MP) labels in grey
    fig.add_trace(go.Scatter(
        x=beamInfo['labelX'],
        y=beamInfo['labelY'],
        text=beamInfo['MP_W_S'],
        mode = 'text',
        textfont = dict(
            size = 10,
            color = 'grey'),
        hoverinfo='skip',
        showlegend=False
    ))

    # Create a list to store the visibility lists for each dataframe
    all_args = []
    vis = []
    visList = []

    #create custom color scale, red to blue through white
    custom_colors = ['#0000FF', '#FFFFFF', '#FF0000']

    #iterate through columns in dataframe (not including the year column)
    for column in df.columns[2:]: 
        # Floor Elevation 
        fig.add_trace(go.Scatter(
            mode = 'markers',
            x=df['mpX'],
            y=df['mpY'],
            text=df.index,
            name="",
            marker=dict(
                color = df[column].values,
                colorscale=custom_colors,
                colorbar=dict(title='Shim Height (in)'),
                size = 10,
                line=dict(
                    color='black',
                    width=1.5
                )           
            ),
            hovertemplate=
            "<b>%{text}</b><br>" +
            "Shim Height: %{marker.color:,} in" ,
            hoverlabel=dict(
                bgcolor = "white"
            ),
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (column==df.columns[len(df.columns)-1])
        ))
            

    # groups and trace visibilities
    vis = []
    visList = []

    for  i, col in enumerate(df.columns[2:]):
        vis = [True]*(54) + ([False]*i + [True] + [False]*((54)-2-(i+1)))
        visList.append(vis)
        vis = []


    # buttons for each group
    buttons = []
    for idx, col in enumerate(df.columns[2:]):
        buttons.append(
            dict(
                label = col,
                method = "update",
                args=[{"visible": visList[idx]}])
        )

    buttons = [{'label': 'Select Survey Date',
                    'method': 'restyle',
                    'args': ['visible', [False]]}] + buttons

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
    )

    # Set axes ranges
    fig.update_xaxes(range=[-25, 415])
    fig.update_yaxes(range=[-15, 140])
    return fig

# Differential Floor Elevations (inches) between monitoring points
def plot_floorDiffElev_plan(floorDiffColorplot, beamInfo, floorDiffplot, floorSymbolplot, floorDir, floorElevPlot, diffAnno):
    df = floorDiffColorplot

    fig = go.Figure()

    buttons = []
    dates = []
    i = 0

    # Plot the beam locations as lines
    for (startX, endX, startY, endY) in zip(beamInfo['startX'], beamInfo['endX'], beamInfo['startY'], beamInfo['endY']):
        fig.add_trace(go.Scatter(
            x=[startX, endX],
            y=[startY, endY],
            mode='lines',
            line = dict(
                color = 'black',
                width = 1.5,
                dash = 'solid'),
            hoverinfo='skip',
            showlegend=False
        ))

    # Plot the Marker Point (MP) labels in grey
    fig.add_trace(go.Scatter(
        x=beamInfo['labelX'],
        y=beamInfo['labelY'],
        text=beamInfo['MP_W_S'],
        mode = 'text',
        textfont = dict(
            size = 10,
            color = 'grey'),
        hoverinfo='skip',
        showlegend=False
    ))

    # Create a list to store the visibility lists for each dataframe
    all_args = []
    vis = []
    visList = []

    #create custom color scale, red to blue through white
    custom_colors = ['#0000FF', '#FFFFFF', '#FF0000']

    #iterate through columns in dataframe (not including the year column)
    for column in floorDiffplot.columns[2:]:
        # Floor Differental
        fig.add_trace(go.Scatter(
            x=df['beamX'],
            y=df['beamY'],
            text=abs(df[column].values.round(2)),
            customdata=df.index,
            name="",
            mode = 'text',
            textfont = dict(
                size = 10,
                color = df[f'{column}_color'].values 
                ),
            hovertemplate=
            "<b>%{customdata}</b><br>" +
            "Floor Elevation<br>Difference %{text} in" ,
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (column==floorDiffplot.columns[len(floorDiffplot.columns)-1])
        ))
            
        # Beam Differental Settlement Arrow - pointing in direction of low end 
        fig.add_trace(go.Scatter(
            x=floorSymbolplot['arrowX'],
            y=floorSymbolplot['arrowY'],
            mode = 'markers',
            marker=dict(
                color='red',
                size=10,
                symbol=floorSymbolplot[column].values,
                angle=floorDir[column].values),
            hoverinfo='skip',
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (column==floorDiffplot.columns[len(floorDiffplot.columns)-1])
        ))
        
        # Floor Elevation 
        fig.add_trace(go.Scatter(
            mode = 'markers',
            x=floorElevPlot['mpX'],
            y=floorElevPlot['mpY'],
            text=floorElevPlot.index,
            name="",
            marker=dict(
                color = floorElevPlot[column].values,
                colorscale=custom_colors,
                colorbar=dict(title='Floor Elevation (ft)'),
                size = 10,
                line=dict(
                    color='black',
                    width=1.5
                )           
            ),
            hovertemplate=
            "<b>%{text}</b><br>" +
            "Floor Elev.: %{marker.color:,} ft" ,
            hoverlabel=dict(
                bgcolor = "white"
            ),
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (column==floorDiffplot.columns[len(floorDiffplot.columns)-1])
        ))
            

    # groups and trace visibilities
    vis = []
    visList = []

    for  i, col in enumerate(floorDiffplot.columns[2:]):
        vis = [True]*(len(floorDiffplot.index)+2) + ([False]*i*3 + [True]*3 + [False]*(len(floorDiffplot.columns)-2-(i+1))*3)
        visList.append(vis)
        vis = []


    # buttons for each group
    buttons = []
    for idx, col in enumerate(floorDiffplot.columns[2:]):
        buttons.append(
            dict(
                label = col,
                method = "update",
                args=[{"visible": visList[idx]}])
        )

    buttons = [{'label': 'Select Survey Date',
                    'method': 'restyle',
                    'args': ['visible', [False]]}] + buttons

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
        annotations = diffAnno,
        #title = 'Differental Floor Elevation [in] between Monitoring Points'
    )

    # Set axes ranges
    fig.update_xaxes(range=[-25, 415])
    fig.update_yaxes(range=[-15, 140])
    return fig

# Differential Floor Slope (inches/Foot) between monitoring points
def plot_floorSlopeElev_plan(floorSlopeColorplot, beamInfo, floorSlopeplot, floorSymbolplot, floorElevPlot, floorDir, slopeAnno):
    df = floorSlopeColorplot

    #create a figure from the graph objects (not plotly express) library
    fig = go.Figure()

    buttons = []
    dates = []
    i = 0

    # Plot the beam locations as lines
    for (startX, endX, startY, endY) in zip(beamInfo['startX'], beamInfo['endX'], beamInfo['startY'], beamInfo['endY']):
        fig.add_trace(go.Scatter(
            x=[startX, endX],
            y=[startY, endY],
            mode='lines',
            line = dict(
                color = 'black',
                width = 1.5,
                dash = 'solid'),
            hoverinfo='skip',
            showlegend=False
        ))

    # Plot the Marker Point (MP) labels in grey
    fig.add_trace(go.Scatter(
        x=beamInfo['labelX'],
        y=beamInfo['labelY'],
        text=beamInfo['MP_W_S'],
        mode = 'text',
        textfont = dict(
            size = 10,
            color = 'grey'),
        hoverinfo='skip',
        showlegend=False
    ))

    # Create a list to store the visibility lists for each dataframe
    all_args = []
    vis = []
    visList = []

    #create custom color scale, red to blue through white
    custom_colors = ['#0000FF', '#FFFFFF', '#FF0000']

    #iterate through columns in dataframe (not including the year column)
    for column in floorSlopeplot.columns[3:]:
        # Floor Differental
        fig.add_trace(go.Scatter(
            x=df['beamX'],
            y=df['beamY'],
            text=abs(df[column].values.round(2)),
            customdata=df.index,
            name="",
            mode = 'text',
            textfont = dict(
                size = 10,
                color = df[f'{column}_color'].values 
                ),
            hovertemplate=
            "<b>%{customdata}</b><br>" +
            "Floor Slope %{text} in/ft" ,
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (column==floorSlopeplot.columns[len(floorSlopeplot.columns)-1])
        ))
            
        # Beam Differental Settlement Arrow - pointing in direction of low end 
        fig.add_trace(go.Scatter(
            x=floorSymbolplot['arrowX'],
            y=floorSymbolplot['arrowY'],
            mode = 'markers',
            marker=dict(
                color='red',
                size=10,
                symbol=floorSymbolplot[column].values,
                angle=floorDir[column].values),
            hoverinfo='skip',
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (column==floorSlopeplot.columns[len(floorSlopeplot.columns)-1])
        ))
        
        # Floor Elevation 
        fig.add_trace(go.Scatter(
            mode = 'markers',
            x=floorElevPlot['mpX'],
            y=floorElevPlot['mpY'],
            text=floorElevPlot.index,
            name="",
            marker=dict(
                color = floorElevPlot[column].values,
                colorscale=custom_colors,
                colorbar=dict(title='Floor Elevation (ft)'),
                size = 10,
                line=dict(
                    color='black',
                    width=1.5
                )           
            ),
            hovertemplate=
            "<b>%{text}</b><br>" +
            "Floor Elev.: %{marker.color:,} ft" ,
            hoverlabel=dict(
                bgcolor = "white"
            ),
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (column==floorSlopeplot.columns[len(floorSlopeplot.columns)-1])
        ))
            

    # groups and trace visibilities
    vis = []
    visList = []

    for  i, col in enumerate(floorSlopeplot.columns[3:]):
        vis = [True]*(len(floorSlopeplot.index)+2) + ([False]*i*3 + [True]*3 + [False]*(len(floorSlopeplot.columns)-(i+1))*3)
        visList.append(vis)
        vis = []


    # buttons for each group
    buttons = []
    for idx, col in enumerate(floorSlopeplot.columns[3:]):
        buttons.append(
            dict(
                label = col,
                method = "update",
                args=[{"visible": visList[idx]}])
        )

    buttons = [{'label': 'Select Survey Date',
                    'method': 'restyle',
                    'args': ['visible', [False]]}] + buttons

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
        annotations = slopeAnno,
        #title = 'Differental Floor Elevation [in] between Monitoring Points'
    )

    # Set axes ranges
    fig.update_xaxes(range=[-25, 415])
    fig.update_yaxes(range=[-15, 140])
    return fig

def plot_3D_settlement_slider_animated(settlementStart, beamInfo3D, plot3dAnno):
    # Calculate the maximum number of traces required for any frame
    max_traces_per_frame = len(beamInfo3D['startX']) + 1  # +1 for the label trace

    # Initialize the figure with the maximum number of empty traces
    fig = go.Figure(data=[go.Scatter3d(x=[], y=[], z=[], mode='lines', showlegend=False) for _ in range(max_traces_per_frame)])

    # Creating frames
    frames = []
    for col in settlementStart.columns:
        frame_traces = []  # List to hold all traces for this frame

        # Create a separate trace for each line segment
        for (startX, endX, startY, endY, startZ, endZ, startColor, endColor) in zip(beamInfo3D['startX'], beamInfo3D['endX'], 
                                                                                    beamInfo3D['startY'], beamInfo3D['endY'], 
                                                                                    beamInfo3D['{0}_start'.format(col)], 
                                                                                    beamInfo3D['{0}_end'.format(col)],
                                                                                    beamInfo3D[col],beamInfo3D[col]):

            line_trace = go.Scatter3d(
                x=[startX, endX],
                y=[startY, endY],
                z = [startZ, endZ],
                text = beamInfo3D['MP_W_S'],
                line_color= [startColor, endColor],
                name="",
                mode='lines',
                line = dict(
                    color = 'black',
                    width = 3,
                    dash = 'solid'),
                #hoverinfo='skip',
                showlegend=False 
            )
            frame_traces.append(line_trace)

        # Create the label trace for this frame
        label_trace = go.Scatter3d(
            x=beamInfo3D['labelX'], 
            y=beamInfo3D['labelY'], 
            z=beamInfo3D[f'{col}_start'], 
            text=beamInfo3D['MP_W_S'], 
            mode='text', 
            textfont=dict(
                size=12,
                color='grey'), 
            hoverinfo='skip', 
            showlegend=False
        )
        frame_traces.append(label_trace)

        # Ensure the frame has the same number of traces as the figure
        while len(frame_traces) < max_traces_per_frame:
            frame_traces.append(go.Scatter3d(x=[], y=[], z=[], mode=[]))

        # Add the frame
        frames.append(go.Frame(data=frame_traces, name=col))

    fig.frames = frames

    # Slider
    sliders = [{"steps": [{"args": [[f.name], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                            "label": col, "method": "animate"} for col, f in zip(settlementStart.columns, fig.frames)],
                "len": 0.95,
                "x": 0.035,
                "y": 0}]

    camera = dict(
        up=dict(x=0, y=0, z=1),
        center=dict(x=0, y=0, z=0),
        eye=dict(x=0.1, y=4, z=3)
    )

    # Define the play and pause buttons
    play_button = dict(
        label="&#9654;",
        method="animate",
        args=[None, {"frame": {"duration": 200, "redraw": True}, "fromcurrent": True, "transition": {"duration": 200, "easing": "quadratic-in-out"}}]
    )

    pause_button = dict(
        label="&#9724;",
        method="animate",
        args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}]
    )

    maxSettlement = settlementStart[settlementStart.columns[len(settlementStart.columns)-1]].max()

    # Update layout for slider and set consistent y-axis range
    fig.update_layout(
        # Update layout with play and pause buttons
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            buttons=[play_button, pause_button],
            x=0,  # x and y determine the position of the buttons
            y=-0.06,
            xanchor="right",
            yanchor="top",
            direction="left"
        )],
        autosize=False,
        margin=dict(l=0, r=0, b=100, t=0),
        scene_camera=camera,
        scene=dict(
            xaxis_title='',
            xaxis= dict(range=[400,-10]), 
            yaxis_title='',
            yaxis= dict(range=[130,-10]),
            zaxis_title='Cumulative Settlement [ft]',
            zaxis = dict(range = [maxSettlement,0])
        ),
        sliders=sliders,
        width = 1100,
        height = 600,
        scene_aspectmode='manual',
        scene_aspectratio=dict(x=7, y=2, z=1),
        uniformtext_minsize=10,
        annotations = plot3dAnno
        )

    # Set initial view, update hover mode
    fig.update_traces(x=frames[0].data[0].x, 
                    y=frames[0].data[0].y, 
                    z=frames[0].data[0].z,
                    hovertemplate="<br>".join([
                        "Settlement [ft]: %{z}"
                        ]),
                    hoverlabel=dict(
                        bgcolor = "white"
                        ))
    return fig

def plot_3D_floorElev_slider_animated_planes(elevationFloorStart, elevFloorInfo3D, plot3dAnnoDiff, floorElevPlot):
    
    # Calculate the maximum number of traces required for any frame
    max_traces_per_frame = len(elevFloorInfo3D['startX']) + 1 + 4 #The added traces are: +1 for the label trace, +4 for two mean and two fitted traces

    # Initialize the figure with the maximum number of empty traces
    fig = go.Figure(data=[go.Scatter3d(x=[], y=[], z=[], mode='lines', showlegend=False) for _ in range(max_traces_per_frame)])

    # Creating frames
    frames = []
    pods = ['A', 'B']
    
    for col in elevationFloorStart.columns:
        frame_traces = []  # List to hold all traces for this frame

        # Create a separate trace for each line segment
        for (startX, endX, startY, endY, startZ, endZ, startColor, endColor) in zip(elevFloorInfo3D['startX'], elevFloorInfo3D['endX'], 
                                                                                    elevFloorInfo3D['startY'], elevFloorInfo3D['endY'], 
                                                                                    elevFloorInfo3D['{0}_start'.format(col)], 
                                                                                    elevFloorInfo3D['{0}_end'.format(col)],
                                                                                    elevFloorInfo3D[col],elevFloorInfo3D[col]):

            line_trace = go.Scatter3d(
                x=[startX, endX],
                y=[startY, endY],
                z = [startZ, endZ],
                text = elevFloorInfo3D['MP_W_S'],
                line_color= [startColor, endColor],
                name="",
                mode='lines',
                line = dict(
                    color = 'black',
                    width = 3,
                    dash = 'solid'),
                #hoverinfo='skip',
                showlegend=False 
            )
            frame_traces.append(line_trace)

        # Create the label trace for this frame
        label_trace = go.Scatter3d(
            x=elevFloorInfo3D['labelX'], 
            y=elevFloorInfo3D['labelY'], 
            z=elevFloorInfo3D[f'{col}_start'], 
            text=elevFloorInfo3D['MP_W_S'], 
            mode='text', 
            textfont=dict(
                size=12,
                color='grey'), 
            hoverinfo='skip', 
            showlegend=False
        )
        frame_traces.append(label_trace)      

        for pod in pods:
            df = floorElevPlot[[pod in s for s in floorElevPlot.index]]
            
            # Extract coordinates
            xs = df['mpX']
            ys = df['mpY']
            zs = df[col]

            # Calculate mean of z values
            Z_mean = zs.mean()

            # Fit plane 
            tmp_A = []
            tmp_b = []
            for i in range(len(xs)):
                tmp_A.append([xs[i], ys[i], 1])
                tmp_b.append(zs[i])
            b = np.matrix(tmp_b).T
            A = np.matrix(tmp_A)
            fit = (A.T * A).I * A.T * b

            # Define ranges for x and y
            xlim = [xs.min(), xs.max()]
            ylim = [ys.min(), ys.max()]

            # Create meshgrid for the plane surface - mean and fitted
            X, Y = np.meshgrid(np.arange(xlim[0], xlim[1]),
                            np.arange(ylim[0], ylim[1]))
            Z_plane_mean = np.ones_like(X) * Z_mean

            Z_plane_fit = np.zeros(X.shape)

            for r in range(X.shape[0]):
                for c in range(X.shape[1]):
                    Z_plane_fit[r,c] = fit[0] * X[r,c] + fit[1] * Y[r,c] + fit[2]

            # Add surface trace for the plane - mean
            mean_plane = go.Surface(x=X,y=Y, z=Z_plane_mean,
                                    showscale=False, showlegend= True,
                                    name=f'Mean plane for {pod} {col}'
            )
            frame_traces.append(mean_plane)      
            
            # Add surface trace for the plane - fit
            fit_plane = go.Surface(x=X, y=Y, z=Z_plane_fit,
                                    colorscale='Viridis', showscale=False, showlegend= True,
                                    name=f'Fit plane for {pod} {col}'
            )
            frame_traces.append(fit_plane)  

        # Ensure the frame has the same number of traces as the figure
        while len(frame_traces) < max_traces_per_frame:
            frame_traces.append(go.Scatter3d(x=[], y=[], z=[], mode=[]))

        # Add the frame
        frames.append(go.Frame(data=frame_traces, name=col))

    fig.frames = frames
            

    # Slider
    sliders = [{"steps": [{"args": [[f.name], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                            "label": col, "method": "animate"} for col, f in zip(elevationFloorStart.columns, fig.frames)],
                "len": 0.95,
                "x": 0.035,
                "y": 0}]

    camera = dict(
        up=dict(x=0, y=0, z=1),
        center=dict(x=0, y=0, z=0),
        eye=dict(x=0.1, y=4, z=3)
    )

    # Define the play and pause buttons
    play_button = dict(
        label="&#9654;",
        method="animate",
        args=[None, {"frame": {"duration": 200, "redraw": True}, "fromcurrent": True, "transition": {"duration": 200, "easing": "quadratic-in-out"}}]
    )

    pause_button = dict(
        label="&#9724;",
        method="animate",
        args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}]
    )

    maxElev = elevFloorInfo3D.loc[:, elevFloorInfo3D.columns.str.contains('_start')].max().max()
    minElev = elevFloorInfo3D.loc[:, elevFloorInfo3D.columns.str.contains('_start')].min().min()

    # Update layout for slider and set consistent y-axis range
    fig.update_layout(
        # Update layout with play and pause buttons
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            buttons=[play_button, pause_button],
            x=0,  # x and y determine the position of the buttons
            y=-0.06,
            xanchor="right",
            yanchor="top",
            direction="left"
        )],
        autosize=False,
        margin=dict(l=0, r=0, b=100, t=0),
        scene_camera=camera,
        scene=dict(
            xaxis_title='',
            xaxis= dict(range=[400,-10]), 
            yaxis_title='',
            yaxis= dict(range=[130,-10]),
            zaxis_title='Floor Elevation [ft]',
            zaxis = dict(range = [minElev,maxElev])
        ),
        sliders=sliders,
        width = 1100,
        height = 600,
        scene_aspectmode='manual',
        scene_aspectratio=dict(x=7, y=2, z=1),
        uniformtext_minsize=10,
        annotations = plot3dAnnoDiff,
        legend = dict(
            xanchor = 'right',
            yanchor = 'top',
            x = 1.2,
            y = 0.9
        )
        )

    # Set initial view, update hover mode
    fig.update_traces(x=frames[0].data[0].x, 
                    y=frames[0].data[0].y, 
                    z=frames[0].data[0].z,
                    hovertemplate="<br>".join([
                        "Elevation [ft]: %{z}"
                        ]),
                    hoverlabel=dict(
                        bgcolor = "white"
                        ))
    return fig

# Plot Floor Elevation Error - fitted
def plot_FloorElev_error_fit(error_fitFloor, color_dict, mapsPods):
    df = error_fitFloor.T

    # plotly figure
    fig = go.Figure()

    for column in df:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[column],
                name= column,
                mode = 'lines+markers',
                marker_color = color_dict[column]
            ))
    
    fig.add_shape(
            type='line',
            x0=df.index.min(),  # Start x position (use the min index)
            x1=df.index.max(),  # End x position (use the max index)
            y0=0,  # Start y position
            y1=0,  # End y position (horizontal line at y=2)
            line=dict(
                color='black',
                width=2,
                dash='solid', 
            )
        )
    
    fig.add_shape(
            type='line',
            x0=df.index.min(),  # Start x position (use the min index)
            x1=df.index.max(),  # End x position (use the max index)
            y0=2,  # Start y position
            y1=2,  # End y position (horizontal line at y=2)
            line=dict(
                color='red',
                width=2,
                dash='dash', 
            )
        )
    
    fig.add_shape(
            type='line',
            x0=df.index.min(),  # Start x position (use the min index)
            x1=df.index.max(),  # End x position (use the max index)
            y0=-2,  # Start y position
            y1=-2,  # End y position (horizontal line at y=2)
            line=dict(
                color='red',
                width=2,
                dash='dash', 
            )
        )
            
    fig.update_layout(xaxis_title="Survey Date",
                      yaxis_title="Anomaly from the Fit Plane [in]")

    # groups and trace visibilities
    group = []
    vis = []
    visList = []
    for m in mapsPods.keys():
        for col in df.columns:
            if col in mapsPods[m]:
                vis.append(True)
            else:
                vis.append(False)
        group.append(m)
        visList.append(vis)
        vis = []

    # buttons for each group
    buttons = []
    for i, g in enumerate(group):
        button =  dict(label=g,
                    method = 'restyle',
                        args = ['visible',visList[i]])
        buttons.append(button)

    # buttons
    buttons = [{'label': 'All Points',
                    'method': 'restyle',
                    'args': ['visible', [True, True, True, True, True, True]]}] + buttons

                

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
        height = 600
    )
    return fig

# Plot Floor Elevation Error - mean
def plot_FloorElev_error_mean(error_meanFloor, color_dict, mapsPods):

    # pod_A = floorElevPlot.loc[floorElevPlot.index.str.contains('A')]
    # pod_B = floorElevPlot.loc[floorElevPlot.index.str.contains('B')]
    # mean_A = pod_A.iloc[:,2:].mean()
    # mean_B = pod_B.iloc[:,2:].mean()

    # error_A = pod_A.iloc[:,2:] - mean_A
    # error_B = pod_B.iloc[:,2:] - mean_B

    # error = pd.concat([error_A, error_B])
    # fit_errorT = error.T

    df = error_meanFloor.T

    # plotly figure
    fig = go.Figure()

    for column in df:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[column],
                name= column,
                mode = 'lines+markers',
                marker_color = color_dict[column]
            ))

    fig.add_shape(
            type='line',
            x0=df.index.min(),  # Start x position (use the min index)
            x1=df.index.max(),  # End x position (use the max index)
            y0=0,  # Start y position
            y1=0,  # End y position (horizontal line at y=2)
            line=dict(
                color='black',
                width=2,
                dash='solid', 
            )
        )
    
    fig.add_shape(
            type='line',
            x0=df.index.min(),  # Start x position (use the min index)
            x1=df.index.max(),  # End x position (use the max index)
            y0=2,  # Start y position
            y1=2,  # End y position (horizontal line at y=2)
            line=dict(
                color='red',
                width=2,
                dash='dash', 
            )
        )
    
    fig.add_shape(
            type='line',
            x0=df.index.min(),  # Start x position (use the min index)
            x1=df.index.max(),  # End x position (use the max index)
            y0=-2,  # Start y position
            y1=-2,  # End y position (horizontal line at y=2)
            line=dict(
                color='red',
                width=2,
                dash='dash', 
            )
        )
            
    fig.update_layout(xaxis_title="Survey Date",
                      yaxis_title="Anomaly from the Mean Plane [in]")

    # groups and trace visibilities
    group = []
    vis = []
    visList = []
    for m in mapsPods.keys():
        for col in df.columns:
            if col in mapsPods[m]:
                vis.append(True)
            else:
                vis.append(False)
        group.append(m)
        visList.append(vis)
        vis = []

    # buttons for each group
    buttons = []
    for i, g in enumerate(group):
        button =  dict(label=g,
                    method = 'restyle',
                        args = ['visible',visList[i]])
        buttons.append(button)

    # buttons
    buttons = [{'label': 'All Points',
                    'method': 'restyle',
                    'args': ['visible', [True, True, True, True, True, True]]}] + buttons

                

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
        height = 600
    )
    return fig

def plot_error_std_floor(error_stdFloor):
    
    uniques_stats = error_stdFloor.columns
    colors = px.colors.qualitative.Plotly  # You can choose any color palette
    color_mapping = {beam: colors[i % len(colors)] for i, beam in enumerate(uniques_stats)}

    # plotly figure
    fig = go.Figure()
    for column in error_stdFloor:
            fig.add_trace(go.Scatter(
                x=error_stdFloor.index,
                y=error_stdFloor[column],
                name= column,
                mode = 'lines+markers',
                marker_color = color_mapping[column]
            ))
        
    fig.update_layout(xaxis_title="Survey Date",
                        yaxis_title="Standard Deviation [in]")
    
    return fig

def plot_fitted_slope_floor(slopes_fitFloor):
    slopes_fitFloor['Survey_date'] = pd.to_datetime(slopes_fitFloor['Survey_date'])

    # Create color mapping for unique statistics
    uniques_stats = slopes_fitFloor.columns[2:]  # Assuming the first two columns are 'Pod' and 'Survey_date'
    colors = px.colors.qualitative.Plotly  # Choose color palette
    color_mapping = {stat: colors[i % len(colors)] for i, stat in enumerate(uniques_stats)}

    # Create traces for each slope type
    fig = go.Figure()

    # Add traces
    for pod in slopes_fitFloor['Pod'].unique():
        pod_data = slopes_fitFloor[slopes_fitFloor['Pod'] == pod]

        for column in uniques_stats:
            fig.add_trace(go.Scatter(x=pod_data['Survey_date'], 
                                    y=pod_data[column], 
                                    mode='lines+markers',
                                    marker_color = color_mapping[column],
                                    name=f'Pod {pod} - {column}'))

    # Create dropdown menu
    dropdown_buttons = [
        {'label': 'All Points', 'method': 'update', 'args': [{'visible': [True] * len(fig.data)}]},  # Show all
        {'label': 'Pod A', 'method': 'update', 'args': [{'visible': [True if 'A' in trace.name else False for trace in fig.data]}]},  # Show only Pod A
        {'label': 'Pod B', 'method': 'update', 'args': [{'visible': [True if 'B' in trace.name else False for trace in fig.data]}]}   # Show only Pod B
    ]

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = dropdown_buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
        height = 600
    )

    fig.update_layout(xaxis_title="Survey Date",
                        yaxis_title="Slope [%]")

    return fig


def plot_3D_gradeBeamElev_slider_animated(elevationGBStart, elevGBInfo3D , plot3dAnno):
    
    # Calculate the maximum number of traces required for any frame
    max_traces_per_frame = len(elevGBInfo3D['startX'])*2 + 1  # +1 for the label trace

    # Initialize the figure with the maximum number of empty traces
    fig = go.Figure(data=[go.Scatter3d(x=[], y=[], z=[], mode='lines', showlegend=False) for _ in range(max_traces_per_frame)])

    # Creating frames
    frames = []
    for col in elevationGBStart.columns:
        frame_traces = []  # List to hold all traces for this frame

        # Create a separate trace for each line segment
        for (startX, endX, startY, endY, startZ, endZ, startColor, endColor) in zip(elevGBInfo3D['startX'], elevGBInfo3D['endX'], 
                                                                                    elevGBInfo3D['startY'], elevGBInfo3D['endY'], 
                                                                                    elevGBInfo3D['{0}_start'.format(col)], 
                                                                                    elevGBInfo3D['{0}_end'.format(col)],
                                                                                    elevGBInfo3D[col],elevGBInfo3D[col]):

            line_trace = go.Scatter3d(
                x=[startX, endX],
                y=[startY, endY],
                z = [startZ, endZ],
                text = elevGBInfo3D['MP_W_S'],
                line_color= [startColor, endColor],
                name="",
                mode='lines',
                line = dict(
                    color = 'black',
                    width = 3,
                    dash = 'solid'),
                #hoverinfo='skip',
                showlegend=False 
            )
            frame_traces.append(line_trace)

            column_trace = go.Scatter3d(
                x=[startX, startX],
                y=[startY, startY],
                z = [startZ, (startZ + 12.31)],
                text = elevGBInfo3D['MP_W_S'],
                line_color= "black",#[startColor, endColor],
                name="",
                mode='lines',
                line = dict(
                    color = 'black',
                    width = 3,
                    dash = 'solid'),
                hoverinfo='skip',
                showlegend=False 
            )
            frame_traces.append(column_trace)

        # Create the label trace for this frame
        label_trace = go.Scatter3d(
            x=elevGBInfo3D['labelX'], 
            y=elevGBInfo3D['labelY'], 
            z=elevGBInfo3D[f'{col}_start'], 
            text=elevGBInfo3D['MP_W_S'], 
            mode='text', 
            textfont=dict(
                size=12,
                color='grey'), 
            hoverinfo='skip', 
            showlegend=False
        )
        frame_traces.append(label_trace)

        # Ensure the frame has the same number of traces as the figure
        while len(frame_traces) < max_traces_per_frame:
            frame_traces.append(go.Scatter3d(x=[], y=[], z=[], mode=[]))

        # Add the frame
        frames.append(go.Frame(data=frame_traces, name=col))

    fig.frames = frames

    # Slider
    sliders = [{"steps": [{"args": [[f.name], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                            "label": col, "method": "animate"} for col, f in zip(elevationGBStart.columns, fig.frames)],
                "len": 0.95,
                "x": 0.035,
                "y": 0}]

    camera = dict(
        up=dict(x=0, y=0, z=1),
        center=dict(x=0, y=0, z=0),
        eye=dict(x=0.1, y=4, z=3)
    )

    # Define the play and pause buttons
    play_button = dict(
        label="&#9654;",
        method="animate",
        args=[None, {"frame": {"duration": 200, "redraw": True}, "fromcurrent": True, "transition": {"duration": 200, "easing": "quadratic-in-out"}}]
    )

    pause_button = dict(
        label="&#9724;",
        method="animate",
        args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}]
    )

    maxElev = elevGBInfo3D.loc[:, elevGBInfo3D.columns.str.contains('_start')].max().max()
    minElev = elevGBInfo3D.loc[:, elevGBInfo3D.columns.str.contains('_start')].min().min()

    # Update layout for slider and set consistent y-axis range
    fig.update_layout(
        # Update layout with play and pause buttons
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            buttons=[play_button, pause_button],
            x=0,  # x and y determine the position of the buttons
            y=-0.06,
            xanchor="right",
            yanchor="top",
            direction="left"
        )],
        autosize=False,
        margin=dict(l=0, r=0, b=100, t=0),
        scene_camera=camera,
        scene=dict(
            xaxis_title='',
            xaxis= dict(range=[400,-10]), 
            yaxis_title='',
            yaxis= dict(range=[130,-10]),
            zaxis_title='Grade Beam Elevation [ft]',
            zaxis = dict(range = [minElev,maxElev])
        ),
        sliders=sliders,
        width = 1100,
        height = 600,
        scene_aspectmode='manual',
        scene_aspectratio=dict(x=7, y=2, z=1),
        uniformtext_minsize=10,
        annotations = plot3dAnno
        )

    # Set initial view, update hover mode
    fig.update_traces(x=frames[0].data[0].x, 
                    y=frames[0].data[0].y, 
                    z=frames[0].data[0].z,
                    hovertemplate="<br>".join([
                        "Elevation [ft]: %{z}"
                        ]),
                    hoverlabel=dict(
                        bgcolor = "white"
                        ))
    return fig

def plot_3D_gradeBeamElev_slider_animated_planes(elevationGBStart, elevGBInfo3D , plot3dAnno, gradeBeamElevPlot):
    
    # Calculate the maximum number of traces required for any frame
    max_traces_per_frame = len(elevGBInfo3D['startX'])*2 + 1 + 4 # +1 for the label trace, +4 for two mean and two fitted traces

    # Initialize the figure with the maximum number of empty traces
    fig = go.Figure(data=[go.Scatter3d(x=[], y=[], z=[], mode='lines', showlegend=False) for _ in range(max_traces_per_frame)])

    # Creating frames
    frames = []
    pods = ['A', 'B']

    for col in elevationGBStart.columns:
        frame_traces = []  # List to hold all traces for this frame

        # Create a separate trace for each line segment
        for (startX, endX, startY, endY, startZ, endZ, startColor, endColor) in zip(elevGBInfo3D['startX'], elevGBInfo3D['endX'], 
                                                                                    elevGBInfo3D['startY'], elevGBInfo3D['endY'], 
                                                                                    elevGBInfo3D['{0}_start'.format(col)], 
                                                                                    elevGBInfo3D['{0}_end'.format(col)],
                                                                                    elevGBInfo3D[col],elevGBInfo3D[col]):

            line_trace = go.Scatter3d(
                x=[startX, endX],
                y=[startY, endY],
                z = [startZ, endZ],
                text = elevGBInfo3D['MP_W_S'],
                line_color= [startColor, endColor],
                name="",
                mode='lines',
                line = dict(
                    color = 'black',
                    width = 3,
                    dash = 'solid'),
                #hoverinfo='skip',
                showlegend=False 
            )
            frame_traces.append(line_trace)

            column_trace = go.Scatter3d(
                x=[startX, startX],
                y=[startY, startY],
                z = [startZ, (startZ + 12.31)],
                text = elevGBInfo3D['MP_W_S'],
                line_color= "black",#[startColor, endColor],
                name="",
                mode='lines',
                line = dict(
                    color = 'black',
                    width = 3,
                    dash = 'solid'),
                hoverinfo='skip',
                showlegend=False 
            )
            frame_traces.append(column_trace)

        # Create the label trace for this frame
        label_trace = go.Scatter3d(
            x=elevGBInfo3D['labelX'], 
            y=elevGBInfo3D['labelY'], 
            z=elevGBInfo3D[f'{col}_start'], 
            text=elevGBInfo3D['MP_W_S'], 
            mode='text', 
            textfont=dict(
                size=12,
                color='grey'), 
            hoverinfo='skip', 
            showlegend=False
        )
        frame_traces.append(label_trace)

        for pod in pods:
            df = gradeBeamElevPlot[[pod in s for s in gradeBeamElevPlot.index]]
            
            # Extract coordinates
            xs = df['mpX']
            ys = df['mpY']
            zs = df[col]

            # Calculate mean of z values
            Z_mean = zs.mean()

            # Fit plane 
            tmp_A = []
            tmp_b = []
            for i in range(len(xs)):
                tmp_A.append([xs[i], ys[i], 1])
                tmp_b.append(zs[i])
            b = np.matrix(tmp_b).T
            A = np.matrix(tmp_A)
            fit = (A.T * A).I * A.T * b

            # Define ranges for x and y
            xlim = [xs.min(), xs.max()]
            ylim = [ys.min(), ys.max()]

            # Create meshgrid for the plane surface - mean and fitted
            X, Y = np.meshgrid(np.arange(xlim[0], xlim[1]),
                            np.arange(ylim[0], ylim[1]))
            Z_plane_mean = np.ones_like(X) * Z_mean

            Z_plane_fit = np.zeros(X.shape)

            for r in range(X.shape[0]):
                for c in range(X.shape[1]):
                    Z_plane_fit[r,c] = fit[0] * X[r,c] + fit[1] * Y[r,c] + fit[2]

            # Add surface trace for the plane - mean
            mean_plane = go.Surface(x=X,y=Y, z=Z_plane_mean,
                                    showscale=False, showlegend= True,
                                    name=f'Mean plane for {pod} {col}'
            )
            frame_traces.append(mean_plane)      
            
            # Add surface trace for the plane - fit
            fit_plane = go.Surface(x=X, y=Y, z=Z_plane_fit,
                                    colorscale='Viridis', showscale=False, showlegend= True,
                                    name=f'Fit plane for {pod} {col}'
            )
            frame_traces.append(fit_plane)  

        # Ensure the frame has the same number of traces as the figure
        while len(frame_traces) < max_traces_per_frame:
            frame_traces.append(go.Scatter3d(x=[], y=[], z=[], mode=[]))

        # Add the frame
        frames.append(go.Frame(data=frame_traces, name=col))

    fig.frames = frames

    # Slider
    sliders = [{"steps": [{"args": [[f.name], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                            "label": col, "method": "animate"} for col, f in zip(elevationGBStart.columns, fig.frames)],
                "len": 0.95,
                "x": 0.035,
                "y": 0}]

    camera = dict(
        up=dict(x=0, y=0, z=1),
        center=dict(x=0, y=0, z=0),
        eye=dict(x=0.1, y=4, z=3)
    )

    # Define the play and pause buttons
    play_button = dict(
        label="&#9654;",
        method="animate",
        args=[None, {"frame": {"duration": 200, "redraw": True}, "fromcurrent": True, "transition": {"duration": 200, "easing": "quadratic-in-out"}}]
    )

    pause_button = dict(
        label="&#9724;",
        method="animate",
        args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}]
    )

    maxElev = elevGBInfo3D.loc[:, elevGBInfo3D.columns.str.contains('_start')].max().max()
    minElev = elevGBInfo3D.loc[:, elevGBInfo3D.columns.str.contains('_start')].min().min()

    # Update layout for slider and set consistent y-axis range
    fig.update_layout(
        # Update layout with play and pause buttons
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            buttons=[play_button, pause_button],
            x=0,  # x and y determine the position of the buttons
            y=-0.06,
            xanchor="right",
            yanchor="top",
            direction="left"
        )],
        autosize=False,
        margin=dict(l=0, r=0, b=100, t=0),
        scene_camera=camera,
        scene=dict(
            xaxis_title='',
            xaxis= dict(range=[400,-10]), 
            yaxis_title='',
            yaxis= dict(range=[130,-10]),
            zaxis_title='Grade Beam Elevation [ft]',
            zaxis = dict(range = [minElev,maxElev])
        ),
        sliders=sliders,
        width = 1100,
        height = 600,
        scene_aspectmode='manual',
        scene_aspectratio=dict(x=7, y=2, z=1),
        uniformtext_minsize=10,
        annotations = plot3dAnno,
        legend = dict(
            xanchor = 'right',
            yanchor = 'top',
            x = 1.2,
            y = 0.9
        )
        )

    # Set initial view, update hover mode
    fig.update_traces(x=frames[0].data[0].x, 
                    y=frames[0].data[0].y, 
                    z=frames[0].data[0].z,
                    hovertemplate="<br>".join([
                        "Elevation [ft]: %{z}"
                        ]),
                    hoverlabel=dict(
                        bgcolor = "white"
                        ))
    return fig

# Plot Floor Elevation Error
def plot_GradeBeamElev_error_fit(error_fitGradeBeam, color_dict, mapsPods):
    df = error_fitGradeBeam.T

    # plotly figure
    fig = go.Figure()

    for column in df:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[column],
                name= column,
                mode = 'lines+markers',
                marker_color = color_dict[column]
            ))
    
    fig.add_shape(
            type='line',
            x0=df.index.min(),  # Start x position (use the min index)
            x1=df.index.max(),  # End x position (use the max index)
            y0=0,  # Start y position
            y1=0,  # End y position (horizontal line at y=2)
            line=dict(
                color='black',
                width=2,
                dash='solid', 
            )
        )
    
    fig.add_shape(
            type='line',
            x0=df.index.min(),  # Start x position (use the min index)
            x1=df.index.max(),  # End x position (use the max index)
            y0=2,  # Start y position
            y1=2,  # End y position (horizontal line at y=2)
            line=dict(
                color='red',
                width=2,
                dash='dash', 
            )
        )
    
    fig.add_shape(
            type='line',
            x0=df.index.min(),  # Start x position (use the min index)
            x1=df.index.max(),  # End x position (use the max index)
            y0=-2,  # Start y position
            y1=-2,  # End y position (horizontal line at y=2)
            line=dict(
                color='red',
                width=2,
                dash='dash', 
            )
        )
            
    fig.update_layout(xaxis_title="Survey Date",
                      yaxis_title="Anomaly from the Fit Plane [in]")

    # groups and trace visibilities
    group = []
    vis = []
    visList = []
    for m in mapsPods.keys():
        for col in df.columns:
            if col in mapsPods[m]:
                vis.append(True)
            else:
                vis.append(False)
        group.append(m)
        visList.append(vis)
        vis = []

    # buttons for each group
    buttons = []
    for i, g in enumerate(group):
        button =  dict(label=g,
                    method = 'restyle',
                        args = ['visible',visList[i]])
        buttons.append(button)

    # buttons
    buttons = [{'label': 'All Points',
                    'method': 'restyle',
                    'args': ['visible', [True, True, True, True, True, True]]}] + buttons

                

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
        height = 600
    )
    return fig

# Plot Grade Beam Elevation Error - mean
def plot_GradeBeamElev_error_mean(error_meanGradeBeam, color_dict, mapsPods):
    df = error_meanGradeBeam.T

    # plotly figure
    fig = go.Figure()

    for column in df:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[column],
                name= column,
                mode = 'lines+markers',
                marker_color = color_dict[column]
            ))
    
    fig.add_shape(
            type='line',
            x0=df.index.min(),  # Start x position (use the min index)
            x1=df.index.max(),  # End x position (use the max index)
            y0=0,  # Start y position
            y1=0,  # End y position (horizontal line at y=2)
            line=dict(
                color='black',
                width=2,
                dash='solid', 
            )
        )
    
    fig.add_shape(
            type='line',
            x0=df.index.min(),  # Start x position (use the min index)
            x1=df.index.max(),  # End x position (use the max index)
            y0=2,  # Start y position
            y1=2,  # End y position (horizontal line at y=2)
            line=dict(
                color='red',
                width=2,
                dash='dash', 
            )
        )
    
    fig.add_shape(
            type='line',
            x0=df.index.min(),  # Start x position (use the min index)
            x1=df.index.max(),  # End x position (use the max index)
            y0=-2,  # Start y position
            y1=-2,  # End y position (horizontal line at y=2)
            line=dict(
                color='red',
                width=2,
                dash='dash', 
            )
        )
            
    fig.update_layout(xaxis_title="Survey Date",
                      yaxis_title="Anomaly from the Mean Plane [in]")

    # groups and trace visibilities
    group = []
    vis = []
    visList = []
    for m in mapsPods.keys():
        for col in df.columns:
            if col in mapsPods[m]:
                vis.append(True)
            else:
                vis.append(False)
        group.append(m)
        visList.append(vis)
        vis = []

    # buttons for each group
    buttons = []
    for i, g in enumerate(group):
        button =  dict(label=g,
                    method = 'restyle',
                        args = ['visible',visList[i]])
        buttons.append(button)

    # buttons
    buttons = [{'label': 'All Points',
                    'method': 'restyle',
                    'args': ['visible', [True, True, True, True, True, True]]}] + buttons

                

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
        height = 600
    )
    return fig

def plot_error_std_gradeBeam(error_stdGradeBeam):
    
    uniques_stats = error_stdGradeBeam.columns
    colors = px.colors.qualitative.Plotly  # You can choose any color palette
    color_mapping = {beam: colors[i % len(colors)] for i, beam in enumerate(uniques_stats)}

    # plotly figure
    fig = go.Figure()
    for column in error_stdGradeBeam:
            fig.add_trace(go.Scatter(
                x=error_stdGradeBeam.index,
                y=error_stdGradeBeam[column],
                name= column,
                mode = 'lines+markers',
                marker_color = color_mapping[column]
            ))
        
    fig.update_layout(xaxis_title="Survey Date",
                        yaxis_title="Standard Deviation [in]")
    
    return fig

def plot_fitted_slope_gradeBeam(slopes_fitGradeBeam):
    slopes_fitGradeBeam['Survey_date'] = pd.to_datetime(slopes_fitGradeBeam['Survey_date'])

    # Create color mapping for unique statistics
    uniques_stats = slopes_fitGradeBeam.columns[2:]  # Assuming the first two columns are 'Pod' and 'Survey_date'
    colors = px.colors.qualitative.Plotly  # Choose color palette
    color_mapping = {stat: colors[i % len(colors)] for i, stat in enumerate(uniques_stats)}

    # Create traces for each slope type
    fig = go.Figure()

    # Add traces
    for pod in slopes_fitGradeBeam['Pod'].unique():
        pod_data = slopes_fitGradeBeam[slopes_fitGradeBeam['Pod'] == pod]

        for column in uniques_stats:
            fig.add_trace(go.Scatter(x=pod_data['Survey_date'], 
                                    y=pod_data[column], 
                                    mode='lines+markers',
                                    marker_color = color_mapping[column],
                                    name=f'Pod {pod} - {column}'))

    # Create dropdown menu
    dropdown_buttons = [
        {'label': 'All Points', 'method': 'update', 'args': [{'visible': [True] * len(fig.data)}]},  # Show all
        {'label': 'Pod A', 'method': 'update', 'args': [{'visible': [True if 'A' in trace.name else False for trace in fig.data]}]},  # Show only Pod A
        {'label': 'Pod B', 'method': 'update', 'args': [{'visible': [True if 'B' in trace.name else False for trace in fig.data]}]}   # Show only Pod B
    ]

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = dropdown_buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
        height = 600
    )

    fig.update_layout(xaxis_title="Survey Date",
                        yaxis_title="Slope [%]")

    return fig

def plot_3D_fullStation_slider_animated(elevationFloorStart, elevFloorInfo3D, elevGBInfo3D, plot3dAnno):
    
    # Calculate the maximum number of traces required for any frame
    max_traces_per_frame = len(elevFloorInfo3D['startX'])*3 + 1  # +1 for the label trace

    # Initialize the figure with the maximum number of empty traces
    fig = go.Figure(data=[go.Scatter3d(x=[], y=[], z=[], mode='lines', showlegend=False) for _ in range(max_traces_per_frame)])

    # Creating frames
    frames = []
    for col in elevationFloorStart.columns:
        frame_traces = []  # List to hold all traces for this frame

        # Create a separate trace for each line segment -- floor
        for (startX, endX, startY, endY, startZ, endZ, startColor, endColor) in zip(elevFloorInfo3D['startX'], elevFloorInfo3D['endX'], 
                                                                                    elevFloorInfo3D['startY'], elevFloorInfo3D['endY'], 
                                                                                    elevFloorInfo3D['{0}_start'.format(col)], 
                                                                                    elevFloorInfo3D['{0}_end'.format(col)],
                                                                                    elevFloorInfo3D[col],elevFloorInfo3D[col]):

            floor_trace = go.Scatter3d(
                x=[startX, endX],
                y=[startY, endY],
                z = [startZ, endZ],
                text = elevFloorInfo3D['MP_W_S'],
                line_color= [startColor, endColor],
                name="",
                mode='lines',
                line = dict(
                    color = 'black',
                    width = 3,
                    dash = 'solid'),
                #hoverinfo='skip',
                showlegend=False 
            )
            frame_traces.append(floor_trace)

        # Create a separate trace for each line segment -- grade beam
        for (startX, endX, startY, endY, startZ, endZ, startColor, endColor) in zip(elevGBInfo3D['startX'], elevGBInfo3D['endX'], 
                                                                                    elevGBInfo3D['startY'], elevGBInfo3D['endY'], 
                                                                                    elevGBInfo3D['{0}_start'.format(col)], 
                                                                                    elevGBInfo3D['{0}_end'.format(col)],
                                                                                    elevGBInfo3D[col],elevGBInfo3D[col]):

            grade_trace = go.Scatter3d(
                x=[startX, endX],
                y=[startY, endY],
                z = [startZ, endZ],
                text = elevGBInfo3D['MP_W_S'],
                line_color= [startColor, endColor],
                name="",
                mode='lines',
                line = dict(
                    color = 'black',
                    width = 3,
                    dash = 'solid'),
                #hoverinfo='skip',
                showlegend=False 
            )
            frame_traces.append(grade_trace)

            column_trace = go.Scatter3d(
                x=[startX, startX],
                y=[startY, startY],
                z = [startZ, (startZ + 12.31)],
                text = elevGBInfo3D['MP_W_S'],
                line_color= "black",#[startColor, endColor],
                name="",
                mode='lines',
                line = dict(
                    color = 'black',
                    width = 3,
                    dash = 'solid'),
                hoverinfo='skip',
                showlegend=False 
            )
            frame_traces.append(column_trace)

        # Create the label trace for this frame
        label_trace = go.Scatter3d(
            x=elevFloorInfo3D['labelX'], 
            y=elevFloorInfo3D['labelY'], 
            z=elevFloorInfo3D[f'{col}_start'], 
            text=elevFloorInfo3D['MP_W_S'], 
            mode='text', 
            textfont=dict(
                size=12,
                color='grey'), 
            hoverinfo='skip', 
            showlegend=False
        )
        frame_traces.append(label_trace)

        # Ensure the frame has the same number of traces as the figure
        while len(frame_traces) < max_traces_per_frame:
            frame_traces.append(go.Scatter3d(x=[], y=[], z=[], mode=[]))

        # Add the frame
        frames.append(go.Frame(data=frame_traces, name=col))

    fig.frames = frames

    # Slider
    sliders = [{"steps": [{"args": [[f.name], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                            "label": col, "method": "animate"} for col, f in zip(elevationFloorStart.columns, fig.frames)],
                "len": 0.95,
                "x": 0.035,
                "y": 0}]

    camera = dict(
        up=dict(x=0, y=0, z=1),
        center=dict(x=0, y=0, z=0),
        eye=dict(x=0.1, y=4, z=3)
    )

    # Define the play and pause buttons
    play_button = dict(
        label="&#9654;",
        method="animate",
        args=[None, {"frame": {"duration": 200, "redraw": True}, "fromcurrent": True, "transition": {"duration": 200, "easing": "quadratic-in-out"}}]
    )

    pause_button = dict(
        label="&#9724;",
        method="animate",
        args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}]
    )

    maxElev = elevFloorInfo3D.loc[:, elevFloorInfo3D.columns.str.contains('_start')].max().max()
    minElev = elevGBInfo3D.loc[:, elevGBInfo3D.columns.str.contains('_start')].min().min()

    # Update layout for slider and set consistent y-axis range
    fig.update_layout(
        # Update layout with play and pause buttons
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            buttons=[play_button, pause_button],
            x=0,  # x and y determine the position of the buttons
            y=-0.06,
            xanchor="right",
            yanchor="top",
            direction="left"
        )],
        autosize=False,
        margin=dict(l=0, r=0, b=100, t=0),
        scene_camera=camera,
        scene=dict(
            xaxis_title='',
            xaxis= dict(range=[400,-10]), 
            yaxis_title='',
            yaxis= dict(range=[130,-10]),
            zaxis_title='Elevation [ft]',
            zaxis = dict(range = [minElev,maxElev])
        ),
        sliders=sliders,
        width = 1100,
        height = 600,
        scene_aspectmode='manual',
        scene_aspectratio=dict(x=7, y=2, z=1),
        uniformtext_minsize=10,
        annotations = plot3dAnno
        )

    # Set initial view, update hover mode
    fig.update_traces(x=frames[0].data[0].x, 
                    y=frames[0].data[0].y, 
                    z=frames[0].data[0].z,
                    hovertemplate="<br>".join([
                        "Elevation [ft]: %{z}"
                        ]),
                    hoverlabel=dict(
                        bgcolor = "white"
                        ))
    return fig

def plot_GradeBeam_profiles(df_GradeBeams):
    # Create a color mapping for each unique long_beam
    unique_beams = np.sort(df_GradeBeams['long_beam'].unique())
    colors = px.colors.qualitative.Plotly  # You can choose any color palette
    color_mapping = {beam: colors[i % len(colors)] for i, beam in enumerate(unique_beams)}

    # Create a figure
    fig = go.Figure()

    # Define year columns
    year_columns = df_GradeBeams.columns[2:]

    # Iterate through each unique long_beam
    for beam in unique_beams:
        # Filter the DataFrame for the current beam
        beam_data = df_GradeBeams[df_GradeBeams['long_beam'] == beam]
        
        # Iterate through the columns representing years (excluding 'long_beam' and 'plotX')
        for column in year_columns:
            # Add a trace for each year with color mapping
            fig.add_trace(go.Scatter(
                mode='lines+markers',
                x=beam_data['plotX'],                 # X-axis values
                y=beam_data[column].values,           # Y-axis values for the specific year
                name=beam,                             # Use only the beam name for the trace
                # text=df_GradeBeams.index,
                line=dict(color=color_mapping[beam]),  # Set the line color based on the long_beam
                showlegend=True,
                visible=(column == year_columns[-1])   # Only the last year column is visible by default
            ))

    # Create visibility lists for each year
    visList = []
    for i in range(len(year_columns)):
        vis = [False] * len(fig.data)
        for j in range(len(unique_beams)):
            vis[i + j * len(year_columns)] = True  # Ensure the correct visibility for each beam-year combo
        visList.append(vis)

    # Update layout if necessary
    fig.update_layout(
        xaxis_title='Horizontal Distance (feet)',
        yaxis_title='Elevation (feet)'
    )

    # Create buttons for each group
    buttons = []
    for idx, col in enumerate(year_columns):
        buttons.append(
            dict(
                label=col,
                method="update",
                args=[{"visible": visList[idx]}]  # Set visibility for the selected year
            )
        )

    buttons = [{'label': 'Select Survey Date',
                'method': 'restyle',
                'args': ['visible', [False] * len(fig.data)]}] + buttons

    # Update layout with buttons
    fig.update_layout(
        updatemenus=[
            dict(
                type="dropdown",
                direction="down",
                buttons=buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom"
            )
        ],
        # title='Profile of Grade Beam Elevations'
    )

    return fig

# Plot Floor Elevation Error - fitted
def plot_GradeBeamElev_diff(gradeBeam_diff, mapsGradeBeams):
    # Create a color mapping for each unique long_beam
    unique_beams = gradeBeam_diff.index
    colors = px.colors.qualitative.Plotly  # You can choose any color palette
    color_mapping = {beam: colors[i % len(colors)] for i, beam in enumerate(unique_beams)}

    df = gradeBeam_diff.T.drop("2022-01-07", axis=0)

    # plotly figure
    fig = go.Figure()

    for column in df:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[column],
                name= column,
                mode = 'lines+markers',
                marker_color = color_mapping[column]
            ))
    
      
    fig.add_shape(
            type='line',
            x0=df.index.min(),  # Start x position (use the min index)
            x1=df.index.max(),  # End x position (use the max index)
            y0=6,  # Start y position
            y1=6,  # End y position (horizontal line at y=2)
            line=dict(
                color='red',
                width=2,
                dash='dash', 
            )
        )
            
    fig.update_layout(xaxis_title="Survey Date",
                      yaxis_title="Grade Beam Elevation Difference (in)")
    
    

    # groups and trace visibilities
    group = []
    vis = []
    visList = []
    for m in mapsGradeBeams.keys():
        for col in df.columns:
            if col in mapsGradeBeams[m]:
                vis.append(True)
            else:
                vis.append(False)
        group.append(m)
        visList.append(vis)
        vis = []

    # buttons for each group
    buttons = []
    for i, g in enumerate(group):
        button =  dict(label=g,
                    method = 'restyle',
                        args = ['visible',visList[i]])
        buttons.append(button)

    # buttons
    buttons = [{'label': 'All Points',
                    'method': 'restyle',
                    'args': ['visible', [True, True, True, True, True, True]]}] + buttons

                

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0,
                xanchor="left",
                y=1.01,
                yanchor="bottom")
        ],
        height = 600
    )
    return fig