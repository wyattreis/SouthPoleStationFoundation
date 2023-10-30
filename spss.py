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
from scipy import interpolate
import plotly.express as px
import plotly.graph_objects as go
from utils import *

st.set_page_config(layout="wide")

st.title('South Pole Station Settlement Visualization and Analysis')
st.sidebar.title('Options')

# Import the South Pole Station excel survey and beam information fils
surveyfile = st.sidebar.file_uploader("South Pole Station Survey File", type = 'csv')
beamfile = st.sidebar.file_uploader("South Pole Labels File", type = 'csv')

# Set forecasting variables
nsurvey = st.sidebar.number_input('Number of Past Surveys Used for Forecast', value=10)
nyears = st.sidebar.number_input('Number of Years Forecasted', value=5)

if st.sidebar.button('Compute Settlement'):

    # Calculate settlement
    # survey_clean, survey_long = read_survey(surveyfile)
    beamInfo, beamLength = read_beamInfo(beamfile)
    st.write(beamInfo)
    # settlement, settlement_points, settlement_delta, settlement_delta_MP = calc_settlement(survey_long)
    # settlementProj = calc_forecast_settlement(settlement, nsurvey, nyears)
    # beamDiff, beamDiffplot, beamSlope, beamSlopeplot = calc_differental_settlement(beamLength, survey_clean, beamInfo)
    
    # # Plot settlement
    # beamDir, beamSymbol, beamDiffColor, beamSlopeColor, beamDiffAnno, beamSlopeAnno = plot_annotations(beamInfo, beamDiff, beamSlope)

    # fig = plot_cumulative_settlement(settlement, settlementProj)
    # st.plotly_chart(fig, use_container_width=True)