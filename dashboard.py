"""
A small dashboard for very simple ebisim simulations
"""

import math

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html

import ebisim
import numpy as np

_BOOTSTRAP_CDN = "https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css"
_DISCLAIMER = 'THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.'

_ELEMENTS = [{"label":ebisim.elements.element_name(z), "value":z} for z in range(2, 106)]

_HEADER = html.Section(className="text-center", children=[
    html.H1("ebisim dash.", className="mb-3"),
    html.P("\nA dashboard for basic ebisim simulations.\n", className="lead text-muted"),
    html.Hr()
])

_FOOTER = html.Section(className="text-justify", children=[
    html.Hr(),
    html.H4('DISCLAIMER', className="text-muted mb-3"),
    html.P(_DISCLAIMER, className="text-muted")
])

_CONTROLS = html.Div(className="container", children=[
    html.P("Confirm entries by pressing enter or switching focus."),
    html.Div(className="row", children=[
        html.Div(className="col-md mb-3", children=[
            html.Label("Element", htmlFor="ctrl_element"),
            dcc.Dropdown(id="ctrl_element", options=_ELEMENTS, value=20)
        ]),
        html.Div(className="col-md mb-3", children=[
            html.Label("Continuous neutral injection", htmlFor="ctrl_cni"),
            dcc.Checklist(id="ctrl_cni", options=[
                {"label": "Activate CNI", "value": "Active"},
            ], values=[], labelStyle={'display': 'inline-block'}, className="form-control")
        ]),
        html.Div(className="col-md mb-3", children=[
            html.Label("Breeding time (ms)", htmlFor="ctrl_brtime"),
            dcc.Input(id="ctrl_brtime", value=200, min=1, type="number", className="form-control",
                      debounce=True)
        ])
    ]),
    html.Div(className="row", children=[
        html.Div(className="col-md mb-3", children=[
            html.Label("Current density (A/cm^2)", htmlFor="ctrl_curden"),
            dcc.Input(id="ctrl_curden", value=100, min=1, type="number", className="form-control",
                      debounce=True)
        ]),
        html.Div(className="col-md mb-3", children=[
            html.Label("Beam energy (eV)", htmlFor="ctrl_energy"),
            dcc.Input(id="ctrl_energy", value=5000, min=1, type="number", className="form-control",
                      debounce=True)
        ]),
        html.Div(className="col-md mb-3", children=[
            html.Label("DR FWHM (eV) [0 to disable]", htmlFor="ctrl_fwhm"),
            dcc.Input(id="ctrl_fwhm", value=50, min=0, type="number", className="form-control",
                      debounce=True)
        ])
    ])
])


app = dash.Dash(__name__, external_stylesheets=[_BOOTSTRAP_CDN], url_base_pathname="/ebisim/")
server = app.server

app.layout = html.Div(className="container-fluid", children=[
    _HEADER,
    html.Div(className="row", children=[
        html.Div(className="col", children=[
            _CONTROLS,
            dcc.Graph(id='plot_csevo', style={'height': 700},),
        ]),
        html.Div(className="col", children=[
            html.Label("Distribution plot time (ms)", htmlFor="ctrl_abtime"),
            dcc.Input(id="ctrl_abtime", value=100, min=0, max=200, type="number",
                className="form-control"),
            dcc.Graph(id='plot_distr', style={},),
            dcc.Graph(id='plot_highest', style={},),
        ]),
    ]),
    _FOOTER
])

@app.callback(Output("ctrl_abtime", "max"), [Input("ctrl_brtime", "value")])
def limit_slider(tmax):
    return tmax


@app.callback(Output("plot_csevo", 'figure'), [
    Input("ctrl_element", "value"), Input("ctrl_curden", "value"), Input("ctrl_energy", "value"),
    Input("ctrl_fwhm", "value"), Input("ctrl_brtime", "value"), Input("ctrl_cni", "values")
])
def update_csevo(z, j, e_kin, dr_fwhm, tmax, cni):
    """This function creates the charge state evolution plot"""
    tmax /= 1000
    cni = True if "Active" in cni else False

    try:
        res = ebisim.basic_simulation(int(z), j, e_kin, tmax, dr_fwhm=dr_fwhm, CNI=bool(cni))
    except:
        res = None

    data = []
    if res:
        for cs in range(res.N.shape[0]):
            data.append(
                {"x": res.t, "y":res.N[cs, :]/res.N.sum(axis=0), "name":str(cs)+"+", "type":"line"}
            )

    highlim = math.log10(tmax)
    lowlim = math.floor(math.log10(.01/j))
    lowlim = lowlim if (lowlim < highlim) else highlim-1
    layout = {
        "title":'Charge state evolution',
        "template":"plotly_dark",
        "xaxis":{"title":"Time (s)", "type":"log", "range":[lowlim, highlim]},
        "yaxis":{"title":"Relative abundance"}
    }

    return {"data":data, "layout":layout}

def figure_to_data(figure):
    return [(np.array(line["x"]), np.array(line["y"])) for line in figure["data"]]

@app.callback(Output("plot_distr", 'figure'), [
    Input("plot_csevo", 'figure'), Input("ctrl_abtime", "value")
    ])
def update_distr(csevo, time):
    """This function creates the plot for times with the highest abundance"""
    time /= 1000
    distr = []
    for (t, N) in figure_to_data(csevo):
        distr.append(np.interp(time, t, N))

    data = [{
        "x": list(range(len(distr))), "y":distr, "type":"bar"
    }]

    layout = {
        "title":f'Charge state distribution at t = {1000*time:.0f} ms',
        "template":"plotly_dark",
        "xaxis":{"title":"Charge state", "range":[0, len(distr)]},
        "yaxis":{"title":"Abdundance",}
    }

    return {"data":data, "layout":layout}

@app.callback(Output("plot_highest", 'figure'), [Input("plot_csevo", 'figure')])
def update_highest(csevo):
    """This function creates the plot for times with the highest abundance"""
    tmax = [t[np.argmax(N)] for (t, N) in figure_to_data(csevo)]

    data = [{
        "x": list(range(len(tmax))), "y":tmax, "type":"bar"
    }]

    layout = {
        "title":'Time of largest abundance',
        "template":"plotly_dark",
        "xaxis":{"title":"Charge state", "range":[0, len(tmax)]},
        "yaxis":{"title":"Time (s)", "type":"log"}
    }

    return {"data":data, "layout":layout}

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0")
