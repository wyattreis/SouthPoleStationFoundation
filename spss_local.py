# -------------------------------------------------------------------------------
# Name          South Pole Station Settlement Frontend
# Description:  Streamlit app to display the plots and forcast tools of the
#               South Pole Station settlement. 
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
import scipy.stats as stats
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt
from utils import *

xlfile = "C:/Users/RDCRLWKR/Documents/FileCloud/My Files/Active Projects/NSF USAP/South Pole Foundation/Technical/Data/SP Settlement Analysis_2023.01.15_BPod_reordered_20240105.xlsx"

# Set forecasting variables
nsurvey = 6
nyears = 5

# Calculate data for plotting 
## DATA IMPORTING & ANALYSIS
# Import the survey data for the south pole station
survey_clean, survey_long = read_xlElev(xlfile)
truss_clean = read_xlTruss(xlfile)
shim_clean = read_xlShim(xlfile)

# Import the basic plotting file to use (label locations, building outline, etc.), and calculate the beam length between each column 
beamInfo, beamLength, MPlocations, beamLength_long, beamLength_sort = read_beamInfo()
# Calculate settlement at the column lugs from the survey file
elevation, gradeBeamElev, gradeBeamElevPlot,  settlement, settlement_points, settlement_delta, settlement_delta_MP, settlement_rate = calc_settlement(survey_long, survey_clean, truss_clean, shim_clean, MPlocations)
# Forecast future settlement for user defined future using user defined previous number of years
settlementProj, settlementProj_trans = calc_forecast_settlement(settlement, nsurvey, nyears)
#Forecast the future floor elevations
elevProj, elevProj_trans, elevFloorProj, elevGradeBeamProj = calc_forecast_elevation(elevation, truss_clean, nsurvey, nyears)
# Calculate the floor elevation differences and slopes accounting for known lug to truss height (shim height)
lugElevPlot, lugFloorPlot, floorElevPlot, floorDiff, floorDiffplot, floorSlope, floorSlopeplot, shimElevPlot = calc_plan_dataframe(survey_clean, truss_clean, shim_clean, MPlocations, beamLength_long, beamLength_sort, beamInfo)
# Calculate the error between fitted planes and the column elevations
error_meanFloor, error_fitFloor, error_stdFloor, slopes_fitFloor, error_meanGradeBeam, error_fitGradeBeam, error_stdGradeBeam, slopes_fitGradeBeam = calc_plane_error(floorElevPlot, gradeBeamElevPlot)
# Calculate the differental settlement between column lugs
beamDiff, beamDiffProj, beamDiffplot, beamSlope, beamSlopeplot, beamSlopeProj, floorDiffElev, floorDiffProj = calc_differental_settlement(beamLength_long, beamLength_sort, survey_clean, beamInfo, settlementProj_trans, elevFloorProj, floorElevPlot)
# Create dataframe for Beam Plotting Styles
beamDirLabels, beamDir, beamSymbol, beamDiffColor, beamSlopeColor, beamSlopeProjColor = plot_beamStyles(beamInfo, beamDiff, beamSlope, beamSlopeProj)
# Create dataframe for floor elevation plotting styles
floorDir, floorSymbolplot, floorDiffColorplot, floorSlopeColorplot = plot_floorStyles(beamDirLabels, beamInfo, floorDiff, floorDiffplot, floorSlope, floorSlopeplot)
# Create dataframe for plot annotations
beamDiffAnno, beamSlopeAnno, diffAnno, slopeAnno, plot3dAnno, color_dict, color_dictBeams, maps, mapsBeams, mapsPods, mapsGradeBeams = plot_annotations()
# Create dataframe for 3D plotting
settlementStart, beamInfo3D = calc_3d_dataframe(beamInfo, settlement_points, settlementProj_trans, beamSlopeColor, beamSlopeProjColor)
elevationFloorStart, elevFloorInfo3D = calc_3d_floorElev(beamInfo, floorElevPlot, elevFloorProj, beamSlopeColor, beamSlopeProjColor)
elevationGBStart, elevGBInfo3D = calc_3d_gradeBeamElev(beamInfo, gradeBeamElev, elevGradeBeamProj, beamSlopeColor, beamSlopeProjColor)
#Calculate Grade Beam Differental 
df_GradeBeams, gradeBeam_diff = calc_GradeBeam_profiles(gradeBeamElevPlot)


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
        {'label': 'All', 'method': 'update', 'args': [{'visible': [True] * len(fig.data)}]},  # Show all
        {'label': 'Pod A', 'method': 'update', 'args': [{'visible': [True if 'A' in trace.name else False for trace in fig.data]}]},  # Show only Pod A
        {'label': 'Pod B', 'method': 'update', 'args': [{'visible': [True if 'B' in trace.name else False for trace in fig.data]}]}   # Show only Pod B
    ]

    # Update layout with dropdown
    fig.update_layout(
        xaxis_title='Survey Date',
        yaxis_title='Slope [%]',
        # legend_title='Slope Types',
        # hovermode='x unified',
        updatemenus=[{
            'buttons': dropdown_buttons,
            'direction': 'down',
            'showactive': True,
        }]
    )

    return fig
