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
# Created:      31 October 2023
# Updated:      08 January 2024
#
# -------------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import scipy.stats as stats
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt
import openpyxl
import xlrd


# import survey dataframe and return clean version
def read_survey(surveyfile):
    survey = pd.read_csv(surveyfile, skiprows=[1], nrows=36)
    
    # rename second 2010/11/2 survey to 2010/11/3
    survey_clean = survey.drop(columns=["DESCRIPTION", "Shims\nNote 13", "Unnamed: 52", "Delta"]).rename(columns={"MONITOR\nPOINT":"MONITOR_POINT"})
    survey_clean = survey_clean.set_index('MONITOR_POINT').rename_axis('date', axis=1)
    survey_clean.columns = pd.to_datetime(survey_clean.columns).astype(str)

    # Transpose so dates are in index column
    survey_long = pd.DataFrame.transpose(survey_clean)
    return survey_clean, survey_long

# import lug to truss measurements
def read_trussHeight(trussfile):
    truss = pd.read_csv(trussfile, skiprows=[1], nrows=36)
    # Clean up the imported truss to survey point file 
    truss_clean = truss.rename(columns={"MONITOR\nPOINT":"MONITOR_POINT"}).set_index('MONITOR_POINT').rename_axis('date', axis=1)
    truss_clean.columns = pd.to_datetime(truss_clean.columns).astype(str)
    return truss_clean

# import survey data from the excel
def read_xlElev(xlfile):
    survey = pd.read_excel(
        io=xlfile,
        engine='openpyxl',
        #engine='xlrd',
        sheet_name='SURVEY DATA',
        skiprows=[0,2,3], 
        nrows=36)
    # rename second 2010/11/2 survey to 2010/11/3
    survey_clean = survey.dropna(axis=1, how='all').drop(columns=["DESCRIPTION", "Shims\nNote 13", "Delta"]).rename(columns={"MONITOR\nPOINT":"MONITOR_POINT", "2010-11-02 00:00:00.1":'2010-11-03 00:00:00'}).set_index('MONITOR_POINT').rename_axis('date', axis=1)
    survey_clean.columns = pd.to_datetime(survey_clean.columns).astype(str)

    # Transpose so dates are in index column
    survey_long = pd.DataFrame.transpose(survey_clean)
    return survey_clean, survey_long

def read_xlTruss(xlfile):
    truss = pd.read_excel(
        io=xlfile,
        engine='openpyxl',
        #engine='xlrd',
        sheet_name='SHIM DATA',
        skiprows=[0,2,3], 
        nrows=36)
    # rename second 2010/11/2 survey to 2010/11/3
    truss_clean = truss.dropna(axis=1, how='all').drop(columns=["DESCRIPTION", "Shims", "Delta"]).rename(columns={"MONITOR\nPOINT":"MONITOR_POINT"}).set_index('MONITOR_POINT').rename_axis('date', axis=1)
    truss_clean.columns = pd.to_datetime(truss_clean.columns).astype(str)
    return truss_clean

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
def calc_settlement(survey_long):
    survey_long['dummy']= 1
    firstValue = survey_long.groupby('dummy').first()
    firstValue = firstValue.to_numpy()[0]

    settlement = survey_long.drop(columns=["dummy"]).apply(lambda row: firstValue - row, axis=1)
    settlement.index = pd.to_datetime(settlement.index)
    settlement_points = pd.DataFrame.transpose(settlement)

    # Calculate the change in settlement in inches for each monitoring point - skip 2010/11/02 surveys, like in excel workbook
    settlement_delta = settlement.drop(['2010-11-02', '2010-11-03'], axis = 0).diff().mul(12)
    settlement_delta_MP = pd.DataFrame.transpose(settlement_delta)

    # Calculate the annual settlement rate for each column 
    diffDays = pd.DataFrame(index=settlement_delta.index)
    diffDays["diffDays"] = settlement_delta.index.to_series().diff().dt.days

    settlement_rate = settlement_delta.iloc[:,:].div(diffDays.diffDays, axis=0).mul(365)
    return settlement, settlement_points, settlement_delta, settlement_delta_MP, settlement_rate

# Cumulative Settlement Forecasting
def calc_forecast_settlement(settlement, nsurvey, nyears):
    settlementInterp = settlement.iloc[(len(settlement.index)-(nsurvey)):(len(settlement.index))]
    currentYear = settlementInterp.index.year[-1]

    projList = []
    for year in range(nyears):
        projYear = (currentYear + year+1).astype(str)
        projYear = pd.to_datetime(projYear + '-01-01') 
        projList.append(projYear)

    settlementExtrap = pd.DataFrame(columns=settlementInterp.columns, index = [projList]).reset_index().set_index('level_0')
    settlementExtrap.index = settlementExtrap.index.map(dt.datetime.toordinal)
    settlementInterp.index = settlementInterp.index.map(dt.datetime.toordinal)

    x_endpoints = list([settlementInterp.index[0], settlementInterp.index[nsurvey-1]]) + settlementExtrap.index.tolist()
    x_enddates = pd.DataFrame(x_endpoints)

    df_regression = settlementInterp.apply(lambda x: stats.linregress(settlementInterp.index, x), result_type='expand').rename(index={0: 'slope', 1: 
                                                                                    'intercept', 2: 'rvalue', 3:
                                                                                    'p-value', 4:'stderr'})

    new_data_loc = {}
    for column in df_regression.columns:   
        slope = df_regression.loc['slope', column]  
        intercept = df_regression.loc['intercept', column]  
        new_data_loc[column] = [slope * val + intercept for val in x_endpoints]

    settlementProj = pd.DataFrame([new_data_loc], columns=new_data_loc.keys()).apply(pd.Series.explode).reset_index().drop(['index'], axis = 1)
    settlementProj = x_enddates.join(settlementProj).set_index(0)
    settlementProj.index.names = ['date']
    settlementProj.index = settlementProj.index.map(dt.datetime.fromordinal)
    settlementProj = settlementProj.apply(pd.to_numeric, errors='ignore').round(3)

    settlementProj_trans = settlementProj
    settlementProj_trans.index = settlementProj_trans.index.strftime('%Y-%m-%d') 
    settlementProj_trans = pd.DataFrame.transpose(settlementProj_trans).iloc[:,2:]
    return settlementProj, settlementProj_trans

# Calculate differental settlement
def calc_differental_settlement(beamLength_long, beamLength_sort, survey_clean, beamInfo, settlementProj_trans):
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

    # Calculate the slope for each beam, transpose for ploting 
    beamSlope = beamLength_sort.join(beamDiff)
    beamSlope.iloc[:,1:] = beamSlope.iloc[:,1:].div(beamSlope.beamLength, axis=0)
    beamSlopeplot = beamInfo[['beamName', 'beamX', 'beamY']].dropna().set_index(['beamName']).join(beamSlope)
    beamSlope = beamSlopeplot.drop(columns=['beamX', 'beamY', 'beamLength'])

    # Calculate the projected slope for each beam 
    beamSlopeProj = beamLength_sort.join(beamDiffProj)
    beamSlopeProj.iloc[:,1:] = beamSlopeProj.iloc[:,1:].div(beamSlopeProj.beamLength, axis=0)
    beamSlopeProj= beamSlopeProj.drop(columns=['beamLength'])
    return beamDiff, beamDiffplot, beamSlope, beamSlopeplot, beamSlopeProj

# Create dataframes for planview plotting 
# (lug and floor elevations, lug to truss measurement, differential settlement)
def calc_plan_dataframe (survey_clean, truss_clean, MPlocations, beamLength_long, beamLength_sort, beamInfo):
    # Lug elevation for each survey date
    lugElevPlot = MPlocations.join(survey_clean)

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
    return lugElevPlot, lugFloorPlot, floorElevPlot, floorDiff, floorDiffplot, floorSlope, floorSlopeplot

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

# Line styles for beam plots
def plot_beamStyles(beamInfo, beamDiff, beamSlope, beamSlopeProj):
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
    beamSymbol = pd.DataFrame(np.select(conditions, choices, default=np.nan), index = beamDiff.index, columns = beamDiff.columns).replace('nan','x')

    # Create dataframe for conditional text color for differental settlement values
    conditions = [abs(beamDiff)<1.5, (abs(beamDiff)>=1.5) & (abs(beamDiff)<2), abs(beamDiff)>=2]
    choices = ['black', 'orange', 'red']
    beamDiffColor = pd.DataFrame(np.select(conditions, choices, default=np.nan), index = beamDiff.index, columns = beamDiff.columns).replace('nan','blue')

    # Create dataframe for conditional text color for differental settlement slope values
    conditions = [abs(beamSlope)<(1/32), (abs(beamSlope)>=(1/32)) & (abs(beamSlope)<(1/16)), (abs(beamSlope)>=(1/16)) & (abs(beamSlope)<(1/8)), abs(beamDiff)>=(1/8)]
    choices = ['black','gold', 'orange', 'red']
    beamSlopeColor = pd.DataFrame(np.select(conditions, choices, default=np.nan), index = beamDiff.index, columns = beamDiff.columns).replace('nan','blue')
    
    # Create dataframe for conditional text color for differental settlement slope values
    conditions = [abs(beamSlopeProj)<(1/32), ((abs(beamSlopeProj)>=(1/32)) & (abs(beamSlopeProj)<(1/16))), ((abs(beamSlopeProj)>=(1/16)) & (abs(beamSlopeProj)<(1/8))), abs(beamSlopeProj)>=(1/8)]
    choices = ['green','teal', 'blue', 'purple']
    beamSlopeProjColor = pd.DataFrame(np.select(conditions, choices, default=np.nan), index = beamSlopeProj.index, columns = beamSlopeProj.columns).replace('nan','blue')
    return beamDirLabels, beamDir, beamSymbol, beamDiffColor, beamSlopeColor, beamSlopeProjColor

# Line styles for floor plots
def plot_floorStyles(beamDirLabels, beamInfo, floorDiff, floorDiffplot, floorSlope, floorSlopeplot):
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
    floorSymbol = pd.DataFrame(np.select(conditions, choices, default=np.nan), index = floorDiff.index, columns = floorDiff.columns).replace('nan','x')
    floorSymbolplot = beamInfo[['beamName', 'arrowX', 'arrowY']].dropna().set_index(['beamName']).join(floorSymbol)

    # Create dataframe for conditional text color for floor differental settlement values
    conditions = [abs(floorDiff)<1.5, (abs(floorDiff)>=1.5) & (abs(floorDiff)<2), abs(floorDiff)>=2]
    choices = ['black', 'orange', 'red']
    floorDiffColor = pd.DataFrame(np.select(conditions, choices, default=np.nan), index = floorDiff.index, columns = floorDiff.columns).replace('nan','blue')
    floorDiffColorplot = floorDiffplot.join(floorDiffColor, rsuffix='_color')

    # Create dataframe for conditional text color for differental settlement slope values
    conditions = [abs(floorSlope)<(1/32), ((abs(floorSlope)>=(1/32)) & (abs(floorSlope)<(1/16))), ((abs(floorSlope)>=(1/16)) & (abs(floorSlope)<(1/8))), abs(floorSlope)>=(1/8)]
    choices = ['black','gold', 'orange', 'red']
    floorSlopeColor = pd.DataFrame(np.select(conditions, choices, default=np.nan), index = floorSlope.index, columns = floorSlope.columns).replace('nan','blue')
    floorSlopeColorplot = floorSlopeplot.join(floorSlopeColor, rsuffix='_color')
    return floorDir, floorSymbolplot, floorDiffColorplot, floorSlopeColorplot
    
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
        dict(text="<span style='color:black'>Observed</span> & <span style='color:green'>Forecasted</span> Beam Slope less than 1/32 in/ft",
                x=0.6, xref="paper", xanchor="right",
                y=-0.05, yref="paper", yanchor="bottom",
                align="right",
                showarrow=False, 
                font = dict(
                    size = 14,
                    color = 'grey')
            ),
        dict(text="<span style='color:gold'>Observed</span> & <span style='color:teal'>Forecasted</span> Beam Slope between 1/32 and 1/16 in/ft",
                x=1, xref="paper", xanchor="right",
                y=-0.05, yref="paper", yanchor="bottom",
                align="right",
                showarrow=False, 
                font = dict(
                    size = 14,
                    color = 'grey')
            ),
        dict(text="<span style='color:orange'>Observed</span> & <span style='color:blue'>Forecasted</span> Beam Slope between 1/16 and 1/8 in/ft",
                x=.6, xref="paper", xanchor="right",
                y=-0.08, yref="paper", yanchor="bottom",
                align="right",
                showarrow=False, 
                font = dict(
                    size = 14,
                    color = 'grey')
            ),
        dict(text="<span style='color:red'>Observed</span> & <span style='color:purple'>Forecasted</span> Beam Slope greater than 1/8 in/ft",
                x=1, xref="paper", xanchor="right",
                y=-0.08, yref="paper", yanchor="bottom",
                align="right",
                showarrow=False, 
                font = dict(
                    size = 14,
                    color = 'grey')
            ),
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
    'B4-1': '#1b9e77', 'B4-2': '#d95f02', 'B4-3': '#7570b3', 'B4-4': '#e7298a'
}

    # Identify the monitor point groupings based on the pod
    maps = {'A1':['A1-1', 'A1-2', 'A1-3', 'A1-4'],
        'A2':['A2-1', 'A2-2', 'A2-3', 'A2-4', 'A2-5','A2-6'],
        'A3':['A3-1', 'A3-2', 'A3-3', 'A3-4'],
        'A4':['A4-1', 'A4-2', 'A4-3', 'A4-4'],
       'B1':['B1-1', 'B1-2', 'B1-3', 'B1-4'],
        'B2':['B2-1', 'B2-2', 'B2-3', 'B2-4', 'B2-5','B2-6'],
        'B3':['B3-1', 'B3-2', 'B3-3', 'B3-4'],
        'B4':['B4-1', 'B4-2', 'B4-3', 'B4-4']}
    
    return beamDiffAnno, beamSlopeAnno, diffAnno, slopeAnno, plot3dAnno, color_dict, maps

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

    fig.update_layout(xaxis_title="Survey Date",
                    yaxis_title="Settlement [in/year]")

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

# 3D Plot - settlement with a slider
def plot_3D_settlement_slider(settlementStart, beamInfo3D):
    fig = go.Figure()

    for col in settlementStart.columns:
        # Plot the beam locations as lines
        for (startX, endX, startY, endY, startZ, endZ, startColor, endColor, mpLabel) in zip(beamInfo3D['startX'], beamInfo3D['endX'], 
                                                                                    beamInfo3D['startY'], beamInfo3D['endY'], 
                                                                                    beamInfo3D['{0}_start'.format(col)], 
                                                                                    beamInfo3D['{0}_end'.format(col)],
                                                                                    beamInfo3D[col],beamInfo3D[col], beamInfo3D['MP_W_S']):
            fig.add_trace(go.Scatter3d(
                x=[startX, endX],
                y=[startY, endY],
                z = [startZ, endZ],
                text = mpLabel,
                line_color= [startColor, endColor],
                name="",
                mode='lines',
                line = dict(
                    color = 'black',
                    width = 1.5,
                    dash = 'solid'),
                showlegend=False, 
                #setting only the first dataframe to be visible as default
                visible = (col==settlementStart.columns[len(settlementStart.columns)-1]),
                hovertemplate="<br>".join([
                    #"MP: %{mpLabel}",
                    "Settlement [ft]: %{z}"])
                ))
                   
            # Plot the Marker Point (MP) labels in grey
            fig.add_trace(go.Scatter3d(
                x=beamInfo3D['labelX'],
                y=beamInfo3D['labelY'],
                z=beamInfo3D['{0}_start'.format(col)],
                text=beamInfo3D['MP_W_S'],
                mode = 'text',
                textfont = dict(
                    size = 10,
                    color = 'grey'),
                hoverinfo='skip',
                showlegend=False, 
                #setting only the first dataframe to be visible as default
                visible = (col==settlementStart.columns[len(settlementStart.columns)-1])
                ))
        
    # groups and trace visibilities
    vis = []
    visList = []

    for  i, col in enumerate(settlementStart.columns):
        n = len(beamInfo3D.index)*2
        vis = ([False]*i*n + [True]*n + [False]*(len(settlementStart.columns)-(i+1))*n)
        visList.append(vis)
        vis = []


    # buttons for each group
    steps = []
    for idx, col in enumerate(settlementStart.columns):
        steps.append(
            dict(
                label = col,
                method = "update",
                args=[{"visible": visList[idx]}])
        )

    sliders = [dict(
        active=len(settlementStart.columns)-1,
        currentvalue={"prefix": "Survey Date: "},
        pad={"t": 20, "b":10},
        len = 0.945,
        x = 0.0,
        steps=steps
    )]

    camera = dict(
        up=dict(x=0, y=0, z=1),
        center=dict(x=0, y=0, z=0),
        eye=dict(x=0, y=4, z=3)
    )

    maxSettlement = settlementStart[settlementStart.columns[len(settlementStart.columns)-1]].max()
    
    fig.update_layout(
        autosize=False,
        margin=dict(l=0, r=0, b=0, t=0),
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
        height = 500,
        scene_aspectmode='manual',
        scene_aspectratio=dict(x=7, y=2, z=1)
    )
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