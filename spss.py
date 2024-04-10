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
nsurvey = st.sidebar.number_input('Number of Past Surveys Used for Forecast', value=10)
nyears = st.sidebar.number_input('Number of Years Forecasted', value=5)

if st.sidebar.button('Compute Settlement'):

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
    elevationFloorStart, elevFloorInfo3D = calc_3d_floorElev(beamInfo, floorElevPlot, elevFloorProj, beamSlopeColor, beamSlopeProjColor)
    elevationGBStart, elevGBInfo3D = calc_3d_gradeBeamElev(beamInfo, gradeBeamElev, elevGradeBeamProj, beamSlopeColor, beamSlopeProjColor)
    
    ## PLAVIEW PLOTTING
    # Differental Settlement Planview
    fig_diff_plan = plot_DiffSettlement_plan(beamDiffplot, beamInfo, beamDiffColor, beamSymbol, beamDir, beamDiffAnno)
    # Differental Settlement Slope Planview
    fig_slope_plan = plot_SlopeSettlement_plan(beamSlopeplot, beamInfo, beamSlopeColor, beamSymbol, beamDir, beamSlopeAnno)
    # Differental Floor Elevation Planview 
    fig_floorElev_plan = plot_floorDiffElev_plan(floorDiffColorplot, beamInfo, floorDiffplot, floorSymbolplot, floorDir, floorElevPlot, diffAnno)
    # Differental Floor Slope Planview
    fig_floorSlope_plan = plot_floorSlopeElev_plan(floorSlopeColorplot, beamInfo, floorSlopeplot, floorSymbolplot, floorElevPlot, floorDir, slopeAnno)
    # Lug Elevation
    fig_lugElev_plan = plot_lugElev_plan(lugElevPlot, beamInfo)
    # Lug to Floor Height
    fig_lugTrussHeight_plan = plot_lugFloorHeight_plan(lugFloorPlot, beamInfo)

    # Create heading heading for the plan view plot that describes each tab of the plot
    st.subheader("Plan View Plots")

    # Create Streamlit Plot objects - Plan Figure
    tab1, tab2, tab3, tab4 = st.tabs(["Differental Floor Elevation [in]", "Floor Slope [in/ft]", 
                                "Lug Elevation [ft]", "Lug to Truss Height [ft]"])
    with tab1:
        st.text("The differential elevations (in inches) of the floor between each column. The floor elevation includes the lug elevations and the shim pack height.  \nData is limited to the period where shim pack heights are known.")
        st.plotly_chart(fig_floorElev_plan, use_container_width=True, height=600)
    with tab2:
        st.text("The slope (in inches per foot) of the station floor between each column using the differental floor elevations at each column and the known distances between each column.  \nData is limited to the period where shim pack heights are known.")
        st.plotly_chart(fig_floorSlope_plan, use_container_width=True, height=600)
    with tab3:
        st.text("The elevation (in feet) of the column lugs used to survey the station settlement.  \nAll survey dates are included.")
        st.plotly_chart(fig_lugElev_plan, use_container_width=True, height=600)
    with tab4:
        st.text("The height (in feet) between the lug survey points and the bottom of the floor trusses, this measurement includes the shimpack height.  \nData is limited to the period where shim pack heights are known.")
        st.plotly_chart(fig_lugTrussHeight_plan, use_container_width=True, height=600)

    ## TIMESERIES PLOTTING
    # Cumulative settlement
    fig_cumulative = plot_cumulative_settlement(settlement, settlementProj, color_dict, maps)
    # Settlement Rate
    fig_rate = plot_settlementRate(settlement_rate, color_dict, maps)
    
    st.subheader("Time Series Plots")
    # Create Streamlit Plot objects - Plan Figure
    tab1, tab2 = st.tabs(["Cumulative Settlement [ft]", "Annualized Settlement Rate [in/yr]"])
    with tab1:
        st.text("The cumulative settlement (in feet) of the station based on the survey lugs.  \nAll survey dates are included.")
        st.plotly_chart(fig_cumulative, use_container_width=True, height=600)
    with tab2:
        st.text("The rate of settlement (in inches per year) between each survey data annualized to account for variable periods between the surveys.  \nAll survey dates are included.")
        st.plotly_chart(fig_rate, use_container_width=True, height=600)

    ## 3D PLOTTING
    fig_3d_floor = plot_3D_floorElev_slider_animated(elevationFloorStart, elevFloorInfo3D, plot3dAnno)
    fig_3d_gradeBeam = plot_3D_gradeBeamElev_slider_animated(elevationGBStart, elevGBInfo3D , plot3dAnno)
    fig_3d_station = plot_3D_fullStation_slider_animated(elevationFloorStart, elevFloorInfo3D, elevGBInfo3D, plot3dAnno)

    st.subheader("3-Deminsional Animations of Settlement")
    # Differental Settlement 3D
    tab1, tab2, tab3 = st.tabs(["Floor Elevation [ft]", "Grade Beam Elevation [ft]", "Station Foundation Elevation[ft]"])
    with tab1:
        st.text("The observed and forecasted floor elevations.  \nForecasted elevations use settlement trend rates from the number of years specified.  \nFloor elevations equal the survey lug elevation plus the distance to the bottom of floor joist, including shim pack height.  \nData is limited to the period where shim pack heights are known.")
        st.plotly_chart(fig_3d_floor)
    with tab2:
        st.text("The observed and forecasted grade beam elevations. \nForecasted elevations use settlement trend rates from the number of years specified.  \nGrade beam elevation is equal to the survey lug elevation minus 11.31 feet (As-Builts Sheet A5.1; column height = 12.31', lugs are ~1' below top of column). \nAll survey dates are included.")
        st.plotly_chart(fig_3d_gradeBeam) 
    with tab3:
        st.text("The observed and forecasted grade beam and floor elevations of the station.  \nForecasted elevations use settlement trend rates from the number of years specified.  \nColumns are shown for clarity, opening between top of column and floor elevation includes variability in shim packs and distance between top of column and floor joists.  \nData is limited to the period where shim pack heights are known.")
        st.plotly_chart(fig_3d_station) 