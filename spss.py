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

st.set_page_config(layout="wide")

left_co, cent_co,last_co = st.columns([0.05, 0.9, 0.05])
with cent_co:

    htp = 'https://github.com/wyattreis/SouthPoleStationFoundation/blob/main/southpole_fromB_cropped.jpg?raw=true'
    st.image(htp, use_column_width=True, caption='U.S. South Pole Station. Credit: Marc Ankenbauer (2013)')

left_co, cent_co,last_co = st.columns([0.1, 0.8, 0.1])
with cent_co:
    st.title('South Pole Station Settlement Visualization and Analysis', anchor=False)

st.sidebar.title('Survey and Forecast Options:')

# Import the South Pole Station excel survey and beam information fils
surveyfile = st.sidebar.file_uploader("South Pole Station Survey File", type = 'csv')
trussfile = st.sidebar.file_uploader("South Pole Station Truss Height File", type = 'csv')

# Set forecasting variables
nsurvey = st.sidebar.number_input('Number of Past Surveys Used for Forecast', value=10)
nyears = st.sidebar.number_input('Number of Years Forecasted', value=5)

if st.sidebar.button('Compute Settlement'):

    # Calculate data for plotting 
    survey_clean, survey_long = read_survey(surveyfile)
    truss_clean = read_trussHeight(trussfile)
    beamInfo, beamLength, MPlocations = read_beamInfo()
    settlement, settlement_points, settlement_delta, settlement_delta_MP, settlement_rate = calc_settlement(survey_long)
    settlementProj = calc_forecast_settlement(settlement, nsurvey, nyears)
    beamDiff, beamDiffplot, beamSlope, beamSlopeplot, beamLength_long, beamLength_sort = calc_differental_settlement(beamLength, survey_clean, beamInfo)
    lugElevPlot, lugFloorPlot, floorElevPlot, floorDiff, floorDiffplot, floorSlope, floorSlopeplot = calc_plan_dataframe (survey_clean, truss_clean, MPlocations, beamLength_long, beamLength_sort, beamLength, beamInfo)
    beamDir, beamSymbol, beamDiffColor, beamSlopeColor, floorDir, floorSymbolplot, floorDiffColorplot, floorSlopeColorplot, beamDiffAnno, beamSlopeAnno, diffAnno, slopeAnno, color_dict, maps = plot_annotations(beamInfo, beamDiff, beamSlope, floorDiff, floorDiffplot, floorSlope, floorSlopeplot)
    settlementStart, beamInfo3D = calc_3d_dataframe(beamInfo, settlement_points, beamSlopeColor)
    
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

    # Create Streamlit Plot objects - Plan Figure
    tab1, tab2, tab3, tab4 = st.tabs(["Differental Floor Elevation [in]", "Differental Floor Slope [in/ft]", 
                                "Lug Elevation [ft]", "Lug to Truss Height [ft]"])
    with tab1:
        # Use the Streamlit theme.
        # This is the default. So you can also omit the theme argument.
        st.plotly_chart(fig_floorElev_plan, use_container_width=True, height=600)
    with tab2:
        # Use the native Plotly theme.
        st.plotly_chart(fig_floorSlope_plan, use_container_width=True, height=600)
    with tab3: 
        st.plotly_chart(fig_lugElev_plan, use_container_width=True, height=600)
    with tab4:
        st.plotly_chart(fig_lugTrussHeight_plan, use_container_width=True, height=600)

    # Cumulative settlement
    fig_cumulative = plot_cumulative_settlement(settlement, settlementProj, color_dict, maps)
    
    # Delta Settlement
    fig_delta = plot_delta_settlement(settlement_delta, color_dict, maps)

    # Settlement Rate
    fig_rate = plot_settlementRate(settlement_rate, color_dict, maps)
    
    # Create Streamlit Plot objects - Plan Figure
    tab1, tab2 = st.tabs(["Cumulative Settlement [ft]", "Annualized Settlement Rate [in/yr]"])
    with tab1:
        # Use the Streamlit theme.
        # This is the default. So you can also omit the theme argument.
        st.plotly_chart(fig_cumulative, use_container_width=True, height=600)
    with tab2:
        # Use the native Plotly theme.
        st.plotly_chart(fig_rate, use_container_width=True, height=600)

    # Differental Settlement 3D
    left_co, cent_co,last_co = st.columns([0.025, 0.95, 0.025])
    with cent_co:
        fig_3d_slider = plot_3D_settlement_slider_animated(settlementStart, beamInfo3D)
        st.plotly_chart(fig_3d_slider, width = 1100, height = 800)