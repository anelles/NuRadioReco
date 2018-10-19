from __future__ import absolute_import, division, print_function  # , unicode_literals
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash
import plotly.graph_objs as go
import json
import numpy as np
import uuid
import glob
from NuRadioReco.utilities import units
from NuRadioReco.framework.parameters import stationParameters as stnp
from NuRadioReco.framework.parameters import channelParameters as chp
from flask import Flask, send_from_directory
from app import app
from apps import traces
from apps import cosmic_rays
from apps.common import get_point_index
import apps.simulation
import os
import sys
# from apps import summary
import dataprovider
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('index')

data_folder = os.path.dirname(sys.argv[1])

# Loading screen CSS
# app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/brPBPO.css"})
# app.css.append_css({
#     'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'
# })
app.css.append_css({"external_url": "https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css"})
provider = dataprovider.DataProvider()


app.title = 'ARIANNA viewer'

app.layout = html.Div([
    # represents the URL bar, doesn't render anything
    dcc.Location(id='url', refresh=False),
    html.Div(id='user_id', style={'display': 'none'},
             children=json.dumps(None)),
#     html.Div(id='filename', style={'display': 'none'},
#              children=json.dumps(None)),
    html.Div(id='station_id', style={'display': 'none'},
             children=json.dumps(None)),
    html.Div(id='event-ids',  style={'display': 'none'},
             children=json.dumps([])),

    html.Div([
        html.Div([
        html.Div('File location:', className='input-group-text')
        ], className='input-group-addon'),
        dcc.Input(id='datafolder', placeholder='filename', type='text', value=data_folder, className='form-control')
        ], className='input-group'),
    html.Div([
        dcc.Dropdown(id='filename',
                     options=[{'label': l, 'value': l} for l in sorted(glob.glob(data_folder + '/*.ar*'))],
                     className='custom-dropdown'),
         html.Div([
            html.Button('open file', id='btn-open-file', className='btn btn-default')
            ], className='input-group-btn'),
    ], className='input-group'),
    html.Div([
        html.Div([
                html.Button([
                        html.Div(className='fa fa-arrow-left')
                    ],
                    id='btn-previous-event',
                    className='btn btn-primary',
                    n_clicks_timestamp = 0
                ),
                html.Button(
                    id = 'event-number-display',
                    children = '''''',
                    className='btn btn-primary'
                ),
                html.Button([
                        html.Div(className='fa fa-arrow-right')
                    ],
                    id='btn-next-event',
                    className='btn btn-primary',
                    n_clicks_timestamp=0
                    )
            ],
            className='btn-group'
            ),
        html.Div([
             dcc.Slider(
                id='event-counter-slider',
                step=1,
                value=0,
                marks={}
            ),
        ],
        style={
        'margin': '10px 10px 20px 10px',
        'flex': '1'}
        )
    ],
    style={
    'display': 'flex'
    }),
    dcc.Tabs([
        dcc.Tab([
            html.H3('summary plots'),
            html.Div(id='trigger', style={'display': 'none'},
                     children=json.dumps(None)),
            html.Div([
                html.Div([
                    html.H5("template time fit")
                ], className="six columns"),
                html.Div([
                    html.H5("cross correlation fitter"),
                    dcc.Graph(id='skyplot-xcorr')
                ], className="six columns")
            ], className='row'),
            html.Div(id='output')
        ], id='summary-tab', label='Summary'),
        dcc.Tab([
            traces.layout
        ], label='Traces'),
        dcc.Tab([
            apps.simulation.layout
        ], label='Simulation'),
        dcc.Tab([
            cosmic_rays.layout
        ], label='Cosmic Rays')
    ])
])


# next/previous buttons
@app.callback(
Output('event-counter-slider', 'value'),
[Input('btn-next-event', 'n_clicks_timestamp'),
Input('btn-previous-event', 'n_clicks_timestamp')],
[State('event-counter-slider', 'value')]
)
def set_event_number(next_evt_click_timestamp, prev_evt_click_timestamp, i_event):
    print(i_event)
    if prev_evt_click_timestamp == 0 and next_evt_click_timestamp == 0:
        return 0
    if prev_evt_click_timestamp > next_evt_click_timestamp:
        return i_event - 1
    else:
        return i_event + 1

'''
@app.callback(
    Output('event-counter', 'children'),
    [Input('btn-next-event', 'n_clicks'),
     Input('btn-previous-event', 'n_clicks'),
     Input('event-counter-slider', 'value'),
     Input('skyplot', 'clickData'),
     Input('cr-xcorrelation', 'clickData'),
     Input('cr-xcorrelation-amplitude', 'clickData'),
     Input('cr-polarization-zenith', 'clickData'),
     Input('skyplot-xcorr', 'clickData'),
     Input('event-ids', 'children')],
    [State('event-counter', 'children'),
     State('filename', 'value'),
     State('user_id', 'children')])
def next_event(n_clicks_next, n_clicks_previous, evt_counter_slider, click1, click2, click3, click4, click5, jevent_ids,
               evt_counter_json, filename, juser_id):
#     filename = json.loads(jfilename)
    user_id = json.loads(juser_id)
    tmp = json.loads(evt_counter_json)
    evt_counter = tmp['evt_counter']
    current_selection = json.loads(jevent_ids)
    was_clicked = False
    print("current evt_counter is {}".format(evt_counter))
    if filename is not None:
        ariio = provider.get_arianna_io(user_id, filename)
        number_of_events = ariio.get_n_events()
        event_ids = ariio.get_event_ids()
        # first check if new event selection has fired callback
        # we do this by checking if current event is in event selection
        if((current_selection is not None) and (current_selection != []) and (str(event_ids[evt_counter]) not in current_selection)):
            print('not in current selection')
            evt_counter = get_point_index(event_ids, [current_selection[0]])[0]
        else:
            if(n_clicks_next != tmp['next']):
                if(current_selection != [] and current_selection is not None):  # do we have an active selection? then loop only through the selection
                    for event_index in range(evt_counter + 1, number_of_events):
                        if(str(event_ids[event_index]) in current_selection):
                            evt_counter = event_index
                            break
                else:
                    if(evt_counter < number_of_events - 1):
                        evt_counter += 1
            elif(n_clicks_previous != tmp['prev']):
                if(current_selection != [] and current_selection is not None):  # do we have an active selection? then loop only through the selection
                    for event_index in range(0, evt_counter)[::-1]:
                        if(str(event_ids[event_index]) in current_selection):
                            evt_counter = event_index
                            break
                else:
                    if(evt_counter > 0):
                        evt_counter -= 1
            else:  # then callback was fired by click on plot
                for click in [click1, click2, click3, click4, click5]:
                    if click is not None:
                        was_clicked = True
                        event_id = click['points'][0]['text']
                        event_index = get_point_index(event_ids, [event_id])[0]
                        if(event_index != tmp['evt_counter']):
                            evt_counter = event_index
                            was_clicked = True
                if not was_clicked:
                    if(current_selection != [] and current_selection is not None):  # do we have an active selection? then loop only through the selection
                        event_index = get_point_index(event_ids, [current_selection[evt_counter_slider]])[0]
                        if(event_index != tmp['evt_counter']):
                            evt_counter = event_index
                    else:
                        if(evt_counter_slider != tmp['evt_counter']):
                            print("evt_counter_slider is {}".format(evt_counter_slider))
                            evt_counter = evt_counter_slider  # set event counter to current slider value

        print("setting evt_counter to {}".format(evt_counter))
    else:
        number_of_events = 0
        event_ids = []
        event_counter = 0
        n_clicks_next = 0
        n_clicks_previous = 0
    tmp['evt_counter'] = evt_counter
    tmp['next'] = n_clicks_next
    tmp['prev'] = n_clicks_previous
    return json.dumps(tmp)
'''

@app.callback(
Output('event-number-display', 'children'),
[Input('filename', 'value'),
Input('event-counter-slider', 'value')]
)
def set_event_number_display(filename, event_number):
    if filename is None:
        return 'No file selected'
    return 'Event {}'.format(event_number)

# slider functions
###############
# set maximum value of slider
@app.callback(
    Output('event-counter-slider', 'max'),
    [Input('filename', 'value'),
     Input('event-ids', 'children')],
    [State('user_id', 'children')])
def update_slider_options(filename, jevent_ids, juser_id):
    if filename is None:
        return 0
#     filename = json.loads(jfilename)
    current_selection = json.loads(jevent_ids)
    if(current_selection != [] and current_selection is not None):
        return len(current_selection) - 1
    user_id = json.loads(juser_id)
    ariio = provider.get_arianna_io(user_id, filename)
    number_of_events = ariio.get_n_events()
    return number_of_events - 1

@app.callback(
Output('event-counter-slider', 'marks'),
[Input('filename', 'value')],
[State('user_id', 'children')]
)
def update_slider_marks(filename, juser_id):
    if filename is None:
        return {}
    user_id = json.loads(juser_id)
    ariio = provider.get_arianna_io(user_id, filename)
    n_events = ariio.get_n_events()
    step_size = int(np.power(10., int(np.log10(n_events))))
    marks = {}
    for i in range(0, n_events, step_size):
        print (marks)
        marks[i] = str(i)
    if n_events%step_size != 0:
        marks[n_events] = str(n_events)
    return marks
    

@app.callback(Output('user_id', 'children'),
              [Input('url', 'pathname')],
              [State('user_id', 'children')])
def set_uuid(pathname, juser_id):
    user_id = json.loads(juser_id)
    if(user_id is None):
        user_id = uuid.uuid4().hex
    return json.dumps(user_id)


@app.callback(Output('filename', 'options'),
              [Input('datafolder', 'value')])
def set_filename_dropdown(folder):
    return [{'label': l, 'value': l} for l in sorted(glob.glob(os.path.join(folder, '*.ar*')))]

# @app.callback(Output('filename', 'children'),
#               [Input('btn-open-file', 'n_clicks')],
#               [State('user_id', 'children'),
#                State('filename', 'children')])
# def open_file(n_clicks, juser_id, jfilename):
#     user_id = json.loads(juser_id)
#     filename = json.loads(jfilename)
#     if(filename is None):
#         with open('filename.txt', 'r') as fin:
#             filename = fin.readlines()[0].strip('\n')
#             ariio = provider.get_arianna_io(user_id, filename)
#     print("setting filename to ", filename)
#     return json.dumps(filename)


@app.callback(Output('station_id', 'children'),
              [Input('filename', 'value')],
              [State('user_id', 'children'),
               State('station_id', 'children')])
def set_station_id(filename, juser_id, jstation_id):
    station_id = json.loads(jstation_id)
    if(station_id is None and filename is not None):
        user_id = json.loads(juser_id)
#         filename = json.loads(jfilename)
        ariio = provider.get_arianna_io(user_id, filename)
        station_id = ariio.get_header().keys()[0]
    print("setting stationid to {}".format(station_id))
    return json.dumps(station_id)

# @app.callback(Output('event-counter', 'children'),
#               [Input('filename', 'children')],
#               [State('event-counter', 'children')])
# def reset_event_counter(jfilename, jeventcounter):
#     eventcounter = json.loads(jeventcounter)
#     eventcounter['evt_counter'] = 0
#     return json.dumps(eventcounter)


@app.callback(Output('summary', 'style'),
              [Input('url', 'pathname')])
def display_page2(pathname):
    if pathname == '/apps/traces':
        return {'display': 'none'}
    if pathname == '/apps/summary':
        return {}
#     elif pathname == '/apps/app2':
#         return app2.layout
    else:
        return '404'


@app.callback(Output('skyplot-xcorr', 'figure'),
              [Input('filename', 'value'),
               Input('trigger', 'children'),
               Input('event-ids', 'children'),
               Input('station_id', 'children')],
              [State('user_id', 'children')])
def plot_skyplot_xcorr(filename, trigger, jcurrent_selection, jstation_id, juser_id):
    if filename is None or jstation_id is None:
        return {}
    user_id = json.loads(juser_id)
    station_id = json.loads(jstation_id)
    current_selection = json.loads(jcurrent_selection)
    ariio = provider.get_arianna_io(user_id, filename)
    traces = []
    keys = ariio.get_header()[station_id].keys()
    if stnp.zenith in keys and stnp.azimuth in keys:
        traces.append(go.Scatterpolar(
            r=np.rad2deg(ariio.get_header()[station_id][stnp.zenith]),
            theta=np.rad2deg(ariio.get_header()[station_id][stnp.azimuth]),
            text=[str(x) for x in ariio.get_event_ids()],
            mode='markers',
            name='all events',
            opacity=1,
            marker=dict(
                color='blue'
            )
        ))
    else:
        return {}

    # update with current selection
    print('current selection is ', current_selection)
    if current_selection != []:
        for trace in traces:
            trace['selectedpoints'] = get_point_index(trace['text'], current_selection)

    return {
        'data': traces,
        'layout': go.Layout(
            showlegend= True,
#             xaxis={'type': 'linear', 'title': ''},
#             yaxis={'title': xcorr_states[xcorr_type], 'range': [0, 1]},
#             margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
#             legend={'x': 0, 'y': 1},
            hovermode='closest',
            height=500
        )
    }


# update event ids list from plot selection
@app.callback(Output('event-ids', 'children'),
              [Input('cr-skyplot', 'selectedData'),
               Input('cr-xcorrelation', 'selectedData'),
               Input('cr-xcorrelation-amplitude', 'selectedData'),
               Input('skyplot-xcorr', 'selectedData'),
               Input('cr-polarization-zenith', 'selectedData')],
              [State('event-ids', 'children')])
def set_event_selection(selectedData1, selectedData2, selectedData3, selectedData4, selectedData5, jcurrent_selection):
    current_selection = json.loads(jcurrent_selection)
    tcurrent_selection = []
    print(current_selection)
    for i, selection in enumerate([selectedData1, selectedData2, selectedData3, selectedData4, selectedData5]):  # check which selection has fired the callback
        if selection is not None:
            print('selection {} is not None'.format(i))
            event_ids = []
            for x in selection['points']:
                print(x)
                t = x['text']
                if t not in event_ids:
                    event_ids.append(t)
            print(event_ids)
            if not np.array_equal(np.array(event_ids), current_selection):  # this selection has fired the callback
                print('selection {} is different from current selection'.format(i))
                tcurrent_selection = event_ids
#     print('selection 1', selectedData1)
#     print('selection 2', selectedData2)
#     print('current selection', current_selection)
    return json.dumps(tcurrent_selection)

# # update event ids list from plot selection
# @app.callback(Output('skyplot', 'figure'),
#                [Input('event-ids', 'children')],
#                [State('skyplot', 'figure')])
# def update_event_selection1(jcurrent_selection, figure):
#     current_selection = json.loads(jcurrent_selection)
#     figure['data']['selectedpoints'] = current_selection
#     return figure
#
#
# # update event ids list from plot selection
# @app.callback(Output('cr-xcorrelation', 'figure'),
#                [Input('event-ids', 'children')],
#                [State('cr-xcorrelation', 'figure')])
# def update_event_selection2(jcurrent_selection, figure):
#     current_selection = json.loads(jcurrent_selection)
#     figure['data']['selectedpoints'] = current_selection
#     return figure


if __name__ == '__main__':
    app.run_server(debug=True, port=8080)
