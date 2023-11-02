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

    st.title('South Pole Station Settlement Visualization and Analysis', anchor=False)

st.sidebar.title('Survey and Forecast Options:')

# Import the South Pole Station excel survey and beam information fils
surveyfile = st.sidebar.file_uploader("South Pole Station Survey File", type = 'csv')

# Set forecasting variables
nsurvey = st.sidebar.number_input('Number of Past Surveys Used for Forecast', value=10)
nyears = st.sidebar.number_input('Number of Years Forecasted', value=5)

if st.sidebar.button('Compute Settlement'):

    # Calculate settlement
    survey_clean, survey_long = read_survey(surveyfile)
    beamInfo, beamLength = read_beamInfo()
    settlement, settlement_points, settlement_delta, settlement_delta_MP = calc_settlement(survey_long)
    settlementProj = calc_forecast_settlement(settlement, nsurvey, nyears)
    beamDiff, beamDiffplot, beamSlope, beamSlopeplot = calc_differental_settlement(beamLength, survey_clean, beamInfo)
    settlementStart, beamInfo3D = calc_3d_dataframe(beamInfo, settlement_points)
    
    # Plots 
    beamDir, beamSymbol, beamDiffColor, beamSlopeColor, beamDiffAnno, beamSlopeAnno, color_dict, maps = plot_annotations(beamInfo, beamDiff, beamSlope)

    # Differental Settlement Planview
    fig_diff_plan = plot_DiffSettlement_plan(beamDiffplot, beamInfo, beamDiffColor, beamSymbol, beamDir, beamDiffAnno)
    
    # Differental Settlement Slope Planview
    fig_slope_plan = plot_SlopeSttlement_plan(beamSlopeplot, beamInfo, beamSlopeColor, beamSymbol, beamDir, beamSlopeAnno)
    
    # Create Streamlit Plot objects - Plan Figure
    tab1, tab2 = st.tabs(["Differental Settlement [in]", "Differental Slope [in/ft]"])
    with tab1:
        # Use the Streamlit theme.
        # This is the default. So you can also omit the theme argument.
        st.plotly_chart(fig_diff_plan, use_container_width=True, height=600)
    with tab2:
        # Use the native Plotly theme.
        st.plotly_chart(fig_slope_plan, use_container_width=True, height=600)

    # Cumulative settlement
    fig_cumulative = plot_cumulative_settlement(settlement, settlementProj, color_dict, maps)
    
    # Delta Settlement
    fig_delta = plot_delta_settlement(settlement_delta, color_dict, maps)
    
    # Create Streamlit Plot objects - Plan Figure
    tab1, tab2 = st.tabs(["Cumulative Settlement [ft]", "Change in Settlement [in]"])
    with tab1:
        # Use the Streamlit theme.
        # This is the default. So you can also omit the theme argument.
        st.plotly_chart(fig_cumulative, use_container_width=True, height=600)
    with tab2:
        # Use the native Plotly theme.
        st.plotly_chart(fig_delta, use_container_width=True, height=600)

    # Differental Settlement 3D
    left_co, cent_co,last_co = st.columns([0.05, 0.9, 0.05])
    with cent_co:
        fig_3d_slider = plot_3D_settlement_slider(settlementStart, beamInfo3D)
        st.plotly_chart(fig_3d_slider, width = 900, height = 700)

    

    
