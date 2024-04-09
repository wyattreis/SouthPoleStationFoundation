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
nsurvey = 10
nyears = 5

# Calculate data for plotting 
## DATA IMPORTING & ANALYSIS
# Import the survey data for the south pole station
survey_clean, survey_long = read_xlElev(xlfile)
truss_clean = read_xlTruss(xlfile)

# Import the basic plotting file to use (label locations, building outline, etc.), and calculate the beam length between each column 
beamInfo, beamLength, MPlocations, beamLength_long, beamLength_sort = read_beamInfo()
# Calculate settlement at the column lugs from the survey file
settlement, settlement_points, settlement_delta, settlement_delta_MP, settlement_rate = calc_settlement(survey_long)
# Forecast future settlement for user defined future using user defined previous number of years
settlementProj, settlementProj_trans = calc_forecast_settlement(settlement, nsurvey, nyears)
# Calculate the differental settlement between column lugs
beamDiff, beamDiffplot, beamSlope, beamSlopeplot, beamSlopeProj = calc_differental_settlement(beamLength_long, beamLength_sort, survey_clean, beamInfo, settlementProj_trans)
# Calculate the floor elevation differences and slopes accounting for known lug to truss height (shim height)
lugElevPlot, lugFloorPlot, floorElevPlot, floorDiff, floorDiffplot, floorSlope, floorSlopeplot = calc_plan_dataframe (survey_clean, truss_clean, MPlocations, beamLength_long, beamLength_sort, beamInfo)
# Create dataframe for Beam Plotting Styles
beamDirLabels, beamDir, beamSymbol, beamDiffColor, beamSlopeColor, beamSlopeProjColor = plot_beamStyles(beamInfo, beamDiff, beamSlope, beamSlopeProj)
# Create dataframe for floor elevation plotting styles
floorDir, floorSymbolplot, floorDiffColorplot, floorSlopeColorplot = plot_floorStyles(beamDirLabels, beamInfo, floorDiff, floorDiffplot, floorSlope, floorSlopeplot)
# Create dataframe for plot annotations
beamDiffAnno, beamSlopeAnno, diffAnno, slopeAnno, plot3dAnno, color_dict, maps = plot_annotations()
# Create dataframe for 3D plotting
settlementStart, beamInfo3D = calc_3d_dataframe(beamInfo, settlement_points, settlementProj_trans, beamSlopeColor, beamSlopeProjColor)
settlementFloorStart, floorInfo3D = calc_3d_floorElev(beamInfo, floorElevPlot, settlementProj_trans, beamSlopeColor, beamSlopeProjColor)

survey_long['dummy']= 1
firstValue = survey_long.groupby('dummy').first()
firstValue = firstValue.to_numpy()[0]
print(firstValue)

# elevation = survey_long.drop(columns=["dummy"]).apply(lambda row: firstValue - row, axis=1)
# settlement.index = pd.to_datetime(settlement.index)

elevInterp = survey_long.iloc[(len(survey_long.index)-(nsurvey)):(len(survey_long.index))]
settlementInterp = settlement.iloc[(len(settlement.index)-(nsurvey)):(len(settlement.index))]
# currentYear = elevInterp.index.year[-1]

print(elevInterp)
print(settlementInterp)

# projList = []
# for year in range(nyears):
#     projYear = (currentYear + year+1).astype(str)
#     projYear = pd.to_datetime(projYear + '-01-01') 
#     projList.append(projYear)

# settlementExtrap = pd.DataFrame(columns=settlementInterp.columns, index = [projList]).reset_index().set_index('level_0')
# settlementExtrap.index = settlementExtrap.index.map(dt.datetime.toordinal)
# settlementInterp.index = settlementInterp.index.map(dt.datetime.toordinal)

# x_endpoints = list([settlementInterp.index[0], settlementInterp.index[nsurvey-1]]) + settlementExtrap.index.tolist()
# x_enddates = pd.DataFrame(x_endpoints)

# df_regression = settlementInterp.apply(lambda x: stats.linregress(settlementInterp.index, x), result_type='expand').rename(index={0: 'slope', 1: 
#                                                                                 'intercept', 2: 'rvalue', 3:
#                                                                                 'p-value', 4:'stderr'})

# new_data_loc = {}
# for column in df_regression.columns:   
#     slope = df_regression.loc['slope', column]  
#     intercept = df_regression.loc['intercept', column]  
#     new_data_loc[column] = [slope * val + intercept for val in x_endpoints]

# settlementProj = pd.DataFrame([new_data_loc], columns=new_data_loc.keys()).apply(pd.Series.explode).reset_index().drop(['index'], axis = 1)
# settlementProj = x_enddates.join(settlementProj).set_index(0)
# settlementProj.index.names = ['date']
# settlementProj.index = settlementProj.index.map(dt.datetime.fromordinal)
# settlementProj = settlementProj.apply(pd.to_numeric, errors='ignore').round(3)

# settlementProj_trans = settlementProj
# settlementProj_trans.index = settlementProj_trans.index.strftime('%Y-%m-%d') 
# settlementProj_trans = pd.DataFrame.transpose(settlementProj_trans).iloc[:,2:]



# currentElev = survey_clean.iloc[:,-1]
# print(currentElev)

# projectedElev = settlementProj_trans.sub(currentElev, axis=0)

# print(projectedElev)






# # Differental Settlement Planview
# fig_diff_plan = plot_DiffSettlement_plan(beamDiffplot, beamInfo, beamDiffColor, beamSymbol, beamDir, beamDiffAnno)

# # Differental Settlement Slope Planview
# fig_slope_plan = plot_SlopeSettlement_plan(beamSlopeplot, beamInfo, beamSlopeColor, beamSymbol, beamDir, beamSlopeAnno)

# # Differental Floor Elevation Planview 
# fig_floorElev_plan = plot_floorDiffElev_plan(floorDiffColorplot, beamInfo, floorDiffplot, floorSymbolplot, floorDir, floorElevPlot, diffAnno)
# fig_floorElev_plan.show()

# # Differental Floor Slope Planview
# fig_floorSlope_plan = plot_floorSlopeElev_plan(floorSlopeColorplot, beamInfo, floorSlopeplot, floorSymbolplot, floorElevPlot, floorDir, slopeAnno)

# # Lug Elevation
# fig_lugElev_plan = plot_lugElev_plan(lugElevPlot, beamInfo)

# # Lug to Floor Height
# fig_lugTrussHeight_plan = plot_lugFloorHeight_plan(lugFloorPlot, beamInfo)

# # # Create Streamlit Plot objects - Plan Figure
# # tab1, tab2, tab3, tab4 = st.tabs(["Differental Floor Elevation [in]", "Differental Floor Slope [in/ft]", 
# #                             "Lug Elevation [ft]", "Lug to Truss Height [ft]"])
# # with tab1:
# #     # Use the Streamlit theme.
# #     # This is the default. So you can also omit the theme argument.
# #     st.plotly_chart(fig_floorElev_plan, use_container_width=True, height=600)
# # with tab2:
# #     # Use the native Plotly theme.
# #     st.plotly_chart(fig_floorSlope_plan, use_container_width=True, height=600)
# # with tab3: 
# #     st.plotly_chart(fig_lugElev_plan, use_container_width=True, height=600)
# # with tab4:
# #     st.plotly_chart(fig_lugTrussHeight_plan, use_container_width=True, height=600)

# # Cumulative settlement
# fig_cumulative = plot_cumulative_settlement(settlement, settlementProj, color_dict, maps)

# # Delta Settlement
# fig_delta = plot_delta_settlement(settlement_delta, color_dict, maps)

# # Settlement Rate
# fig_rate = plot_settlementRate(settlement_rate, color_dict, maps)

# # # Create Streamlit Plot objects - Plan Figure
# # tab1, tab2 = st.tabs(["Cumulative Settlement [ft]", "Annualized Settlement Rate [in/yr]"])
# # with tab1:
# #     # Use the Streamlit theme.
# #     # This is the default. So you can also omit the theme argument.
# #     st.plotly_chart(fig_cumulative, use_container_width=True, height=600)
# # with tab2:
# #     # Use the native Plotly theme.
# #     st.plotly_chart(fig_rate, use_container_width=True, height=600)

# # # Differental Settlement 3D
# # left_co, cent_co,last_co = st.columns([0.025, 0.95, 0.025])
# # with cent_co:
# fig_3d_slider = plot_3D_settlement_slider_animated(settlementStart, beamInfo3D)
# fig_3d_slider.show()
# #     st.plotly_chart(fig_3d_slider, width = 1100, height = 800)