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
    #survey = pd.ExcelFile(surveyfile)
    #survey = pd.read_excel(survey, 'Data', nrows=36, skiprows=[0,2,3])
    survey = pd.read_csv(surveyfile, skiprows=[1], nrows=36)
    
    # rename second 2010/11/2 survey to 2010/11/3
    #survey_clean = survey.drop(columns=["DESCRIPTION", "Shims\nNote 13", "Unnamed: 52", "Delta"]).rename(columns={"MONITOR\nPOINT":"MONITOR_POINT", "2010-11-02 00:00:00.1":'2010-11-03 00:00:00'})
    survey_clean = survey.drop(columns=["DESCRIPTION", "Shims\nNote 13", "Unnamed: 52", "Delta"]).rename(columns={"MONITOR\nPOINT":"MONITOR_POINT"})
    survey_clean = survey_clean.set_index('MONITOR_POINT').rename_axis('date', axis=1)
    survey_clean.columns = pd.to_datetime(survey_clean.columns).astype(str)

    # Transpose so dayes are in index column
    survey_long = pd.DataFrame.transpose(survey_clean)
    return survey_clean, survey_long

# import beam information and label location

def read_beamInfo():
    beamfile = 'https://raw.githubusercontent.com/wyattreis/SouthPoleStationFoundation/main/SP_BeamArrowLabels.csv'
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

# Create dataframe for 3D plotting
def calc_3d_dataframe(beamInfo, settlement_points):
    beamStart = beamInfo[['MP_W_S', 'beamName']].set_index('MP_W_S')
    settlementStart = beamStart.join(settlement_points).set_index('beamName')
    settlementStart.columns = pd.to_datetime(settlementStart.columns).astype(str)

    beamEnd = beamInfo[['MP_E_N', 'beamName']].set_index('MP_E_N')
    settlementEnd = beamEnd.join(settlement_points).set_index('beamName')
    settlementEnd.columns = pd.to_datetime(settlementEnd.columns).astype(str)

    settlement3D = settlementStart.join(settlementEnd, lsuffix='_start', rsuffix='_end')
    settlement3D = settlement3D[settlement3D.index.notnull()]
    return settlementStart, settlement3D

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

    # Identify the monitor point groupings based on the pod
    maps = {'A1':['A1-1', 'A1-2', 'A1-3', 'A1-4'],
        'A2':['A2-1', 'A2-2', 'A2-3', 'A2-4', 'A2-5','A2-6'],
        'A3':['A3-1', 'A3-2', 'A3-3', 'A3-4'],
        'A4':['A4-1', 'A4-2', 'A4-3', 'A4-4'],
       'B1':['B1-1', 'B1-2', 'B1-3', 'B1-4'],
        'B2':['B2-1', 'B2-2', 'B2-3', 'B2-4', 'B2-5','B2-6'],
        'B3':['B3-1', 'B3-2', 'B3-3', 'B3-4'],
        'B4':['B4-1', 'B4-2', 'B4-3', 'B4-4']}
    
    return beamDir, beamSymbol, beamDiffColor, beamSlopeColor, beamDiffAnno, beamSlopeAnno, color_dict, maps

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
                size = 10,
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
                size = 10,
                color = beamDiffColor[column].values
                ),
            #hoverinfo='skip',
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
        #title = 'Differental Settlement [in] between Monitoring Points'
    )

    # Set axes ranges
    fig.update_xaxes(range=[-25, 415])
    fig.update_yaxes(range=[-15, 140])
    return fig

# Plot differental settlement slope in plan view
def plot_SlopeSttlement_plot(beamSlopeplot, beamInfo, beamSlopeColor, beamSymbol, beamDir, beamSlopeAnno):
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
            size = 10,
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
                size = 12,
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
        #title = 'Differental Slope [in/ft]'
    )

    # Set axes ranges
    fig.update_xaxes(range=[-25, 415])
    fig.update_yaxes(range=[-15, 140])
    return fig

# 3D Plot - settlement 
def plot_3D_settlement(settlementStart, settlement3D, beamInfo, beamDiff):
    fig = go.Figure()

    for col in settlementStart.columns:
        # Plot the beam locations as lines
        for (startX, endX, startY, endY, startZ, endZ) in zip(beamInfo['startX'], beamInfo['endX'], 
                                                            beamInfo['startY'], beamInfo['endY'], 
                                                            settlement3D['{0}_start'.format(col)], 
                                                            settlement3D['{0}_end'.format(col)]):
            fig.add_trace(go.Scatter3d(
                x=[startX, endX],
                y=[startY, endY],
                z = [startZ, endZ],
                text = beamInfo['MP_W_S'],
                #name="",
                mode='lines',
                line = dict(
                    color = 'black',
                    width = 1.5,
                    dash = 'solid'),
                #hoverinfo='skip',
                showlegend=False, 
                #setting only the first dataframe to be visible as default
                visible = (col==beamDiff.columns[len(beamDiff.columns)-1])))
        
        # Plot the Marker Point (MP) labels in grey
            fig.add_trace(go.Scatter3d(
                x=beamInfo['labelX'],
                y=beamInfo['labelY'],
                z=settlement3D['{0}_start'.format(col)],
                text=beamInfo['MP_W_S'],
                mode = 'text',
                textfont = dict(
                    size = 10,
                    color = 'grey'),
                hoverinfo='skip',
                showlegend=False, 
                #setting only the first dataframe to be visible as default
                visible = (col==beamDiff.columns[len(beamDiff.columns)-1])))
            
    fig.update_traces(
        hovertemplate="<br>".join([
            "MP: %{text}",
            "Settlement [in]: %{z}",
        ])
    )
        
    fig.update_scenes(xaxis_autorange="reversed", 
                    yaxis_autorange="reversed",
                    zaxis_autorange="reversed")  

    camera = dict(
        up=dict(x=0, y=0, z=1),
        center=dict(x=0, y=0, z=0),
        eye=dict(x=1.5, y=1.5, z=1.5)
    )

    fig.update_layout(
        autosize=False,
        width=800, 
        height=450,
        margin=dict(l=0, r=0, b=0, t=0),
        scene_camera=camera,
        scene=dict(
            xaxis_title='',
            yaxis_title='',
            zaxis_title='Cumulative Settlement [ft]',
        ),
    )

    # groups and trace visibilities
    vis = []
    visList = []

    for  i, col in enumerate(beamDiff.columns):
        n = len(settlement3D.index)*2
        vis = ([False]*i*n + [True]*n + [False]*(len(beamDiff.columns)-(i+1))*n)
        visList.append(vis)
        vis = []


    # buttons for each group
    buttons = []
    for idx, col in enumerate(beamDiff.columns):
        buttons.append(
            dict(
                label = col,
                method = "update",
                args=[{"visible": visList[idx]}])
        )

    buttons = [{'label': 'Select Survey Date',
                    'method': 'restyle',
                    'args': ['visible', [False]*len(beamDiff.columns)*len(settlement3D.index)]}] + buttons

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons)
        ],
    )
    return fig