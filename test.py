import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Create a plotly figure
df_in = floorElevPlot

fig = go.Figure()
pods = ['A', 'B']
for pod in pods:
    df = df_in[[pod in s for s in df_in.index]]

    for col in df.columns[2:]:
        # Extract coordinates
        xs = df['mpX']
        ys = df['mpY']
        zs = df[col]

        # Calculate mean of z values
        Z_mean = zs.mean()

        # Fit plane 
        tmp_A = []
        tmp_b = []
        for i in range(len(xs)):
            tmp_A.append([xs[i], ys[i], 1])
            tmp_b.append(zs[i])
        b = np.matrix(tmp_b).T
        A = np.matrix(tmp_A)
        fit = (A.T * A).I * A.T * b

        # Define ranges for x and y
        xlim = [xs.min(), xs.max()]
        ylim = [ys.min(), ys.max()]

        # Create meshgrid for the plane surface - mean and fitted
        X, Y = np.meshgrid(np.arange(xlim[0], xlim[1]),
                        np.arange(ylim[0], ylim[1]))
        Z_plane_mean = np.ones_like(X) * Z_mean

        Z_plane_fit = np.zeros(X.shape)

        for r in range(X.shape[0]):
            for c in range(X.shape[1]):
                Z_plane_fit[r,c] = fit[0] * X[r,c] + fit[1] * Y[r,c] + fit[2]

        # Add surface trace for the plane - mean
        fig.add_trace(go.Surface(x=X, y=Y, z=Z_plane_mean,
                                colorscale='Viridis', showscale=False, showlegend= True,
                                name=f'Mean plane for {pod} {col}'))      
        
        # Add surface trace for the plane - fit
        fig.add_trace(go.Surface(x=X, y=Y, z=Z_plane_fit,
                                colorscale='Viridis', showscale=False, showlegend= True,
                                name=f'Fit plane for {pod} {col}'))

        # Add scatter trace for the points
        fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs,
                                mode='markers', marker=dict(size=5),
                                name=f'Points for {pod} {col}'))
    
fig.show()

def plot_3D_floorElev_slider_animated(elevationFloorStart, elevFloorInfo3D, plot3dAnno):
    
    # Calculate the maximum number of traces required for any frame
    max_traces_per_frame = len(elevFloorInfo3D['startX']) + 1  # +1 for the label trace

    # Initialize the figure with the maximum number of empty traces
    fig = go.Figure(data=[go.Scatter3d(x=[], y=[], z=[], mode='lines', showlegend=False) for _ in range(max_traces_per_frame)])

    # Creating frames
    frames = []
    for col in elevationFloorStart.columns:
        frame_traces = []  # List to hold all traces for this frame

        # Create a separate trace for each line segment
        for (startX, endX, startY, endY, startZ, endZ, startColor, endColor) in zip(elevFloorInfo3D['startX'], elevFloorInfo3D['endX'], 
                                                                                    elevFloorInfo3D['startY'], elevFloorInfo3D['endY'], 
                                                                                    elevFloorInfo3D['{0}_start'.format(col)], 
                                                                                    elevFloorInfo3D['{0}_end'.format(col)],
                                                                                    elevFloorInfo3D[col],elevFloorInfo3D[col]):

            line_trace = go.Scatter3d(
                x=[startX, endX],
                y=[startY, endY],
                z = [startZ, endZ],
                text = elevFloorInfo3D['MP_W_S'],
                line_color= [startColor, endColor],
                name="",
                mode='lines',
                line = dict(
                    color = 'black',
                    width = 3,
                    dash = 'solid'),
                #hoverinfo='skip',
                showlegend=False 
            )
            frame_traces.append(line_trace)

        # Create the label trace for this frame
        label_trace = go.Scatter3d(
            x=elevFloorInfo3D['labelX'], 
            y=elevFloorInfo3D['labelY'], 
            z=elevFloorInfo3D[f'{col}_start'], 
            text=elevFloorInfo3D['MP_W_S'], 
            mode='text', 
            textfont=dict(
                size=12,
                color='grey'), 
            hoverinfo='skip', 
            showlegend=False
        )
        frame_traces.append(label_trace)

        # Ensure the frame has the same number of traces as the figure
        while len(frame_traces) < max_traces_per_frame:
            frame_traces.append(go.Scatter3d(x=[], y=[], z=[], mode=[]))

        # Add the frame
        frames.append(go.Frame(data=frame_traces, name=col))

    fig.frames = frames

    # Slider
    sliders = [{"steps": [{"args": [[f.name], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                            "label": col, "method": "animate"} for col, f in zip(elevationFloorStart.columns, fig.frames)],
                "len": 0.95,
                "x": 0.035,
                "y": 0}]

    camera = dict(
        up=dict(x=0, y=0, z=1),
        center=dict(x=0, y=0, z=0),
        eye=dict(x=0.1, y=4, z=3)
    )

    # Define the play and pause buttons
    play_button = dict(
        label="&#9654;",
        method="animate",
        args=[None, {"frame": {"duration": 200, "redraw": True}, "fromcurrent": True, "transition": {"duration": 200, "easing": "quadratic-in-out"}}]
    )

    pause_button = dict(
        label="&#9724;",
        method="animate",
        args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}]
    )

    maxElev = elevFloorInfo3D.loc[:, elevFloorInfo3D.columns.str.contains('_start')].max().max()
    minElev = elevFloorInfo3D.loc[:, elevFloorInfo3D.columns.str.contains('_start')].min().min()

    # Update layout for slider and set consistent y-axis range
    fig.update_layout(
        # Update layout with play and pause buttons
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            buttons=[play_button, pause_button],
            x=0,  # x and y determine the position of the buttons
            y=-0.06,
            xanchor="right",
            yanchor="top",
            direction="left"
        )],
        autosize=False,
        margin=dict(l=0, r=0, b=100, t=0),
        scene_camera=camera,
        scene=dict(
            xaxis_title='',
            xaxis= dict(range=[400,-10]), 
            yaxis_title='',
            yaxis= dict(range=[130,-10]),
            zaxis_title='Floor Elevation [ft]',
            zaxis = dict(range = [minElev,maxElev])
        ),
        sliders=sliders,
        width = 1100,
        height = 600,
        scene_aspectmode='manual',
        scene_aspectratio=dict(x=7, y=2, z=1),
        uniformtext_minsize=10,
        annotations = plot3dAnno
        )

    # Set initial view, update hover mode
    fig.update_traces(x=frames[0].data[0].x, 
                    y=frames[0].data[0].y, 
                    z=frames[0].data[0].z,
                    hovertemplate="<br>".join([
                        "Elevation [ft]: %{z}"
                        ]),
                    hoverlabel=dict(
                        bgcolor = "white"
                        ))
    return fig