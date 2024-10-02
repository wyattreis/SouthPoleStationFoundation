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

## DATA IMPORTING
# Import the survey data for the south pole station
survey_clean = read_xl(xlfile, 'SURVEY DATA')
truss_clean = read_xl(xlfile, 'TRUSS DATA')
shim_clean = read_xl(xlfile, 'SHIM DATA').div(12) 

# Import the basic plotting file to use (label locations, building outline, etc.), and calculate the beam length between each column 
beamInfo, beamLength, MPlocations, beamLength_long, beamLength_sort = read_beamInfo()


# DATA ANALYSIS
# Calculate settlement at the column lugs from the survey file
elevation, gradeBeamElev, gradeBeamElevPlot,  settlement, settlement_points, settlement_delta, settlement_delta_MP, settlement_rate = calc_settlement(survey_clean, truss_clean, shim_clean, MPlocations)
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
beamDirLabels, beamDir, beamSymbol, beamDiffColor, beamSlopeColor, beamSlopeProjColor = plot_beamStyles(beamInfo, beamDiff, beamSlope, beamSlopeProj, floorDiffElev)
# Create dataframe for floor elevation plotting styles
floorDir, floorSymbolplot, floorDiffColor, floorDiffColorplot, floorSlopeColorplot = plot_floorStyles(beamDirLabels, beamInfo, floorDiff, floorDiffplot, floorSlope, floorSlopeplot)
# Create dataframe for plot annotations
beamDiffAnno, beamSlopeAnno, diffAnno, plot3dAnnoDiff, slopeAnno, plot3dAnno, color_dict, color_dictBeams, maps, mapsBeams, mapsPods, mapsGradeBeams = plot_annotations()
# Create dataframe for 3D plotting
settlementStart, beamInfo3D = calc_3d_dataframe(beamInfo, settlement_points, settlementProj_trans, beamSlopeColor, beamSlopeProjColor)
elevationFloorStart, elevFloorInfo3D = calc_3d_floorElev(beamInfo, floorElevPlot, elevFloorProj, floorDiffColor, beamSlopeProjColor)
elevationGBStart, elevGBInfo3D = calc_3d_gradeBeamElev(beamInfo, gradeBeamElev, elevGradeBeamProj, beamSlopeColor, beamSlopeProjColor)
#Calculate Grade Beam Differental 
df_GradeBeams, gradeBeam_diff = calc_GradeBeam_profiles(gradeBeamElevPlot)
