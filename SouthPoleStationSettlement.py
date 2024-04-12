#!/usr/bin/env python
# coding: utf-8

# In[]:
import streamlit as st
import pandas as pd
import numpy as np
from scipy import interpolate
import plotly.express as px
import plotly.graph_objects as go

# In[]:
# Set the location of the South Pole Station excel survey file
surveyfile = "C:/Users/RDCRLWKR/Documents/Active Projects/South Pole Foundation/Technical/Data/SP Settlement Analysis_2023.01.15.xlsx"

# Set the loaction of the South Pole Station beam lengths and labels file
beamfile = "C:/Users/RDCRLWKR/Documents/Active Projects/South Pole Foundation/Technical/Data/SP_BeamArrowLabels.csv"

# In[]:
# Read in the data sheet from the survey excel file - limit to the data only
xls = pd.ExcelFile(surveyfile)
survey = pd.read_excel(xls, 'Data', nrows=36, skiprows=[0,2,3])

# Read in beam lengths and labeling locations
beamInfo = pd.read_csv(beamfile)
beamLength = beamInfo[['MP_W_S', 'MP_E_N', 'beamName', 'beamLength']].dropna()

# Clean up the imported file and convert to long format - change of index name is anticiptory
# rename second 2010/11/2 survey to 2010/11/3
survey_clean = survey.drop(columns=["DESCRIPTION", "Shims\nNote 13", "Unnamed: 52", "Delta"]).rename(columns={"MONITOR\nPOINT":"MONITOR_POINT", "2010-11-02 00:00:00.1":'2010-11-03 00:00:00'})
survey_clean = survey_clean.set_index('MONITOR_POINT').rename_axis('date', axis=1)
survey_clean.columns = pd.to_datetime(survey_clean.columns).astype(str)

# Move date file into dataframe and force dates into index column
survey_long = pd.DataFrame.transpose(survey_clean)


# In[3]:


# Identify the first non-NAN value for each support
survey_long['dummy']= 1
firstValue = survey_long.groupby('dummy').first()
firstValue = firstValue.to_numpy()[0]

# Calculate the cumulative settlement in feet for each column by survey data
settlement = survey_long.drop(columns=["dummy"]).apply(lambda row: firstValue - row, axis=1)
settlement.index = pd.to_datetime(settlement.index)

# Transpose the settlement file to index on the Monitoring Points
settlement_points = pd.DataFrame.transpose(settlement)

# Calculate the differential settlement in inches for each monitoring point - skip 2010/11/02 surveys, like in excel workbook
settlement_delta = settlement.drop(['2010-11-02', '2010-11-03'], axis = 0).diff().mul(12)

settlement_delta_MP = pd.DataFrame.transpose(settlement_delta)


# In[4]:


# Cumulative Settlement Forecasting
# Number of past surveys used to forecast 
nsurvey = 10

# Number of years of projection 
nyears = 5

settlementInterp = settlement.iloc[[(len(settlement.index)-(nsurvey)),(len(settlement.index)-1)]]
currentYear = settlementInterp.index.year[1]

projList = []
for year in range(nyears):
    projYear = (currentYear + year+1).astype(str)
    projYear = pd.to_datetime(projYear + '-01-01') 
    projList.append(projYear)

settlementExtrap = pd.DataFrame(columns=settlementInterp.columns, index = [projList]).reset_index().set_index('level_0')
settlementProj = pd.concat([settlementInterp,settlementExtrap])

settlementProj = settlementProj.interpolate(method="slinear", fill_value="extrapolate", limit_direction="both")


# In[ ]:


# Plot Cumulative Settlement
df = settlement #change based on dataframe to plot

# Identify the groupings based on the pod
maps = {'A1':['A1-1', 'A1-2', 'A1-3', 'A1-4'],
        'A2':['A2-1', 'A2-2', 'A2-3', 'A2-4', 'A2-5','A2-6'],
        'A3':['A3-1', 'A3-2', 'A3-3', 'A3-4'],
        'A4':['A4-1', 'A4-2', 'A4-3', 'A4-4'],
       'B1':['B1-1', 'B1-2', 'B1-3', 'B1-4'],
        'B2':['B2-1', 'B2-2', 'B2-3', 'B2-4', 'B2-5','B2-6'],
        'B3':['B3-1', 'B3-2', 'B3-3', 'B3-4'],
        'B4':['B4-1', 'B4-2', 'B4-3', 'B4-4'],}

# column: color
color_dict = {
    'A1-1': '#7fc97f', 'A1-2': '#beaed4', 'A1-3': '#fdc086', 'A1-4': '#ffff99',
    'A2-1': '#7fc97f', 'A2-2': '#beaed4', 'A2-3': '#fdc086', 'A2-4': '#ffff99', 'A2-5': '#386cb0','A2-6': '#f0027f',
    'A3-1': '#7fc97f', 'A3-2': '#beaed4', 'A3-3': '#fdc086', 'A3-4': '#ffff99',
    'A4-1': '#7fc97f', 'A4-2': '#beaed4', 'A4-3': '#fdc086', 'A4-4': '#ffff99',
    'B1-1': '#7fc97f', 'B1-2': '#beaed4', 'B1-3': '#fdc086', 'B1-4': '#ffff99',
    'B2-1': '#7fc97f', 'B2-2': '#beaed4', 'B2-3': '#fdc086', 'B2-4': '#ffff99', 'B2-5': '#386cb0','B2-6': '#f0027f',
    'B3-1': '#7fc97f', 'B3-2': '#beaed4', 'B3-3': '#fdc086', 'B3-4': '#ffff99',
    'B4-1': '#7fc97f', 'B4-2': '#beaed4', 'B4-3': '#fdc086', 'B4-4': '#ffff99'
}

color = settlement.columns.map(color_dict)

# plotly figure
figSettlement = go.Figure()

for column in df:
        figSettlement.add_trace(go.Scatter(
            x=df.index,
            y=df[column],
            name= column,
            mode = 'lines+markers',
            marker_color = color_dict[column]
        ))

for column in settlementProj:
        figSettlement.add_trace(go.Scatter(
            x=settlementProj.index,
            y=settlementProj[column],
            name= column + ' Projection',
            mode = 'lines+markers',
            marker_color = color_dict[column],
            line = dict(
                width = 1.5,
                dash = 'dash'),
            marker = dict(
                size=7.5,
                symbol='star'),
        ))
        
figSettlement.update_layout(xaxis_title="Survey Date",
                 yaxis_title="Cumulative Settlement [ft]")

# groups and trace visibilities
group = []
vis = []
visList = []
for m in maps.keys():
    for col in df.columns:
        if col in maps[m]:
            vis.append(True)
        else:
            vis.append(False)
    group.append(m)
    visList.append(vis)
    vis = []

# buttons for each group
buttons = []
for i, g in enumerate(group):
    button =  dict(label=g,
                   method = 'restyle',
                    args = ['visible',visList[i]])
    buttons.append(button)

# buttons
buttons = [{'label': 'All Points',
                 'method': 'restyle',
                 'args': ['visible', [True, True, True, True, True, True]]}] + buttons

               

# update layout with buttons                       
figSettlement.update_layout(
    updatemenus=[
        dict(
        type="dropdown",
        direction="down",
        buttons = buttons,
            pad={"r": 10, "t": 10},
            showactive=True,
            x=0.0,
            xanchor="left",
            y=1.01,
            yanchor="bottom")
    ],
)

#fig.write_html("C:/Users/RDCRLWKR/Documents/Active Projects/South Pole Foundation/Technical/Figures/settlement.html")
figSettlement.show()


# In[ ]:


# Plot Change in Settlement between each survey
df = settlement_delta #change based on dataframe to plot

# Identify the groupings based on the pod
maps = {'A1':['A1-1', 'A1-2', 'A1-3', 'A1-4'],
        'A2':['A2-1', 'A2-2', 'A2-3', 'A2-4', 'A2-5','A2-6'],
        'A3':['A3-1', 'A3-2', 'A3-3', 'A3-4'],
        'A4':['A4-1', 'A4-2', 'A4-3', 'A4-4'],
       'B1':['B1-1', 'B1-2', 'B1-3', 'B1-4'],
        'B2':['B2-1', 'B2-2', 'B2-3', 'B2-4', 'B2-5','B2-6'],
        'B3':['B3-1', 'B3-2', 'B3-3', 'B3-4'],
        'B4':['B4-1', 'B4-2', 'B4-3', 'B4-4'],}

# plotly figure
figSettlementDelta = go.Figure()

for column in df:
        figSettlementDelta.add_trace(go.Scatter(
            x=df.index,
            y=df[column],
            name= column,
            mode = 'lines+markers',
            marker_color = color_dict[column]
        ))

figSettlementDelta.update_layout(xaxis_title="Survey Date",
                 yaxis_title="Settlement Change [in]")

# groups and trace visibilities
group = []
vis = []
visList = []
for m in maps.keys():
    for col in df.columns:
        if col in maps[m]:
            vis.append(True)
        else:
            vis.append(False)
    group.append(m)
    visList.append(vis)
    vis = []

# buttons for each group
buttons = []
for i, g in enumerate(group):
    button =  dict(label=g,
                   method = 'restyle',
                    args = ['visible',visList[i]])
    buttons.append(button)

buttons = [{'label': 'All Points',
                 'method': 'restyle',
                 'args': ['visible', [True, True, True, True, True, True]]}] + buttons

                     

# update layout with buttons                       
figSettlementDelta.update_layout(
    updatemenus=[
        dict(
        type="dropdown",
        direction="down",
        buttons = buttons,
            pad={"r": 10, "t": 10},
            showactive=True,
            x=0.0,
            xanchor="left",
            y=1.01,
            yanchor="bottom")
    ],
)

#fig.write_html("C:/Users/RDCRLWKR/Documents/Active Projects/South Pole Foundation/Technical/Figures/settlement_delta.html")
figSettlementDelta.show()


# In[32]:


# Convert the beam length file to long format and make index the east or south Monitoring Point for each beam
beamLength_long = pd.melt(beamLength, id_vars=['beamName', 'beamLength']).rename(columns={'value':'MONITOR_POINT', 'variable':'beamEnd'})
beamLength_long.set_index('MONITOR_POINT', inplace = True)
beamLength_sort = beamLength_long.drop(columns=['beamEnd']).sort_values('beamName').set_index('beamName')
beamLength_sort = beamLength_sort[~beamLength_sort.index.duplicated(keep='first')]

# Merge the beam file and the settlement file
beamSettlement = beamLength_long.join(survey_clean)#.sort_values(by=['beamName', 'beamEnd']).rename_axis('date', axis=1)

# Group by beamName, difference, and convert to inches, keep only the differenced values
beamDiff = beamSettlement.set_index(['beamName']).sort_values(by=['beamName', 'beamEnd']).drop(columns=['beamEnd', 'beamLength']).groupby(['beamName']).diff().mul(12)
beamDiff = beamDiff[~beamDiff.index.duplicated(keep='last')]
beamDiff.columns = pd.to_datetime(beamDiff.columns).astype(str)
beamDiffplot = beamInfo[['beamName', 'beamX', 'beamY']].dropna().set_index(['beamName']).join(beamDiff)
beamDiff = beamDiffplot.drop(columns=['beamX', 'beamY'])

# Calculate the slope for each beam, transpose for ploting 
beamSlope = beamLength_sort.join(beamDiff)
beamSlope.iloc[:,1:] = beamSlope.iloc[:,1:].div(beamSlope.beamLength, axis=0)
beamSlopeplot = beamInfo[['beamName', 'beamX', 'beamY']].dropna().set_index(['beamName']).join(beamSlope)
beamSlope = beamSlopeplot.drop(columns=['beamX', 'beamY', 'beamLength'])


# In[33]:


beamSlope


# In[34]:


# Calculate the direction of arrow of each beam
beamDirLabels = beamInfo[['beamName','beamDir']].set_index(['beamName'])
beamDir = pd.DataFrame(np.where(beamDiff >= 0, 0, 180), index = beamDiff.index, columns = beamDiff.columns)
beamDir = beamDirLabels.join(beamDir).dropna()

# Add 90 degrees to the vertical columns, leave horizontal columns as is
cols = beamDir.columns[1:]
for col in cols:
    beamDir.loc[beamDir['beamDir'] != 'h', col] -= 90
    
beamDir = beamDir.drop(columns=['beamDir'])
beamDir.columns = pd.to_datetime(beamDir.columns).astype(str)

# Create dataframe for conditional text color for differental settlement values
conditions = [abs(beamDiff)>0, abs(beamDiff)==0]
choices = ['triangle-right', 'circle-open']

beamSymbol = pd.DataFrame(np.select(conditions, choices, default=np.nan), index = beamDiff.index, columns = beamDiff.columns).replace('nan','x')

# Create dataframe for conditional text color for differental settlement values
conditions = [abs(beamDiff)<1.5, (abs(beamDiff)>=1.5) & (abs(beamDiff)<2), abs(beamDiff)>=2]
choices = ['black', 'orange', 'red']

beamDiffColor = pd.DataFrame(np.select(conditions, choices, default=np.nan), index = beamDiff.index, columns = beamDiff.columns).replace('nan','blue')

# Create dataframe for conditional text color for differental settlement slope values
conditions = [abs(beamSlope)<(1/32), (abs(beamSlope)>=(1/32)) & (abs(beamSlope)<(1/16)), (abs(beamSlope)>=(1/16)) & (abs(beamSlope)<(1/8)), abs(beamDiff)>=(1/8)]
choices = ['black','gold', 'orange', 'red']

beamSlopeColor = pd.DataFrame(np.select(conditions, choices, default=np.nan), index = beamDiff.index, columns = beamDiff.columns).replace('nan','blue')


# In[35]:


# Create annotations for both plots
beamDiffAnno = list([
        dict(text="Differental Settlement less than 1.5 inches",
             x=1, xref="paper", xanchor="right",
             y=1.09, yref="paper", yanchor="bottom",
             align="right", 
             showarrow=False, 
             font = dict(
                 color = 'black')),
        dict(text="Differental Settlement between 1.5 and 2.0 inches",
             x=1, xref="paper", xanchor="right",
             y=1.05, yref="paper", yanchor="bottom",
             align="right", 
             showarrow=False, 
             font = dict(
                 color = 'orange')),
        dict(text="Differental Settlement greater than 2.0 inches",
             x=1, xref="paper", xanchor="right",
             y=1.01, yref="paper", yanchor="bottom",
             align="right", 
             showarrow=False, 
             font = dict(
                 color = 'red')),
       dict(text="Note: Arrows point in the direction of increased settlement.",
            x=1, xref="paper", xanchor="right",
            y=-0.1, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False, 
            font = dict(
                color = 'black')
           )
    ])

beamSlopeAnno = list([
       dict(text="Differental Slope less than 1/32 inch per foot",
            x=1, xref="paper", xanchor="right",
            y=1.13, yref="paper", yanchor="bottom",
            align="right",
            showarrow=False, 
            font = dict(
                color = 'black')
           ),
       dict(text="Differental Slope between 1/32 and 1/16 inch per foot",
            x=1, xref="paper", xanchor="right",
            y=1.09, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False,
            font = dict(
                color = 'gold')
           ),
       dict(text="Differental Slope between 1/16 and 1/8 inch per foot", 
            x=1, xref="paper", xanchor="right",
            y=1.05, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False, 
            font = dict(
                color = 'orange')
           ),
       dict(text="Differental Slope greater than 1/8 inch per foot",
            x=1, xref="paper", xanchor="right",
            y=1.01, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False, 
            font = dict(
                color = 'red')
           ),
       dict(text="Note: Arrows point in the direction of increased settlement.",
            x=1, xref="paper", xanchor="right",
            y=-0.1, yref="paper", yanchor="bottom",
            align="right", 
            showarrow=False, 
            font = dict(
                color = 'black')
           )
   ])


# In[36]:


df = beamDiffplot

#create a figure from the graph objects (not plotly express) library
figBeamDiff = go.Figure()

buttons = []
dates = []
i = 0

# Plot the beam locations as lines
for (startX, endX, startY, endY) in zip(beamInfo['startX'], beamInfo['endX'], beamInfo['startY'], beamInfo['endY']):
    figBeamDiff.add_trace(go.Scatter(
        x=[startX, endX],
        y=[startY, endY],
        mode='lines',
        line = dict(
            color = 'black',
            width = 1.5,
            dash = 'solid'),
        hoverinfo='skip',
        showlegend=False
    ))

# Plot the Marker Point (MP) labels in grey
figBeamDiff.add_trace(go.Scatter(
    x=beamInfo['labelX'],
    y=beamInfo['labelY'],
    text=beamInfo['MP_W_S'],
    mode = 'text',
    textfont = dict(
        size = 10,
        color = 'grey'),
    hoverinfo='skip',
    showlegend=False
))

# Create a list to store the visibility lists for each dataframe
all_args = []
vis = []
visList = []


#iterate through columns in dataframe (not including the year column)
for column in df.columns[2:]:
    # Beam Differental Settlement
    figBeamDiff.add_trace(go.Scatter(
        x=df['beamX'],
        y=df['beamY'],
        text=abs(df[column].values.round(2)),
        mode = 'text',
        #name = column, 
        textfont = dict(
            size = 10,
            color = beamDiffColor[column].values
            ),
        #hoverinfo='skip',
        showlegend=False, 
        #setting only the first dataframe to be visible as default
        visible = (column==df.columns[len(df.columns)-1])
    ))
        
        # Beam Differental Settlement Arrow - pointing in direction of low end 
    figBeamDiff.add_trace(go.Scatter(
        x=beamInfo['arrowX'],
        y=beamInfo['arrowY'],
        mode = 'markers',
        #name = column,
        marker=dict(
            color='red',
            size=10,
            symbol=beamSymbol[column].values,
            angle=beamDir[column].values),
        hoverinfo='skip',
        showlegend=False, 
        #setting only the first dataframe to be visible as default
        visible = (column==df.columns[len(df.columns)-1])
     ))
        

# groups and trace visibilities
vis = []
visList = []

for  i, col in enumerate(df.columns[2:]):
    vis = [True]*(len(df.index)+2) + ([False]*i*2 + [True]*2 + [False]*(len(df.columns)-2-(i+1))*2)
    visList.append(vis)
    vis = []


# buttons for each group
buttons = []
for idx, col in enumerate(df.columns[2:]):
    buttons.append(
        dict(
            label = col,
            method = "update",
            args=[{"visible": visList[idx]}])
    )

buttons = [{'label': 'Select Survey Date',
                 'method': 'restyle',
                 'args': ['visible', [False]*152]}] + buttons

# update layout with buttons                       
figBeamDiff.update_layout(
    updatemenus=[
        dict(
        type="dropdown",
        direction="down",
        buttons = buttons,
            pad={"r": 10, "t": 10},
            showactive=True,
            x=0.0,
            xanchor="left",
            y=1.01,
            yanchor="bottom")
    ],
    annotations = beamDiffAnno,
    #title = 'Differental Settlement [in] between Monitoring Points'
)

# Set axes ranges
figBeamDiff.update_xaxes(range=[-25, 415])
figBeamDiff.update_yaxes(range=[-15, 140])

#figBeamDiffPlot.write_html("C:/Users/RDCRLWKR/Documents/Active Projects/South Pole Foundation/Technical/Figures/diffSettlementPlan.html")
figBeamDiff.show()


# In[37]:


df = beamSlopeplot

#create a figure from the graph objects (not plotly express) library
figBeamSlope = go.Figure()

buttons = []
dates = []
i = 0

# Plot the beam locations as lines
for (startX, endX, startY, endY) in zip(beamInfo['startX'], beamInfo['endX'], beamInfo['startY'], beamInfo['endY']):
    figBeamSlope.add_trace(go.Scatter(
        x=[startX, endX],
        y=[startY, endY],
        mode='lines',
        line = dict(
            color = 'black',
            width = 1.5,
            dash = 'solid'),
        hoverinfo='skip',
        showlegend=False
    ))

# Plot the Marker Point (MP) labels in grey
figBeamSlope.add_trace(go.Scatter(
    x=beamInfo['labelX'],
    y=beamInfo['labelY'],
    text=beamInfo['MP_W_S'],
    mode = 'text',
    textfont = dict(
        size = 10,
        color = 'grey'),
    hoverinfo='skip',
    showlegend=False
))

# Create a list to store the visibility lists for each dataframe
all_args = []
vis = []
visList = []


#iterate through columns in dataframe (not including the year column)
for column in df.columns[3:]:
    # Beam Differental Settlement
    figBeamSlope.add_trace(go.Scatter(
        x=df['beamX'],
        y=df['beamY'],
        text=abs(df[column].values.round(2)),
        mode = 'text',
        #name = column, 
        textfont = dict(
            size = 12,
            color = beamSlopeColor[column].values),
        hoverinfo='skip',
        showlegend=False, 
        #setting only the first dataframe to be visible as default
        visible = (column==df.columns[len(df.columns)-1])
    ))
        
        # Beam Differental Settlement Arrow - pointing in direction of low end 
    figBeamSlope.add_trace(go.Scatter(
        x=beamInfo['arrowX'],
        y=beamInfo['arrowY'],
        mode = 'markers',
        #name = column,
        marker=dict(
            color='red',
            size=10,
            symbol=beamSymbol[column].values,
            angle=beamDir[column].values),
        hoverinfo='skip',
        showlegend=False, 
        #setting only the first dataframe to be visible as default
        visible = (column==df.columns[len(df.columns)-1])
     ))
        

# groups and trace visibilities
vis = []
visList = []

for  i, col in enumerate(df.columns[3:]):
    vis = [True]*(len(df.index)+2) + ([False]*i*2 + [True]*2 + [False]*(len(df.columns)-(i+1))*2)
    visList.append(vis)
    vis = []


# buttons for each group
buttons = []
for idx, col in enumerate(df.columns[3:]):
    buttons.append(
        dict(
            label = col,
            method = "update",
            args=[{"visible": visList[idx]}])
    )

buttons = [{'label': 'Select Survey Date',
                 'method': 'restyle',
                 'args': ['visible', [False]*152]}] + buttons

# update layout with buttons                       
figBeamSlope.update_layout(
    updatemenus=[
        dict(
        type="dropdown",
        direction="down",
        buttons = buttons,
            pad={"r": 10, "t": 10},
            showactive=True,
            x=0.0,
            xanchor="left",
            y=1.01,
            yanchor="bottom")
    ],
    annotations = beamSlopeAnno,
    #title = 'Differental Slope [in/ft]'
)

# Set axes ranges
figBeamSlope.update_xaxes(range=[-25, 415])
figBeamSlope.update_yaxes(range=[-15, 140])

figBeamSlope.show()


# In[ ]:


# Create dataframe for 3D plotting
beamStart = beamInfo[['MP_W_S', 'beamName']].set_index('MP_W_S')
settlementStart = beamStart.join(settlement_points).set_index('beamName')
settlementStart.columns = pd.to_datetime(settlementStart.columns).astype(str)

beamEnd = beamInfo[['MP_E_N', 'beamName']].set_index('MP_E_N')
settlementEnd = beamEnd.join(settlement_points).set_index('beamName')
settlementEnd.columns = pd.to_datetime(settlementEnd.columns).astype(str)

settlement3D = settlementStart.join(settlementEnd, lsuffix='_start', rsuffix='_end')
settlement3D = settlement3D[settlement3D.index.notnull()]

beamInfo3D = beamInfo.loc[:, ['beamName','MP_W_S','startX', 'startY', 'endX','endY','labelX', 'labelY']].set_index('beamName')
beamInfo3D = beamInfo3D.join(settlement3D)
beamInfo3D = beamInfo3D[beamInfo3D.index.notnull()]

# In[ ]:


# Create 3D plot of South Pole Station settlement
fig3DSettlement = go.Figure()

for col in settlementStart.columns:
    # Plot the beam locations as lines
    for (startX, endX, startY, endY, startZ, endZ) in zip(beamInfo['startX'], beamInfo['endX'], 
                                                          beamInfo['startY'], beamInfo['endY'], 
                                                          settlement3D['{0}_start'.format(col)], 
                                                          settlement3D['{0}_end'.format(col)]):
        fig3DSettlement.add_trace(go.Scatter3d(
            x=[startX, endX],
            y=[startY, endY],
            z = [startZ, endZ],
            text = beamInfo['MP_W_S'],
            #name="",
            mode='lines',
            line = dict(
                color = 'black',
                width = 1.5,
                dash = 'solid'),
            #hoverinfo='skip',
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (col==beamDiff.columns[len(beamDiff.columns)-1])))
    
    # Plot the Marker Point (MP) labels in grey
        fig3DSettlement.add_trace(go.Scatter3d(
            x=beamInfo['labelX'],
            y=beamInfo['labelY'],
            z=settlement3D['{0}_start'.format(col)],
            text=beamInfo['MP_W_S'],
            mode = 'text',
            textfont = dict(
                size = 10,
                color = 'grey'),
            hoverinfo='skip',
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (col==beamDiff.columns[len(beamDiff.columns)-1])))
        
fig3DSettlement.update_traces(
    hovertemplate="<br>".join([
        "MP: %{text}",
        "Settlement [in]: %{z}",
    ])
)
    
fig3DSettlement.update_scenes(xaxis_autorange="reversed", 
                  yaxis_autorange="reversed",
                  zaxis_autorange="reversed")  

camera = dict(
    up=dict(x=0, y=0, z=1),
    center=dict(x=0, y=0, z=0),
    eye=dict(x=1.5, y=1.5, z=1.5)
)

fig3DSettlement.update_layout(
    autosize=False,
    width=800, 
    height=450,
    margin=dict(l=0, r=0, b=0, t=0),
    scene_camera=camera,
    scene=dict(
        xaxis_title='',
        yaxis_title='',
        zaxis_title='Cumulative Settlement [ft]',
    )
)

# groups and trace visibilities
vis = []
visList = []

for  i, col in enumerate(beamDiff.columns):
    n = len(settlement3D.index)*2
    vis = ([False]*i*n + [True]*n + [False]*(len(beamDiff.columns)-(i+1))*n)
    visList.append(vis)
    vis = []


# buttons for each group
buttons = []
for idx, col in enumerate(beamDiff.columns):
    buttons.append(
        dict(
            label = col,
            method = "update",
            args=[{"visible": visList[idx]}])
    )

buttons = [{'label': 'Select Survey Date',
                 'method': 'restyle',
                 'args': ['visible', [False]*len(beamDiff.columns)*len(settlement3D.index)]}] + buttons

# update layout with buttons                       
fig3DSettlement.update_layout(
    updatemenus=[
        dict(
        type="dropdown",
        direction="down",
        buttons = buttons)
    ],
)

fig3DSettlement.show()


# In[ ]:
# Create animation of the 3d plot 

fig = go.Figure()

for col in settlementStart.columns:
    # Plot the beam locations as lines
    for (startX, endX, startY, endY, startZ, endZ) in zip(beamInfo3D['startX'], beamInfo3D['endX'], 
                                                        beamInfo3D['startY'], beamInfo3D['endY'], 
                                                        beamInfo3D['{0}_start'.format(col)], 
                                                        beamInfo3D['{0}_end'.format(col)]):
        fig.add_trace(go.Scatter3d(
            x=[startX, endX],
            y=[startY, endY],
            z = [startZ, endZ],
            text = beamInfo3D['MP_W_S'],
            #name="",
            mode='lines',
            line = dict(
                color = 'black',
                width = 1.5,
                dash = 'solid'),
            #hoverinfo='skip',
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (col==settlementStart.columns[len(settlementStart.columns)-1])))
    
    # Plot the Marker Point (MP) labels in grey
        fig.add_trace(go.Scatter3d(
            x=beamInfo3D['labelX'],
            y=beamInfo3D['labelY'],
            z=beamInfo3D['{0}_start'.format(col)],
            text=beamInfo3D['MP_W_S'],
            mode = 'text',
            textfont = dict(
                size = 10,
                color = 'grey'),
            hoverinfo='skip',
            showlegend=False, 
            #setting only the first dataframe to be visible as default
            visible = (col==settlementStart.columns[len(settlementStart.columns)-1])))
        
frames = []
for i, col in enumerate(settlementStart.columns):
    frames.append(go.Frame(data=[go.Scatter3d(z = [startZ, endZ]),
                                go.Scatter3d(z = beamInfo3D['{0}_start'.format(col)])],
                                name=f"fr{i}"))

fig.update(frames=frames)
              
fig.update_traces(
    hovertemplate="<br>".join([
        "MP: %{text}",
        "Settlement [in]: %{z}",
    ])
)
    
fig.update_scenes(xaxis_autorange="reversed", 
                yaxis_autorange="reversed",
                zaxis_autorange="reversed")  

camera = dict(
    up=dict(x=0, y=0, z=1),
    center=dict(x=0, y=0, z=0),
    eye=dict(x=1.5, y=1.5, z=1.5)
)

fig.update_layout(
    autosize=False,
    width=800, 
    height=450,
    margin=dict(l=0, r=0, b=0, t=0),
    scene_camera=camera,
    scene=dict(
        xaxis_title='',
        yaxis_title='',
        zaxis_title='Cumulative Settlement [ft]',
    ),
)

# groups and trace visibilities
vis = []
visList = []

for  i, col in enumerate(settlementStart.columns):
    n = len(beamInfo3D.index)*2
    vis = ([False]*i*n + [True]*n + [False]*(len(settlementStart.columns)-(i+1))*n)
    visList.append(vis)
    vis = []


# buttons for each group
steps = []
for idx, col in enumerate(settlementStart.columns):
    steps.append(
        dict(
            label = col, #.split('-')[0],
            method = "update",
            args=[{"visible": visList[idx]}])
    )

sliders = [dict(
    active=len(settlementStart.columns)-1,
    currentvalue={"prefix": "Survey Date: "},
    pad={"t": 20, "b":10},
    len = 0.85,
    x = 0.095,
    steps=steps
)]

def frame_args(duration):
    return {
            "frame": {"duration": duration},
            "mode": "immediate",
            "fromcurrent": True,
            "transition": {"duration": duration, "easing": "linear"},
        }

fig.update_layout(
    # updatemenus = [
    #         {
    #             "buttons": [
    #                 {
    #                     "args": [None, frame_args(50)],
    #                     "label": "&#9654;", # play symbol
    #                     "method": "animate",
    #                 },
    #                 {
    #                     "args": [[None], frame_args(0)],
    #                     "label": "&#9724;", # pause symbol
    #                     "method": "animate",
    #                 },
    #             ],
    #             "direction": "left",
    #             "pad": {"r": 10, "t": 20},
    #             "type": "buttons",
    #             "x": 0.1,
    #             "y": -0.05,
    #         }
    # ],
    sliders=sliders,
    width = 600,
    height = 500
)

fig.show()


# %%
fig=go.Figure().set_subplots(2,1, vertical_spacing=0.05,
                             specs=[[{"type": "polar"}], [{"type":"bar"}]])

r=[3.5, 1.5, 2.5, 4.5, 4.5, 4, 3]
theta=[65, 15, 210, 110, 312.5, 180, 270]
width=[20,15,10,20,15,30,15]
x= np.arange(1, 8)
bh = [4, 6, 3, 7, 8, 5, 9]


fig.add_trace(go.Barpolar(r=r[:1], theta=theta[:1], width=width[:1], 
                          marker_color="#ff8c00",
                          marker_line_color="black",
                          marker_line_width=1),1, 1)
fig.add_trace(go.Bar(x=x[:1], y=bh[:1], marker_color="green", width=0.95), 2,1);

fig.update_layout(width=600, height=500, xaxis_range=[0.5, 7.5], yaxis_range=[0, max(bh)+0.5]);

frames=[go.Frame(data=[go.Barpolar(r=r[:k+1], theta=theta[:k+1], width=width[:k+1]),
                       go.Bar(x=x[:k+1], y=bh[:k+1])],
                 name=f"fr{k}",
                 traces=[0,1]) for k in range(len(r))]  #r, theta, width, x, bh must have the same len=number of frames

fig.update(frames=frames)

def frame_args(duration):
    return {
            "frame": {"duration": duration},
            "mode": "immediate",
            "fromcurrent": True,
            "transition": {"duration": duration, "easing": "linear"},
        }

fr_duration=50  # customize this frame duration according to your data!!!!!
sliders = [
            {
                "pad": {"b": 10, "t": 50},
                "len": 0.9,
                "x": 0.1,
                "y": 0,
                "steps": [
                    {
                        "args": [[f.name], frame_args(fr_duration)],
                        "label": f"fr{k+1}",
                        "method": "animate",
                    }
                    for k, f in enumerate(fig.frames)
                ],
            }
        ]


fig.update_layout(sliders=sliders,
                  updatemenus = [
                        {
                        "buttons": [
                            {
                             "args": [None, frame_args(fr_duration)],
                             "label": "&#9654;", # play symbol
                             "method": "animate",
                            },
                            {
                             "args": [[None], frame_args(fr_duration)],
                             "label": "&#9724;", # pause symbol
                             "method": "animate",
                            }],
                        "direction": "left",
                        "pad": {"r": 10, "t": 70},
                        "type": "buttons",
                        "x": 0.1,
                        "y": 0,
                        }])

# %%
A = np.random.randn(30).reshape((15, 2))
centroids = np.random.randint(10, size=10).reshape((5, 2))
clusters = [1, 2, 3, 4, 5]
colors = ['red', 'green', 'blue', 'yellow', 'magenta']

fig = go.Figure(
    data=[go.Scatter(x=A[:3][:,0],
                     y=A[:3][:,1],
                     mode='markers',
                     name='cluster 1',
                     marker_color=colors[0]),
          go.Scatter(x=[centroids[0][0]],
                     y=[centroids[0][1]],
                     mode='markers',
                     name='centroid of cluster 1',
                     marker_color=colors[0],
                     marker_symbol='x')
         ],
    layout=go.Layout(
        xaxis=dict(range=[-10, 10], autorange=False),
        yaxis=dict(range=[-10, 10], autorange=False),
        title="Start Title",
        updatemenus=[dict(
            type="buttons",
            buttons=[dict(label="Play",
                          method="animate",
                          args=[None]),
                     dict(label="Pause",
                          method="animate",
                          args=[None,
                               {"frame": {"duration": 0, "redraw": False},
                                "mode": "immediate",
                                "transition": {"duration": 0}}],
                         )])]
    ),
    frames=[
    go.Frame(
    data=[go.Scatter(x=A[:3][:,0],
                     y=A[:3][:,1],
                     mode='markers',
                     name='cluster 1',
                     marker_color=colors[0]),
          go.Scatter(x=[centroids[0][0]],
                     y=[centroids[0][1]],
                     mode='markers',
                     name='centroid of cluster 1',
                     marker_color=colors[0],
                     marker_symbol='x')
         ]),
    go.Frame(
        data=[
            go.Scatter(x=A[:3][:,0],
                       y=A[:3][:,1],
                       mode='markers',
                       name='cluster 2',
                       marker_color=colors[1]),
            go.Scatter(x=[centroids[1][0]],
                       y=[centroids[1][1]],
                       mode='markers',
                       name='centroid of cluster 2',
                       marker_color=colors[1],
                       marker_symbol='x')
        ]),
    go.Frame(
        data=[
            go.Scatter(x=A[3:5][:,0],
                       y=A[3:5][:,1],
                       mode='markers',
                       name='cluster 3',
                       marker_color=colors[2]),
            go.Scatter(x=[centroids[2][0]],
                       y=[centroids[2][1]],
                       mode='markers',
                       name='centroid of cluster 3',
                       marker_color=colors[2],
                       marker_symbol='x')
        ]),
    go.Frame(
        data=[
            go.Scatter(x=A[5:8][:,0],
                       y=A[5:8][:,1],
                       mode='markers',
                       name='cluster 4',
                       marker_color=colors[3]),
        go.Scatter(x=[centroids[3][0]],
                   y=[centroids[3][1]],
                   mode='markers',
                   name='centroid of cluster 4',
                   marker_color=colors[3],
                   marker_symbol='x')]),
    go.Frame(
        data=[
            go.Scatter(x=A[8:][:,0],
                       y=A[8:][:,1],
                       mode='markers',
                       name='cluster 5',
                       marker_color=colors[4]),
            go.Scatter(x=[centroids[4][0]],
                       y=[centroids[4][1]],
                       mode='markers',
                       name='centroid of cluster 5',
                       marker_color=colors[4],
                       marker_symbol='x')
        ]),
    ])
            
fig.show()

# In[]

import plotly.graph_objects as go
import numpy as np
#from plotly.offline import iplot
def rndata():
    return np.random.randint(1,10,10)

n_frames=10
my_colors = ["RoyalBlue", "#09ffff", "#19d3f3", "#e763fa", "#ab63fa", 
             "#636efa", "#00cc96", "#EF553B", "#119DFF", "#0D76BF" ]    

my_symbols= ['circle', 'circle-open', 'cross', 'diamond',
            'diamond-open', 'square', 'square-open', 'x', 'circle', 'diamond']

fig = go.Figure(go.Scatter3d(x=rndata(),y=rndata(),z=rndata(), name='Nodes1',  mode="lines",
                             line_color="RoyalBlue", line_width=2
                             ))
fig.add_scatter3d(x=rndata(),y=rndata(),z=rndata(), 
                  mode="markers", marker_symbol=["circle"]*10, 
                  name='Nodes2', marker_size=6)

#Store Names and their corresponding order of the 
nameDataindexdict={}
for dt in fig.data:
    nameDataindexdict[dt['name']]=fig.data.index(dt)

frames = []

for k in range(n_frames):
    frames.append(go.Frame(data=[go.Scatter3d(z=rndata(), line_color=my_colors[k]),
                                 go.Scatter3d(marker_symbol=[my_symbols[k]]*10)],
                            #traces=[0,1], #This means that the above trace updates (within go.Frame definition)  #are performed for fig.data[0], fig.data[1]
                            traces=[nameDataindexdict['Nodes1'],nameDataindexdict['Nodes2']], #This means that the above trace updates are for traces with name ...          
                            name=f"fr{k}"))      
    

fig.update(frames=frames)
updatemenus = [dict(
        buttons = [
            dict(
                args = [None, {"frame": {"duration": 50, "redraw": True},
                                "fromcurrent": True}],
                label = "Play",
                method = "animate"
                ),
            dict(
                 args = [[None], {"frame": {"duration": 0, "redraw": False},
                                  "mode": "immediate",
                                  "transition": {"duration": 0}}],
                label = "Pause",
                method = "animate"
                )
        ],
        direction = "left",
        pad = {"r": 10, "t": 87},
        showactive = False,
        type = "buttons",
        x = 0.1,
        xanchor = "right",
        y = 0,
        yanchor = "top"
    )]  

sliders = [dict(steps = [dict(method= 'animate',
                              args= [[f'frame{k}'],                           
                              dict(mode= 'immediate',
                                   frame= dict(duration=400, redraw=True),
                                   transition=dict(duration= 0))
                                 ],
                              label=f'{k+1}'
                             ) for k in range(n_frames)], 
                active=0,
                transition= dict(duration= 0 ),
                x=0, # slider starting position  
                y=0, 
                currentvalue=dict(font=dict(size=12), 
                                  prefix='frame: ', 
                                  visible=True, 
                                  xanchor= 'center'
                                 ),  
                len=1.0) #slider length
           ]
fig.update_layout(width=1000, height=600,  
                  
                  updatemenus=updatemenus,
                  sliders=sliders)
fig.show()