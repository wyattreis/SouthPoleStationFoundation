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

# Import the basic plotting file to use (label locations, building outline, etc.), and calculate the beam length between each column 
beamInfo, beamLength, MPlocations, beamLength_long, beamLength_sort = read_beamInfo()
# Calculate settlement at the column lugs from the survey file
elevation, gradeBeamElev, settlement, settlement_points, settlement_delta, settlement_delta_MP, settlement_rate = calc_settlement(survey_long)
# Forecast future settlement for user defined future using user defined previous number of years
settlementProj, settlementProj_trans = calc_forecast_settlement(settlement, nsurvey, nyears)
#Forecast the future floor elevations
elevProj, elevProj_trans, elevFloorProj, elevGradeBeamProj = calc_forecast_elevation(elevation, truss_clean, nsurvey, nyears)
# Calculate the floor elevation differences and slopes accounting for known lug to truss height (shim height)
lugElevPlot, lugFloorPlot, floorElevPlot, floorDiff, floorDiffplot, floorSlope, floorSlopeplot = calc_plan_dataframe (survey_clean, truss_clean, MPlocations, beamLength_long, beamLength_sort, beamInfo)
# Calculate the differental settlement between column lugs
beamDiff, beamDiffProj, beamDiffplot, beamSlope, beamSlopeplot, beamSlopeProj, floorDiffElev = calc_differental_settlement(beamLength_long, beamLength_sort, survey_clean, beamInfo, settlementProj_trans, elevFloorProj, floorElevPlot)
# Create dataframe for Beam Plotting Styles
beamDirLabels, beamDir, beamSymbol, beamDiffColor, beamSlopeColor, beamSlopeProjColor = plot_beamStyles(beamInfo, beamDiff, beamSlope, beamSlopeProj)
# Create dataframe for floor elevation plotting styles
floorDir, floorSymbolplot, floorDiffColorplot, floorSlopeColorplot = plot_floorStyles(beamDirLabels, beamInfo, floorDiff, floorDiffplot, floorSlope, floorSlopeplot)
# Create dataframe for plot annotations
beamDiffAnno, beamSlopeAnno, diffAnno, slopeAnno, plot3dAnno, color_dict, color_dictBeams, maps, mapsBeams = plot_annotations()
# Create dataframe for 3D plotting
settlementStart, beamInfo3D = calc_3d_dataframe(beamInfo, settlement_points, settlementProj_trans, beamSlopeColor, beamSlopeProjColor)
elevationFloorStart, elevFloorInfo3D = calc_3d_floorElev(beamInfo, floorElevPlot, elevFloorProj, beamSlopeColor, beamSlopeProjColor)
elevationGBStart, elevGBInfo3D = calc_3d_gradeBeamElev(beamInfo, gradeBeamElev, elevGradeBeamProj, beamSlopeColor, beamSlopeProjColor)


df = floorDiffElev.transpose()
df= df.drop('2022-01-07')
#df = df[['A2-6 - A2-5','A1-2 - A1-1','A1-3 - A1-2','A3-2 - A2-6','B1-1 - B2-1','B2-6 - B2-2','B4-1 - B3-4','B4-3 - B4-2','B3-1 - B2-2']]
print(df.columns)

# fig_cumulative = plot_cumulative_settlement(settlement, settlementProj, color_dict, maps)
# fig_cumulative.show()

# floorElevPLot = plot_floorElev_timeseries(floorElevPlot, elevFloorProj, color_dict, maps)
# floorElevPLot.show()

floorDiff = floorDifferential(floorDiffElev, color_dictBeams, mapsBeams)
floorDiff.show(height=600)