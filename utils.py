# -------------------------------------------------------------------------------
# Name          South Pole Station Settlement Visualization and Analysis
# Description:  Collection of utilities to visulaize the historic settlement at 
#               the South Pole Station as recorded by surveys at monitoring 
#               points. Utilities also include analysis to project future 
#               settlement using existing patterns.
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


# Set the location of the South Pole Station excel survey file
##"C:/Users/RDCRLWKR/Documents/Active Projects/South Pole Foundation/Technical/Data/SP Settlement Analysis_2023.01.15.xlsx"
surveyfile = st.sidebar.file_uploader("South Pole Survey File", type = 'xlsx')

# Set the loaction of the South Pole Station beam lengths and labels file
##"C:/Users/RDCRLWKR/Documents/Active Projects/South Pole Foundation/Technical/Data/SP_BeamArrowLabels.csv"
beamfile = st.sidebar.file_uploader("South Pole Labels File", type = 'csv')