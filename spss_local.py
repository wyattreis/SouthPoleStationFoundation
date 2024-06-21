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
nyears = 2

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


print(elevationFloorStart.columns)
# df_in = floorElevPlot

# fig = go.Figure()
# pods = ['A', 'B']
# for pod in pods:
#     df = df_in[[pod in s for s in df_in.index]]

#     for col in df.columns[2:]:
#         # Extract coordinates
#         xs = df['mpX']
#         ys = df['mpY']
#         zs = df[col]

#         # Calculate mean of z values
#         Z_mean = zs.mean()

#         # Define ranges for x and y
#         xlim = [xs.min(), xs.max()]
#         ylim = [ys.min(), ys.max()]

#         # Create meshgrid for the plane surface
#         X, Y = np.meshgrid(np.arange(xlim[0], xlim[1]),
#                         np.arange(ylim[0], ylim[1]))
#         Z_plane = np.ones_like(X) * Z_mean

#         # Add surface trace for the plane
#         fig.add_trace(go.Surface(x=X, y=Y, z=Z_plane,
#                                 colorscale='Viridis', showscale=False, showlegend= True,
#                                 name=f'Plane for {pod} {col}'))

#         # Add scatter trace for the points
#         fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs,
#                                 mode='markers', marker=dict(size=5),
#                                 name=f'Points for {pod} {col}'))
    
# fig.show()

# print(elevationFloorStart)

# df_in = floorElevPlot

# fig = go.Figure()
# pods = ['A', 'B']


# for col in df_in.columns[2:]:
#     for pod in pods:
#         df = df_in[[pod in s for s in df_in.index]]
#         # Extract coordinates
#         xs = df['mpX']
#         ys = df['mpY']
#         zs = df[col]

#         # Calculate mean of z values
#         Z_mean = zs.mean()

#         # Fit plane 
#         tmp_A = []
#         tmp_b = []
#         for i in range(len(xs)):
#             tmp_A.append([xs[i], ys[i], 1])
#             tmp_b.append(zs[i])
#         b = np.matrix(tmp_b).T
#         A = np.matrix(tmp_A)
#         fit = (A.T * A).I * A.T * b

#         # Define ranges for x and y
#         xlim = [xs.min(), xs.max()]
#         ylim = [ys.min(), ys.max()]

#         # Create meshgrid for the plane surface - mean and fitted
#         X, Y = np.meshgrid(np.arange(xlim[0], xlim[1]),
#                         np.arange(ylim[0], ylim[1]))
#         Z_plane_mean = np.ones_like(X) * Z_mean

#         Z_plane_fit = np.zeros(X.shape)

#         for r in range(X.shape[0]):
#             for c in range(X.shape[1]):
#                 Z_plane_fit[r,c] = fit[0] * X[r,c] + fit[1] * Y[r,c] + fit[2]

#         # Add surface trace for the plane - mean
#         fig.add_trace(go.Surface(x=X, y=Y, z=Z_plane_mean,
#                                 colorscale='Viridis', showscale=False, showlegend= True,
#                                 name=f'Mean plane for {pod} {col}'))      
        
#         # Add surface trace for the plane - fit
#         fig.add_trace(go.Surface(x=X, y=Y, z=Z_plane_fit,
#                                 colorscale='Viridis', showscale=False, showlegend= True,
#                                 name=f'Fit plane for {pod} {col}'))

#         # Add scatter trace for the points
#         fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs,
#                                 mode='markers', marker=dict(size=5),
#                                 name=f'Points for {pod} {col}'))
    
# fig.show()



#     # Define a plane using the column data
#     plane = go.Surface(
#         x=[df.iloc[:,0].min(), df.iloc[:,0].max()],
#         y=[df.iloc[:,1].min(), df.iloc[:,1].max()],
#         z=[df[col].mean()],
#         opacity=0.5,
#         showscale=False,
#         name=col  # Set the name of the plane to the column name
#     )
    
#     # Add the plane to the figure
#     fig.add_trace(plane)

# fig.show()


    
#     return Z_a_avg



# Za = meanPlane(df)

# print(Za)


# print(floorElevPlot)

fig_3d_floor_planes = plot_3D_floorElev_slider_animated_planes(elevationFloorStart, elevFloorInfo3D, plot3dAnno, floorElevPlot)
st.plotly_chart(fig_3d_floor_planes)

# planeFit = floorElevPlot
# # planeFit = floorElevPlot.iloc[:,[0,1]].join(gradeBeamElev.iloc[:,48])
# # planeFit.rename(columns={ planeFit.columns[2]: "GBelev" }, inplace = True)

# podA = planeFit[['A' in s for s in planeFit.index]]
# # podB = planeFit[['B' in s for s in planeFit.index]]

# # print(podA)

# xs_A = podA.iloc[:,0]
# ys_A = podA.iloc[:,1]
# zs_A = podA.iloc[:,2]

# # # xs_B = podB.iloc[:,0]
# # # ys_B = podB.iloc[:,1]
# # # zs_B = podB.iloc[:,2]

# do fit - A pod only
# tmp_A = []
# tmp_b = []
# for i in range(len(xs_A)):
#     tmp_A.append([xs_A[i], ys_A[i], 1])
#     tmp_b.append(zs_A[i])
# b = np.matrix(tmp_b).T
# A = np.matrix(tmp_A)
# fit_a = (A.T * A).I * A.T * b
# errors_a = b - A * fit_a
# residual_a = np.linalg.norm(errors_a)

# # # print("solution: %f x + %f y + %f = z" % (fit_a[0], fit_a[1], fit_a[2]))
# # # # print("errors:")
# # # # print(errors)
# # # # print("residual: {}".format(residual))

# # # # do fit - B pod only
# # # tmp_A = []
# # # tmp_b = []
# # # for i in range(len(xs_B)):
# # #     tmp_A.append([xs_B[i], ys_B[i], 1])
# # #     tmp_b.append(zs_B[i])
# # # b = np.matrix(tmp_b).T
# # # A = np.matrix(tmp_A)
# # # fit_b = (A.T * A).I * A.T * b
# # # errors_b = b - A * fit_b
# # # residual_b = np.linalg.norm(errors_b)

# # # # residual_b['MP'] = podA.index
# # # # residual_b.set_index('MP', inplace=True)

# # # # print(residual_b)



# # # # print("solution: %f x + %f y + %f = z" % (fit_b[0], fit_b[1], fit_b[2]))
# # # # print("errors:")
# # # # print(errors_b)
# # # # print("residual: {}".format(errors_b))

# # # # # Z average 
# Z_a_avg = zs_A.mean()
# # # Z_b_avg = zs_B.mean()

# # plot  points and plane
# xlim_A = [min(xs_A), max(xs_A)]
# ylim_A = [min(ys_A), max(ys_A)]

# # # xlim_B = [min(xs_B), max(xs_B)]
# # # ylim_B = [min(ys_B), max(ys_B)]

# X_a,Y_a = np.meshgrid(np.arange(xlim_A[0], xlim_A[1]),
#                   np.arange(ylim_A[0], ylim_A[1]))

# print(X_a)
# # # Z_a = np.zeros(X_a.shape)
# Z_a_mean = np.zeros(X_a.shape)

# # # X_b,Y_b = np.meshgrid(np.arange(xlim_B[0], xlim_B[1]),
# # #                   np.arange(ylim_B[0], ylim_B[1]))
# # # Z_b = np.zeros(X_b.shape)
# # # Z_b_mean = np.zeros(X_b.shape)

# # # for r in range(X_a.shape[0]):
# # #     for c in range(X_a.shape[1]):
# # #         Z_a[r,c] = fit_a[0] * X_a[r,c] + fit_a[1] * Y_a[r,c] + fit_a[2]

# # # for r in range(X_b.shape[0]):
# # #     for c in range(X_b.shape[1]):
# # #         Z_b[r,c] = fit_b[0] * X_b[r,c] + fit_b[1] * Y_b[r,c] + fit_b[2]

# # for r in range(X_a.shape[0]):
# #     for c in range(X_a.shape[1]):
# #         Z_a_mean[r,c] = Z_a_avg


# # # for r in range(X_b.shape[0]):
# # #     for c in range(X_b.shape[1]):
# # #         Z_b_mean[r,c] = Z_b_avg

# # fig = go.Figure()
# # # # fig.add_trace(go.Surface(x=X_a, y=Y_a, z=Z_a))
# # # # fig.add_trace(go.Surface(x=X_b, y=Y_b, z=Z_b))
# # fig.add_trace(go.Surface(x=X_a, y=Y_a, z=Z_a_mean))
# # fig.add_trace(go.Surface(x=X_b, y=Y_b, z=Z_b_mean))
# # fig.add_trace(go.Scatter3d(
# #                 x=planeFit['mpX'],
# #                 y=planeFit['mpY'],
# #                 z=planeFit.iloc[:,2],
# #                 mode = 'markers'
# #                 ))

# # Update layout for slider and set consistent y-axis range
# # fig.update_layout(
# #     autosize=False,
# #     margin=dict(l=0, r=0, b=100, t=0),
# #     scene=dict(
# #         xaxis_title='',
# #         xaxis= dict(range=[400,-10]), 
# #         yaxis_title='',
# #         yaxis= dict(range=[130,-10]),
# #         zaxis_title='Elevation [ft]'),
# #     width = 1100,
# #     height = 600,
# #     scene_aspectmode='manual',
# #     scene_aspectratio=dict(x=7, y=2, z=1),
# #     uniformtext_minsize=10,
# #     annotations = plot3dAnno
# #     )

# fig.show()