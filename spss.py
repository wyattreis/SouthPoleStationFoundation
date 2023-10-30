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

st.set_page_config(layout="wide")

st.title('South Pole Station Settlement Visualization and Analysis')
st.sidebar.title('Options')

# Import the South Pole Station excel survey and beam information fils
surveyfile = st.sidebar.file_uploader("South Pole Station Survey File", type = 'xlsx')
beamfile = st.sidebar.file_uploader("South Pole Labels File", type = 'csv')

# Set forecasting variables
nsurvey = st.sidebar.number_input('Number of Past Surveys Used for Forecast', value=10)
nyears = st.sidebar.number_input('Number of Years Forecasted', value=5)

st.sidebar.button('Compute Settlement')
