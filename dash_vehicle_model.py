# -*- coding: utf-8 -*-

import os
import time
import zmq
import struct
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

    def get_last(self):
        try:
            return self.states[-1]
        except:
            return None

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


class ZmqSender(object):
    port = "5557"

    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind("tcp://*:%s" % self.port)


class MyDashVehicleModel(object):
    def __init__(self):
        self.last_x_acc = 0.0
        self.last_steering_angle_vel = 0.0

        self.live_data = LiveData()
        self.live_data.start_thread()
        self.zmq_sender = ZmqSender()

        self.app = dash.Dash()

        df = pd.DataFrame({'name': ['t', 'x_vel'], 'value': [0, 0]})

        self.app.layout = html.Div(
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
                        html.Div(["x-acceleration"]),
                        dcc.Input(
                            id="x-acc-input-numeric",
                            placeholder="Enter a new acceleration in m/s2...",
                            type="number",
                            value=0,
                            min=0,
                            max=9,
                        ),
                        dcc.Slider(
                            id="x-acc-input-slider",
                            # tooltip="Enter a new acceleration in m/s2...",
                            min=-9,
                            max=9,
                            step=0.1,
                            value=0.0,
                        ),
                        html.Div(id="num_out0"),
                        html.Div(id="num_out1"),
                        html.Div(["steering-angle-velocity"]),
                        dcc.Input(
                            id="steering-angle-vel-input-numeric",
                            type="number",
                            value=0,
                            min=0,
                            max=9,
                        ),
                        dcc.Slider(
                            id="steering-angle-vel-input-slider",
                            min=-90,
                            max=90,
                            step=1.0,
                            value=0.0,
                        ),
                        html.Div(id="num_out2"),
                        html.Div(id="num_out3")
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

        @self.app.callback(
            dash.dependencies.Output(component_id='num_out0', component_property='children'),
            [dash.dependencies.Input('x-acc-input-numeric', 'value')])
        def update_output(value):
            self.last_x_acc = value
            self.zmq_send()
            # return value

        @self.app.callback(
            dash.dependencies.Output(component_id='num_out1', component_property='children'),
            [dash.dependencies.Input('x-acc-input-slider', 'value')])
        def update_output(value):
            self.last_x_acc = value
            self.zmq_send()


        @self.app.callback(
            dash.dependencies.Output(component_id='num_out2', component_property='children'),
            [dash.dependencies.Input('steering-angle-vel-input-numeric', 'value')])
        def update_output(value):
            self.last_steering_angle_vel = value
            self.zmq_send()


        @self.app.callback(
            dash.dependencies.Output(component_id='num_out3', component_property='children'),
            [dash.dependencies.Input('steering-angle-vel-input-slider', 'value')])
        def update_output(value):
            self.last_steering_angle_vel = value
            self.zmq_send()


        @self.app.callback(
            [dash.dependencies.Output('table', 'data'),
             dash.dependencies.Output('graphs', 'children')],
            [dash.dependencies.Input('graph-update', 'n_intervals')])
        def update_graph(n_interval):
            """
            This plots the graphs based on the symbol selected
            :param symbols: list of available symbols
            :return: graphs with high and low values
            """

            last_state = self.live_data.get_last()
            if last_state is not None:
                table_names = list(CState().__dict__.keys())
                table_values = ['{:.01f}'.format(getattr(last_state, k)) for k in table_names]
                dff = pd.DataFrame({'name': table_names, 'value': table_values})
            else:
                dff = pd.DataFrame()

            graphs = [
                html.Div(dcc.Graph(id='g{}'.format(graph_id),
                                   figure={'data': [{'x': [getattr(s, x_attr) for s in self.live_data.states],
                                                     'y': [getattr(s, y_attr) for s in self.live_data.states]}],
                                           'layout': go.Layout(
                                               xaxis={'title': x_attr},
                                               yaxis={'title': y_attr},
                                               margin={'l': 60, 'b': 40, 't': 10, 'r': 10},
                                               hovermode='closest'
                                           )},
                                   style={'height': '200px'}), style={"border": "1px black solid"}) for
                graph_id, (x_attr, y_attr) in enumerate([('x_pos', 'y_pos'),
                                                         ('t', 'x_vel'),
                                                         ('t', 'steering_angle'),
                                                         ('t', 'yaw_angle')])
            ]

            return dff.to_dict('records'), graphs


        @self.app.server.route('/<path:path>')
        def static_file(path):
            static_folder = os.getcwd()
            return send_from_directory(static_folder, path)


    def zmq_send(self):
        # print('The value is {}.'.format(value))
        self.zmq_sender.socket.send(struct.pack('dd', self.last_steering_angle_vel, self.last_x_acc))

if __name__ == '__main__':
    my_dash_vehicle_model = MyDashVehicleModel()
    my_dash_vehicle_model.app.run_server(debug=True, use_reloader=False)
