#------- Beam Pin elevation plan view -------
df = beamSlopeplot

#create a figure from the graph objects (not plotly express) library
fig = go.Figure()

buttons = []
dates = []
i = 0

# Plot the beam locations as lines
for (startX, endX, startY, endY) in zip(beamInfo['startX'], beamInfo['endX'], beamInfo['startY'], beamInfo['endY']):
    fig.add_trace(go.Scatter(
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
fig.add_trace(go.Scatter(
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
    fig.add_trace(go.Scatter(
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
    fig.add_trace(go.Scatter(
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
    vis = []
    vis = [True]*(len(df.index)+2) + ([False]*i*2 + [True]*2 + [False]*(len(df.columns)-(i+1))*2)
    visList.append(vis)


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
            'args': ['visible', [False]]}] + buttons

# update layout with buttons                       
fig.update_layout(
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
fig.update_xaxes(range=[-25, 415])
fig.update_yaxes(range=[-15, 140])

fig.show()

# Create animation of the 3d plot 
def plot_3D_settlement_animation(settlementStart, beamInfo3D):
    fig = go.Figure()

    for col in settlementStart.columns:
        # Plot the beam locations as lines
        for (startX, endX, startY, endY, startZ, endZ, startColor, endColor) in zip(beamInfo3D['startX'], beamInfo3D['endX'], 
                                                                                    beamInfo3D['startY'], beamInfo3D['endY'], 
                                                                                    beamInfo3D['{0}_start'.format(col)], 
                                                                                    beamInfo3D['{0}_end'.format(col)],
                                                                                    beamInfo3D[col],beamInfo3D[col]):
            fig.add_trace(go.Scatter3d(
                x=[startX, endX],
                y=[startY, endY],
                z = [startZ, endZ],
                text = beamInfo3D['MP_W_S'],
                line_color= [startColor, endColor],
                name="",
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
        )
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
        updatemenus = [
                {
                    "buttons": [
                        {
                            "args": [None, frame_args(50)],
                            "label": "&#9654;", # play symbol
                            "method": "animate",
                        },
                        {
                            "args": [[None], frame_args(0)],
                            "label": "&#9724;", # pause symbol
                            "method": "animate",
                        },
                    ],
                    "direction": "left",
                    "pad": {"r": 10, "t": 20},
                    "type": "buttons",
                    "x": 0.1,
                    "y": 0,
                }
        ],
        sliders=sliders,
        width = 1100,
        height = 800
    )
    return fig

# 3D Plot - settlement 
def plot_3D_settlement(settlementStart, beamInfo3D):
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
    buttons = []
    for idx, col in enumerate(settlementStart.columns):
        buttons.append(
            dict(
                label = col,
                method = "update",
                args=[{"visible": visList[idx]}])
        )

    buttons = [{'label': 'Select Survey Date',
                    'method': 'restyle',
                    'args': ['visible', [False]*len(settlementStart.columns)*len(beamInfo3D.index)]}] + buttons

    # update layout with buttons                       
    fig.update_layout(
        updatemenus=[
            dict(
            type="dropdown",
            direction="down",
            buttons = buttons)
        ],
        width = 700,
        height = 700

    )
    return fig