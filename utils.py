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
# Updated:      -
#
# -------------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
from scipy import interpolate
import plotly.express as px
import plotly.graph_objects as go

# import survey dataframe and return clean version
def read_survey(surveyfile):
    survey = pd.ExcelFile(surveyfile)
    survey = pd.read_excel(survey, 'Data', nrows=36, skiprows=[0,2,3])
    
    # rename second 2010/11/2 survey to 2010/11/3
    survey_clean = survey.drop(columns=["DESCRIPTION", "Shims\nNote 13", "Unnamed: 52", "Delta"]).rename(columns={"MONITOR\nPOINT":"MONITOR_POINT", "2010-11-02 00:00:00.1":'2010-11-03 00:00:00'})
    survey_clean = survey_clean.set_index('MONITOR_POINT').rename_axis('date', axis=1)
    survey_clean.columns = pd.to_datetime(survey_clean.columns).astype(str)

    # Transpose so dayes are in index column
    survey_long = pd.DataFrame.transpose(survey_clean)
    return survey_clean, survey_long

# import beam information and label location
def read_beamInfo(beamfile):
    beamInfo = pd.read_csv(beamfile)
    beamLength = beamInfo[['MP_W_S', 'MP_E_N', 'beamName', 'beamLength']].dropna()
    return beamInfo, beamLength

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
    return settlement, settlement_points, settlement_delta, settlement_delta_MP

# Cumulative Settlement Forecasting
def calc_forecast_settlement(settlement, nsurvey, nyears):
    settlementInterp = settlement.iloc[[(len(settlement.index)-(nsurvey)),(len(settlement.index)-1)]]
    currentYear = settlementInterp.index.year[1]

    projList = []
    for year in range(nyears):
        projYear = (currentYear + year+1).astype(str)
        projYear = pd.to_datetime(projYear + '-01-01') 
        projList.append(projYear)

    settlementExtrap = pd.DataFrame(columns=settlementInterp.columns, index = [projList]).reset_index().set_index('level_0')
    settlementProj = pd.concat([settlementInterp,settlementExtrap])

    settlementProj = settlementProj.interpolate(method="slinear", fill_value="extrapolate", limit_direction="both")
    return settlementProj

# Calculate differental settlement
def calc_differental_settlement(beamLength, survey_clean, beamInfo):
    # Convert the beam length file to long format and make index the east or south Monitoring Point for each beam
    beamLength_long = pd.melt(beamLength, id_vars=['beamName', 'beamLength']).rename(columns={'value':'MONITOR_POINT', 'variable':'beamEnd'})
    beamLength_long.set_index('MONITOR_POINT', inplace = True)
    beamLength_sort = beamLength_long.drop(columns=['beamEnd']).sort_values('beamName').set_index('beamName')
    beamLength_sort = beamLength_sort[~beamLength_sort.index.duplicated(keep='first')]
    
    # Merge the beam file and the settlement file
    beamSettlement = beamLength_long.join(survey_clean)

    # Group by beamName, difference, and convert to inches, keep only the differenced values
    beamDiff = beamSettlement.set_index(['beamName']).sort_values(by=['beamName', 'beamEnd']).drop(columns=['beamEnd', 'beamLength']).groupby(['beamName']).diff().mul(12)
    beamDiff = beamDiff[~beamDiff.index.duplicated(keep='last')]
    beamDiff.columns = pd.to_datetime(beamDiff.columns).astype(str)
    beamDiffplot = beamInfo[['beamName', 'beamX', 'beamY']].dropna().set_index(['beamName']).join(beamDiff)
    beamDiff = beamDiffplot.drop(columns=['beamX', 'beamY'])

    # Calculate the slope for each beam, transpose for ploting 
    beamSlope = beamLength_sort.join(beamDiff)
    beamSlope.iloc[:,1:] = beamSlope.iloc[:,1:].div(beamSlope.beamLength, axis=0)
    beamSlopeplot = beamInfo[['beamName', 'beamX', 'beamY']].dropna().set_index(['beamName']).join(beamSlope)
    beamSlope = beamSlopeplot.drop(columns=['beamX', 'beamY', 'beamLength'])
    return beamDiff, beamDiffplot, beamSlope, beamSlopeplot

# Annotation for plots
def plot_annotations(beamInfo, beamDiff, beamSlope):
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
            y=-0.1, yref="paper", yanchor="bottom",
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
            y=-0.1, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False, 
            font = dict(
                color = 'black')
           )
   ])
    return beamDir, beamSymbol, beamDiffColor, beamSlopeColor, beamDiffAnno, beamSlopeAnno

# Plot Cumulative Settlement
def plot_cumulative_settlement(settlement, settlementProj):
    df = settlement 

    # Identify the monitor point groupings based on the pod
    maps = {'A1':['A1-1', 'A1-2', 'A1-3', 'A1-4'],
        'A2':['A2-1', 'A2-2', 'A2-3', 'A2-4', 'A2-5','A2-6'],
        'A3':['A3-1', 'A3-2', 'A3-3', 'A3-4'],
        'A4':['A4-1', 'A4-2', 'A4-3', 'A4-4'],
       'B1':['B1-1', 'B1-2', 'B1-3', 'B1-4'],
        'B2':['B2-1', 'B2-2', 'B2-3', 'B2-4', 'B2-5','B2-6'],
        'B3':['B3-1', 'B3-2', 'B3-3', 'B3-4'],
        'B4':['B4-1', 'B4-2', 'B4-3', 'B4-4']}

    # column: color - assign each monitor point a specifc color
    color_dict = {
    'A1-1': '#7fc97f', 'A1-2': '#beaed4', 'A1-3': '#fdc086', 'A1-4': '#ffff99',
    'A2-1': '#7fc97f', 'A2-2': '#beaed4', 'A2-3': '#fdc086', 'A2-4': '#ffff99', 'A2-5': '#386cb0','A2-6': '#f0027f',
    'A3-1': '#7fc97f', 'A3-2': '#beaed4', 'A3-3': '#fdc086', 'A3-4': '#ffff99',
    'A4-1': '#7fc97f', 'A4-2': '#beaed4', 'A4-3': '#fdc086', 'A4-4': '#ffff99',
    'B1-1': '#7fc97f', 'B1-2': '#beaed4', 'B1-3': '#fdc086', 'B1-4': '#ffff99',
    'B2-1': '#7fc97f', 'B2-2': '#beaed4', 'B2-3': '#fdc086', 'B2-4': '#ffff99', 'B2-5': '#386cb0','B2-6': '#f0027f',
    'B3-1': '#7fc97f', 'B3-2': '#beaed4', 'B3-3': '#fdc086', 'B3-4': '#ffff99',
    'B4-1': '#7fc97f', 'B4-2': '#beaed4', 'B4-3': '#fdc086', 'B4-4': '#ffff99'}

    color = settlement.columns.map(color_dict)

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
    )
    return fig



