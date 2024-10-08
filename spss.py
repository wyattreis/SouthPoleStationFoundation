# -------------------------------------------------------------------------------
# Name          South Pole Station Settlement Frontend
# Description:  Streamlit app to display the plots and forcast tools of the
#               South Pole Station settlement. 
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
from utils import *

st.set_page_config(layout="wide")

left_co, cent_co,last_co = st.columns([0.05, 0.9, 0.05])
with cent_co:

    htp = 'https://github.com/wyattreis/SouthPoleStationFoundation/blob/main/southpole_fromB_cropped.jpg?raw=true'
    st.image(htp, use_column_width=True, caption='Amundsen-Scott South Pole Station. Credit: Marc Ankenbauer (2013)')

left_co, cent_co,last_co = st.columns([0.25, 0.5, 0.25])
with cent_co:
    st.title('Amundsen-Scott South Pole Station', anchor=False)

left_co, cent_co,last_co = st.columns([0.15, 0.7, 0.15])
with cent_co:
    st.title('Foundation Settlement Visualization and Analysis', anchor=False)

st.sidebar.title('Survey Data and Forecast Options:')

# Import the South Pole Station excel survey and beam information fils
xlfile = st.sidebar.file_uploader("Upload South Pole Station Survey File", type = ['xlsx'])

# Set forecasting variables
nsurvey = st.sidebar.number_input('Number of Past Surveys Used for Forecast', value=6)
nyears = st.sidebar.number_input('Number of Years Forecasted', value=5)

if st.sidebar.button('Compute Settlement'):

    ## DATA IMPORTING & ANALYSIS
    # Import the survey data for the south pole station
    survey_clean = read_xl(xlfile, 'SURVEY DATA')
    truss_clean = read_xl(xlfile, 'TRUSS DATA')
    shim_clean = read_xl(xlfile, 'SHIM DATA').div(12) # convert from inches to feet

    # Import the basic plotting file to use (label locations, building outline, etc.), and calculate the beam length between each column 
    beamInfo, beamLength, MPlocations, beamLength_long, beamLength_sort = read_beamInfo()

    # Calculate settlement at the column lugs from the survey file
    elevation, gradeBeamElev, gradeBeamElevPlot,  settlement, settlement_points, settlement_delta, settlement_delta_MP, settlement_rate = calc_settlement(survey_clean, truss_clean, shim_clean, MPlocations)
    # Forecast future settlement for user defined future using user defined previous number of years
    settlementProj, settlementProj_trans = calc_forecast_settlement(settlement, nsurvey, nyears)
    #Forecast the future floor elevations
    elevProj, elevProj_trans, elevFloorProj, elevGradeBeamProj = calc_forecast_elevation(elevation, truss_clean, nsurvey, nyears)
    # Calculate the floor elevation differences and slopes accounting for known lug to truss height (shim height)
    lugElevPlot, lugFloorPlot, floorElevPlot, floorDiff, floorDiffplot, floorSlope, floorSlopeplot, shimElevPlot, gradeBeamDiff = calc_plan_dataframe(survey_clean, truss_clean, shim_clean, MPlocations, beamLength_long, beamLength_sort, beamInfo, gradeBeamElev)
    # Calculate the error between fitted planes and the column elevations
    error_meanFloor, error_fitFloor, error_stdFloor, slopes_fitFloor, error_meanGradeBeam, error_fitGradeBeam, error_stdGradeBeam, slopes_fitGradeBeam = calc_plane_error(floorElevPlot, gradeBeamElevPlot)
    # Calculate the differental settlement between column lugs
    beamDiff, beamDiffProj, beamDiffplot, beamSlope, beamSlopeplot, beamSlopeProj, floorDiffElev, floorDiffProj = calc_differental_settlement(beamLength_long, beamLength_sort, survey_clean, beamInfo, settlementProj_trans, elevFloorProj, floorElevPlot)
    # Create dataframe for Beam Plotting Styles
    beamDirLabels, beamDir, beamSymbol, beamDiffColor, beamSlopeColor, beamSlopeProjColor = plot_beamStyles(beamInfo, beamDiff, beamSlope, beamSlopeProj, floorDiffElev)
    # Create dataframe for floor elevation plotting styles
    floorDir, floorSymbolplot, floorDiffColor, floorDiffColorplot, floorSlopeColorplot, gradeBeamDiffColor = plot_floorStyles(beamDirLabels, beamInfo, floorDiff, floorDiffplot, floorSlope, floorSlopeplot, gradeBeamDiff)
    # Create dataframe for plot annotations
    beamDiffAnno, beamSlopeAnno, diffAnno, plot3dAnnoDiff, slopeAnno, plot3dAnno, color_dict, color_dictBeams, maps, mapsBeams, mapsPods, mapsGradeBeams = plot_annotations()
    # Create dataframe for 3D plotting
    settlementStart, beamInfo3D = calc_3d_dataframe(beamInfo, settlement_points, settlementProj_trans, beamSlopeColor, beamSlopeProjColor)
    elevationFloorStart, elevFloorInfo3D = calc_3d_floorElev(beamInfo, floorElevPlot, elevFloorProj, floorDiffColor, beamSlopeProjColor)
    elevationGBStart, elevGBInfo3D = calc_3d_gradeBeamElev(beamInfo, gradeBeamElev, elevGradeBeamProj, gradeBeamDiffColor, beamSlopeProjColor)
    #Calculate Grade Beam Differental 
    df_GradeBeams, gradeBeam_diff = calc_GradeBeam_profiles(gradeBeamElevPlot)
    
    ## PLANVIEW PLOTTING
    # # Differental Settlement Planview
    # fig_diff_plan = plot_DiffSettlement_plan(beamDiffplot, beamInfo, beamDiffColor, beamSymbol, beamDir, beamDiffAnno)
    # # Differental Settlement Slope Planview
    # fig_slope_plan = plot_SlopeSettlement_plan(beamSlopeplot, beamInfo, beamSlopeColor, beamSymbol, beamDir, beamSlopeAnno)
    # Differental Floor Elevation Planview 
    fig_floorElev_plan = plot_floorDiffElev_plan(floorDiffColorplot, beamInfo, floorDiffplot, floorSymbolplot, floorDir, floorElevPlot, diffAnno)
    # Differental Floor Slope Planview
    fig_floorSlope_plan = plot_floorSlopeElev_plan(floorSlopeColorplot, beamInfo, floorSlopeplot, floorSymbolplot, floorElevPlot, floorDir, slopeAnno)
    # Lug Elevation
    fig_lugElev_plan = plot_lugElev_plan(lugElevPlot, beamInfo)
    # Lug to Floor Height
    fig_lugTrussHeight_plan = plot_lugFloorHeight_plan(lugFloorPlot, beamInfo)
    # Shim Height
    fig_shimHeight_plan = plot_shimHeight_plan(shimElevPlot, beamInfo)

    # Create heading heading for the plan view plot that describes each tab of the plot
    st.subheader("Plan View Plots")

    # Create Streamlit Plot objects - Plan Figure
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Differental Floor Elevation [in]", "Floor Slope [in/ft]", 
                                "Lug Elevation [ft]", "Lug to Truss Height [ft]", "Shim Height [in]"])
    with tab1:
        st.text("The differential elevations (in inches) of the floor between each column. The floor elevation is calculated from the survey lug elevation plus the lug to truss height.  \nData is limited to the period where shim pack heights are known.")
        st.plotly_chart(fig_floorElev_plan, use_container_width=True, height=600)
    with tab2:
        st.text("The slope (in inches per foot) of the station floor between each column using the differental floor elevations at each column and the known distances between each column.  \nData is limited to the period where shim pack heights are known.")
        st.plotly_chart(fig_floorSlope_plan, use_container_width=True, height=600)
    with tab3:
        st.text("The elevation (in feet) of the column lugs used to survey the station settlement.  \nAll survey dates are included.")
        st.plotly_chart(fig_lugElev_plan, use_container_width=True, height=600)
    with tab4:
        st.text("The height (in feet) between the lug survey points and the bottom of the floor trusses, this measurement includes the shim pack height.  \nData is limited to the period where shim pack heights are known.")
        st.plotly_chart(fig_lugTrussHeight_plan, use_container_width=True, height=600)
    with tab5:
        st.text("The shim height (in inches).  \nData is limited to the period where shim pack heights are known.")
        st.plotly_chart(fig_shimHeight_plan, use_container_width=True, height=600)

    ## TIMESERIES PLOTTING
    # Cumulative settlement
    fig_cumulative = plot_cumulative_settlement(settlement, settlementProj, color_dict, maps)
    # Settlement Rate
    fig_rate = plot_settlementRate(settlement_rate, color_dict, maps)
    # Floor Elevation 
    fig_floorElev = plot_elev_timeseries(floorElevPlot, color_dict, maps)
    #Grade Beam Elevation
    fig_gradeBeamElev = plot_elev_timeseries(gradeBeamElevPlot, color_dict, maps)
    # Differential between columns timeseries
    floorDiff = floorDifferential(floorDiffElev, floorElevPlot, color_dictBeams, mapsBeams)
    #Grade Beam Profiles
    gradeBeamProfile = plot_GradeBeam_profiles(df_GradeBeams)
    # Max Grade Beam Elevation Difference 
    gradeBeamProfile_diff = plot_GradeBeamElev_diff(gradeBeam_diff , mapsGradeBeams)
    
    st.subheader("Time Series Plots")
    # Create Streamlit Plot objects - Plan Figure
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Cumulative Settlement [ft]", "Annualized Settlement Rate [in/yr]", 
                                                        "Floor Elevation [ft]", "Grade Beam Elevation [ft]",
                                                        "Column Pair Floor Differential [in]",
                                                        "Grade Beam Elevation Profiles [ft]", "Max Grade Beam Elevation Difference [in]"])
    with tab1:
        st.text("The cumulative settlement (in feet) of the station based on the survey lugs.  \nProjected settlement was calculated without including the 2022 survey.  \nAll survey dates are included.")
        st.plotly_chart(fig_cumulative, use_container_width=True, height=600)
    with tab2:
        st.text("The annualized rate of settlement (in inches per year) between each survey date.  \nAll survey dates are included.")
        st.plotly_chart(fig_rate, use_container_width=True, height=600)
    with tab3:
        st.text("The floor elevation (in feet) of the station.  \nData is limited to the period where shim pack heights are known.")
        st.plotly_chart(fig_floorElev, use_container_width=True, height=600)
    with tab4:
        st.text("The grade beam elevation (in feet) of the station.  \nData is limited to the period where shim pack heights are known.")
        st.plotly_chart(fig_gradeBeamElev, use_container_width=True, height=600)
    with tab5:
        st.text("The differential elevation (in inches) for each column pair for each survey date and projected floor elevations.  \nData is limited to the period where shim pack heights are known and projected.  \nThe January 2022 Survey is not plotted or included in calculations due to errors.")
        st.plotly_chart(floorDiff, use_container_width=True, height=600)
    with tab6:
        st.text("The elevation (in feet) profile of each grade beam at the columns for each survey.")
        st.plotly_chart(gradeBeamProfile, use_container_width=True, height=600)
    with tab7:
        st.text("The maximum elevation difference (in inches) of the grade beam profiles during each survey.")
        st.plotly_chart(gradeBeamProfile_diff, use_container_width=True, height=600)

    ## 3D PLOTTING
    fig_3d_floor = plot_3D_floorElev_slider_animated_planes(elevationFloorStart, elevFloorInfo3D, plot3dAnnoDiff, floorElevPlot)
    fig_3d_gradeBeam = plot_3D_gradeBeamElev_slider_animated_planes(elevationGBStart, elevGBInfo3D , plot3dAnnoDiff, gradeBeamElevPlot)
    fig_3d_station = plot_3D_fullStation_slider_animated(elevationFloorStart, elevFloorInfo3D, elevGBInfo3D, plot3dAnnoDiff)

    st.subheader("3-Dimensional Animations of Settlement")
    # Differental Settlement 3D
    tab1, tab2, tab3 = st.tabs(["Floor Elevation [ft]", "Grade Beam Elevation [ft]", "Station Foundation Elevation[ft]"])
    with tab1:
        st.text("The observed floor elevations and the mean and fitted floor elevation planes in each pod. Least squares is used to fit the plane.  \nFloor elevations equal the survey lug elevation plus the lug to truss heigh.  \nData is limited to the period where shim pack heights are known.") #\nForecasted elevations use settlement trend rates from the number of years specified.
        st.plotly_chart(fig_3d_floor)
    with tab2:
        st.text("The observed floor elevations and the mean and fitted floor elevation planes based on the monitoring point elevations in each pod. Least squares is used to fit the plane. \nGrade beam elevation is equal to the survey lug elevation minus the grade beam to survey lug height (calculated using 2017 shim and lug to truss height data).  \nAll survey dates are included.")
        st.plotly_chart(fig_3d_gradeBeam) 
    with tab3:
        st.text("The observed grade beam and floor elevations of the station.  \nColumns are shown for clarity, opening between top of column and floor elevation includes variability in shim packs and distance between top of column and floor joists.  \nData is limited to the period where shim pack heights are known.")
        st.plotly_chart(fig_3d_station)

    ## Plane Error PLOTTING
    fig_floorElev_errorFit = plot_FloorElev_error_fit(error_fitFloor, color_dict, mapsPods)
    fig_gradeBeamElev_errorFit = plot_GradeBeamElev_error_fit(error_fitGradeBeam, color_dict, mapsPods)
    fig_floorElev_errorMean = plot_FloorElev_error_mean(error_meanFloor, color_dict, mapsPods)
    fig_gradeBeamElev_errorMean = plot_GradeBeamElev_error_mean(error_meanGradeBeam, color_dict, mapsPods)
    
    #Stats Plots
    fig_floorElev_errorSTD = plot_error_std_floor(error_stdFloor)
    fig_gradeBeamElev_errorSTD = plot_error_std_gradeBeam(error_stdGradeBeam)
    fig_fittedFloorSlope = plot_fitted_slope_floor(slopes_fitFloor)
    fig_fittedGBSlope = plot_fitted_slope_gradeBeam(slopes_fitGradeBeam)

    st.subheader("Anomaly Between Plane and Measured Elevation")
    # Differental Settlement 3D
    tab1, tab2, tab3, tab4, = st.tabs(["Floor Elevation Error - Least Squares Fit [in]", "Floor Elevation Error - Mean [in]", "Grade Beam Elevation Error - Least Squares Fit [in]", "Grade Beam Elevation Error - Mean [in]" ])
    with tab1:
        st.text("The anomaly between the least squares fitted floor elevation plane for each pod and the calculated floor elevations at each monitoring point.")
        st.plotly_chart(fig_floorElev_errorFit, use_container_width=True, height=600)
    with tab2:
        st.text("The anomaly between the mean floor elevation plane for each pod and the calculated floor elevations at each monitoring point.")
        st.plotly_chart(fig_floorElev_errorMean, use_container_width=True, height=600)
    with tab3:
        st.text("The anomaly between the least square fitted grade beam elevation plane for each pod and the calculated grade beam elevations at each monitoring point.")
        st.plotly_chart(fig_gradeBeamElev_errorFit, use_container_width=True, height=600)
    with tab4:
        st.text("The anomaly between the mean grade beam elevation plane for each pod and the calculated grade beam elevations at each monitoring point.")
        st.plotly_chart(fig_gradeBeamElev_errorMean, use_container_width=True, height=600)
    
    st.subheader("Plane Statistics")
    tab1, tab2, tab3, tab4 = st.tabs(["Fitted Floor Elevation Standard Deviation [in]", "Fitted Grade Beam Standard Deviation [in]", "Fitted Floor Elevation Slope [%]", "Fitted Grade Beam Slope [%]"])
    with tab1:
        st.text("The standard deviation of the anomaly between the fitted floor elevation planes and the measured column elevations for each survey.")
        st.plotly_chart(fig_floorElev_errorSTD, use_container_width=True, height=600)
    with tab2:
        st.text("The standard deviation of the anomaly between the fitted grade beam elevation planes and the measured column elevations for each survey.")
        st.plotly_chart(fig_gradeBeamElev_errorSTD, use_container_width=True, height=600)
    with tab3:
        st.text("The X, Y, and Max Slopes of the fitted floor elevation plane in both pods.")
        st.plotly_chart(fig_fittedFloorSlope, use_container_width=True, height=600)
    with tab4:
        st.text("The X, Y, and Max Slopes of the fitted grade beam elevation plane in both pods.")
        st.plotly_chart(fig_fittedGBSlope, use_container_width=True, height=600)

    st.subheader(" ")

