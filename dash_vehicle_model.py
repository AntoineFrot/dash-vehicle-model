# -*- coding: utf-8 -*-

import os
import time
import zmq
import _thread
import dash
import dash_table
from flask import send_from_directory
import dash_html_components as html
import dash_core_components as dcc

import plotly.graph_objs as go
import pandas as pd

from cstate import CState

MAX_LEN_DATA = 500
REFRESH_PERIOD_MS = 300


class LiveData:

    def __init__(self):
        self.states = []
        self.running = True

    # def append(self, t, x_pos, y_pos, steering_angle, x_vel, yaw_angle, steering_angle_vel, x_acc):
    #     self.t.append(t)
    #     self.x_pos.append(x_pos)
    #     self.y_pos.append(y_pos)
    #     self.steering_angle.append(steering_angle)
    #     self.x_vel.append(x_vel)
    #     self.yaw_angle.append(yaw_angle)
    #     self.steering_angle_vel.append(steering_angle_vel)
    #     self.x_acc.append(x_acc)
    #     if len(self.t) > MAX_LEN_DATA:
    #         self.t = self.t[-MAX_LEN_DATA:]
    #         self.x_pos = self.x_pos[-MAX_LEN_DATA:]
    #         self.y_pos = self.y_pos[-MAX_LEN_DATA:]
    #         self.steering_angle = self.steering_angle[-MAX_LEN_DATA:]
    #         self.x_vel = self.x_vel[-MAX_LEN_DATA:]
    #         self.yaw_angle = self.yaw_angle[-MAX_LEN_DATA:]
    #         self.steering_angle_vel = self.steering_angle_vel[-MAX_LEN_DATA:]
    #         self.x_acc = self.x_acc[-MAX_LEN_DATA:]

    # def thread_func_random(self, thread_name, delay):
    #     while self.running:
    #         try:
    #             t_new = self.t[-1]+.1
    #         except:
    #             t_new = 0.0
    #         self.append(t_new, random.randint(0, 100))
    #         time.sleep(delay)

    def get_last(self):
        try:
            return self.states[-1]
        except:
            return None

    # def get_columns(self):
    #     print(self.states)
    #     return []#[[state.t for state in self.states]]

    def thread_func_zmq(self, thread_name, delay):

        port = "5556"

        # Socket to talk to server
        context = zmq.Context()
        socket = context.socket(zmq.SUB)

        socket.connect("tcp://localhost:%s" % port)
        socket.setsockopt_string(zmq.SUBSCRIBE, '')

        while self.running:
            state = socket.recv_pyobj()
            self.states.append(state)

    def start_thread(self):
        try:
            _thread.start_new_thread(self.thread_func_zmq, ("Thread-1", 0.1,))
        except:
            print("Error: unable to start thread")


live_data = LiveData()
live_data.start_thread()

app = dash.Dash()
# app.config['suppress_callback_exceptions']=True

df = pd.DataFrame({'name': ['t', 'x_vel'], 'value': [0, 0]})

app.layout = html.Div(
    [
        html.Div([

            html.Link(
                rel='stylesheet',
                href='/static/base.css'
            ),

            html.Div([
                html.H2("My vehicle model dashboard"),
            ], className="four columns"),

            html.Div([
                html.Label(
                    [
                        html.Div(["Time points"]),
                        dcc.Input(
                            id="times-input",
                            placeholder="Enter a value...",
                            type="number",
                            value=5,
                            # debounce=True,
                            min=3,
                            max=999,
                        ),
                    ]
                ),
            ], className="four columns"),
        ], className="row"),

        html.Div([
            html.Div(id='graphs', className="eight columns"),
            html.Div(
                [dash_table.DataTable(
                    id='table',
                    columns=[{"name": i, "id": i} for i in df.columns],
                    data=df.to_dict('records'),
                )], className="two columns"),
        ], className="row"),

        # INTERVAL FOR UPDATING
        dcc.Interval(
            id='graph-update',
            interval=REFRESH_PERIOD_MS,  # in milliseconds
            n_intervals=0
        ),
    ],
)


@app.callback(
    [dash.dependencies.Output('table', 'data'),
     dash.dependencies.Output('graphs', 'children')],
    [dash.dependencies.Input('graph-update', 'n_intervals')])
def update_graph(n_interval):
    """
    This plots the graphs based on the symbol selected
    :param symbols: list of available symbols
    :return: graphs with high and low values
    """

    last_state = live_data.get_last()
    if last_state is not None:
        table_names = list(CState().__dict__.keys())
        table_values = ['{:.01f}'.format(getattr(last_state, k)) for k in table_names]
        dff = pd.DataFrame({'name': table_names, 'value': table_values})
    else:
        dff = pd.DataFrame()

    graphs = [
        html.Div(dcc.Graph(id='g{}'.format(graph_id),
                           figure={'data': [{'x': [getattr(s, x_attr) for s in live_data.states],
                                             'y': [getattr(s, y_attr) for s in live_data.states]}],
                                   'layout': go.Layout(
                                       xaxis={'title': x_attr},
                                       yaxis={'title': y_attr},
                                       margin={'l': 60, 'b': 40, 't': 10, 'r': 10},
                                       # legend={'x': 'x', 'y': 'y'},
                                       hovermode='closest'
                                   )},
                           style={'height': '200px'}), style={"border": "1px black solid"}) for
        graph_id, (x_attr, y_attr) in enumerate([('x_pos', 'y_pos'),
                                                 ('t', 'x_vel'),
                                                 ('t', 'steering_angle'),
                                                 ('t', 'yaw_angle')])
    ]

    return dff.to_dict('records'), graphs


@app.server.route('/<path:path>')
def static_file(path):
    static_folder = os.getcwd()
    return send_from_directory(static_folder, path)


if __name__ == '__main__':
    app.run_server(debug=True)
