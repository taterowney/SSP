from PyWindow import *
import os
from numpy import array, log, exp, sin
from lmfit import Model
import warnings
import inspect
import csv
import time

# from labquest import LabQuest

# Table library: https://handsontable.com/docs/javascript-data-grid/installation/
# Chart library: https://www.chartjs.org/docs/latest/

# ./.venv/bin/pyinstaller --onedir --windowed --noconfirm --add-data "./static/*:static" --icon='LorenzAttractorIcon.icns' main.py

# Read the html file
with open(os.path.join(BASE_DIR, "static/new.html"), "r") as f:
    html = f.read()


FUNCTION_PLOTTING_OVERSHOOT = 1.5

class FunctionPlotter:
    def __init__(self, window, container_id="chart"):
        self.window = window
        self.chart = Chart(self.window.document.getElementById(container_id).getContext('2d'), {'type': 'scatter',
                                                                               'data':
                                                                                   {'datasets': [
                                                                                       {'label': 'Function 1', 'data': [], 'backgroundColor': 'rgba(255,99,132,1)', 'borderColor': 'rgba(255,99,132,1)', 'showLine': True, 'pointRadius': 0},
                                                                                       {'label': 'Dataset 1', 'data': [], 'backgroundColor': 'rgba(0,0,255,1)', 'borderColor': 'rgba(0,0,255,1)', 'showLine': False}]},
                                                                               'options':
                                                                                   {'pan': {'enabled': True, 'mode': 'xy', 'speed': 10, 'threshold': 10},
                                                                                    'maintainAspectRatio': False,
                                                                                    'responsive': True,
                                                                                    'scales': {'x': {'type': 'linear', 'position': 'bottom'}},
                                                                                    'plugins': {'zoom': {'zoom': {'wheel': {'enabled': True}, 'pinch': {'enabled': False}, 'onZoom': lambda *args: self.updatePlot(self.x_scales.min, self.x_scales.max, self.y_scales.min, self.y_scales.max)},
                                                                                                         'pan': {'enabled': True, 'mode': 'xy', 'speed': 10, 'threshold': 10, 'onPan': lambda *args: self.updatePlot(self.x_scales.min, self.x_scales.max, self.y_scales.min, self.y_scales.max)},},
                                                                                                'legend': {'display': False}}}})
        self.x_scales = self.chart.scales.x
        self.y_scales = self.chart.scales.y
        self.datasets = self.chart.data.datasets
        self.dataset_identifiers = {"Function 1": 0, "Dataset 1": 1}
        self.plotted_functions = {"Function 1": {"is_active": False, "generator": None, "x_min": None, "x_max": None, "y_min": None, "y_max": None}}

    def setZoom(self, x_min, x_max, y_min, y_max):
        self.chart.zoomScale('x', {'min': x_min, 'max': x_max})
        self.chart.zoomScale('y', {'min': y_min, 'max': y_max})
        self.updatePlot(x_min, x_max, y_min, y_max)
        self.chart.update('none')

    def setData(self, dataset, x, y):
        self.datasets[self.dataset_identifiers[dataset]].data = [{'x': x[i], 'y': y[i]} for i in range(len(x))]
        self.chart.update('none')

    def plot(self, fxn, label="Function 1"):
        self.plotted_functions[label]["is_active"] = True
        self.plotted_functions[label]["generator"] = fxn
        self.plotted_functions[label]["x_min"] = self.x_scales.min
        self.plotted_functions[label]["x_max"] = self.x_scales.max
        # self.plotted_functions[label]["y_min"] = self.y_scales.min
        # self.plotted_functions[label]["y_max"] = self.y_scales.max
        self.updatePlot(self.x_scales.min, self.x_scales.max, self.y_scales.min, self.y_scales.max)

    def clearPlot(self, label="Function 1"):
        self.plotted_functions[label]["is_active"] = False
        self.setData(label, [], [])
        self.updatePlot(self.x_scales.min, self.x_scales.max, self.y_scales.min, self.y_scales.max)

    def updatePlot(self, x_min_current, x_max_current, y_min_current, y_max_current):
        # Update the plot for all active functions
        delta_x = x_max_current - x_min_current
        # delta_y = y_max_current - y_min_current
        for label, data in self.plotted_functions.items():
            if data["is_active"]:
                # To avoid plotting a very similar piece of the function over and over, we overshoot slightly, and when the user zooms or pans, we extend the range of the plot if needed
                # Check if the sides of our view of the plot are approaching the place where we last stopped graphing the function, or if they are much narrower than the last time we graphed the function
                if data["x_min"] > x_min_current - (delta_x*FUNCTION_PLOTTING_OVERSHOOT*0.5) or data["x_max"] < x_max_current + (delta_x*FUNCTION_PLOTTING_OVERSHOOT*0.5) or data["x_max"] - data["x_min"] > (x_max_current - x_min_current)*FUNCTION_PLOTTING_OVERSHOOT*2 or data["x_max"] - data["x_min"] < (x_max_current - x_min_current)/FUNCTION_PLOTTING_OVERSHOOT*2:
                    x, y = self.generatePoints(data["generator"], x_min_current - (delta_x*FUNCTION_PLOTTING_OVERSHOOT), x_max_current + (delta_x*FUNCTION_PLOTTING_OVERSHOOT), 100)
                    self.plotted_functions[label]["x_min"] = x_min_current - (delta_x*FUNCTION_PLOTTING_OVERSHOOT)
                    self.plotted_functions[label]["x_max"] = x_max_current + (delta_x*FUNCTION_PLOTTING_OVERSHOOT)
                    self.setData(label, x, y)

    def generatePoints(self, fxn, x_min, x_max, num_points):
        step = (x_max - x_min) / num_points
        x = [x_min + step * i for i in range(num_points)]
        y = [fxn(x[i]) for i in range(num_points)]
        return x, y


class DataSpreadsheet:
    def __init__(self, window, container_id="spreadsheet"):
        self.window = window
        initial_data = [['', ''] for _ in range(100)]
        # initial_data = [[1, 2], [3, 4], [5, 6], [7, 9]] + initial_data
        self.table = Handsontable(self.window.document.getElementById(container_id), {'data': initial_data,
                                                                                             'rowHeaders': True,
                                                                                             'colHeaders': ["X", "Y"],
                                                                                             'contextMenu': True,
                                                                                             'manualColumnResize': True,
                                                                                             'manualRowResize': True,
                                                                                             'stretchH': 'all',
                                                                                             'height': '60vh',
                                                                                             'width': '30vw',
                                                                                             'licenseKey': 'non-commercial-and-evaluation',
                                                                                             'columns': [{'type': 'numeric', 'format': '0,0.00'}, {'type': 'numeric', 'format': '0,0.00'}]})
        self.x_data = []
        self.y_data = []
        self.table.addHook('afterChange', lambda *args: self.updatePlotterFromSpreadsheet(plotter))

    def getData(self):
        return eval(self.table.getData().getLiteral().replace("null", "''"))

    def updatePlotterFromSpreadsheet(self, plotter, x_column=0, y_column=1):
        data = eval(self.table.getData().getLiteral().replace("null", "''"))
        x = []
        y = []
        for row in data:
            if isinstance(row[x_column], (int, float)) and isinstance(row[y_column], (int, float)):
                x.append(row[x_column])
                y.append(row[y_column])
        current_x_min, current_x_max, current_y_min, current_y_max = plotter.x_scales.min, plotter.x_scales.max, plotter.y_scales.min, plotter.y_scales.max
        self.x_data = x
        self.y_data = y
        plotter.setData("Dataset 1", x, y)
        # For some reason, when updatePlot is run here specifically, it tries to zoom out to encompass the unseen boundaries of the function as well...
#        plotter.updatePlot(plotter.x_scales.min, plotter.x_scales.max, plotter.y_scales.min, plotter.y_scales.max)
        plotter.setZoom(current_x_min, current_x_max, current_y_min, current_y_max)
        plot_best_fit()

#TODO: Prevent slightly different events from being saved on the Javascript end during callbacks, etc.
# Maybe just add an "addToTrashCollection" method to the JSObject class



w = PyWindow("Test", html)
Chart = JSModule(w, "Chart")
Handsontable = JSModule(w, "Handsontable")
w.open()
spreadsheet = DataSpreadsheet(w)
plotter = FunctionPlotter(w)

document = w.document


# lq = LabQuest()



def zoomToFitPoints(*args, x_data=None, y_data=None):
    if x_data is None or y_data is None:
        x_data, y_data = spreadsheet.x_data, spreadsheet.y_data
    if len(x_data) > 0:
        min_x, max_x, min_y, max_y = min(x_data), max(x_data), min(y_data), max(y_data)
        plotter.setZoom(min_x - 0.1*(max_x - min_x), max_x + 0.1*(max_x - min_x), min_y - 0.1*(max_y - min_y), max_y + 0.1*(max_y - min_y))
    else:
        plotter.setZoom(0, 10, 0, 10)

w.document.getElementById("reset").onclick = zoomToFitPoints


def plot_best_fit(*args):
#    selection = w.document.getElementById("functionSelect").value.replace('"', "")

    x_data, y_data = spreadsheet.x_data, spreadsheet.y_data

    x_data = array(x_data, dtype="float64")
    y_data = array(y_data, dtype="float64")

    if len(x_data) < 2 or len(y_data) < 2:
        return

    if document.getElementById("plot-proportional").checked == True:
        fxn = lambda x, m: m*x
        function_render = lambda m: f"y = {round(m, 4)}x"

    elif document.getElementById("plot-linear").checked == True:
        fxn = lambda x, m, b: m * x + b
        function_render = lambda m, b: f"y = {round(m, 4)}x + {round(b, 4)}"

    elif document.getElementById("plot-quadratic").checked == True:
        fxn = lambda x, a, b, c: a + b * x + c * x ** 2
        function_render = lambda a, b, c: f"y = {round(a, 4)}x^2 + {round(b, 4)}x + {round(c, 4)}"

    elif document.getElementById("plot-cubic").checked == True:
        fxn = lambda x, a, b, c, d: a + b * x + c * x ** 2 + d * x ** 3
        function_render = lambda a, b, c, d: f"y = {round(d, 4)}x^3 + {round(c, 4)}x^2 + {round(b, 4)}x + {round(a, 4)}"

    elif document.getElementById("plot-exponential").checked == True:
        fxn = lambda x, a, b: a * exp(b * x)
        function_render = lambda a, b: f"y = {round(a, 4)}e^{round(b, 4)}x"

    elif document.getElementById("plot-logarithmic").checked == True:
        fxn = lambda x, a, b: a * log(b * x)
        function_render = lambda a, b: f"y = {round(a, 4)} ln({round(b, 4)}x)"

    elif document.getElementById("plot-power").checked == True:
        fxn = lambda x, a, b: a * x ** b
        function_render = lambda a, b: f"y = {round(a, 4)} x^{round(b, 4)}"

    elif document.getElementById("plot-sinusoidal").checked == True:
        fxn = lambda x, a, b, c, d: a * sin(b * x + c) + d
        function_render = lambda a, b, c, d: f"y = {round(a, 4)} sin({round(b, 4)}x + {round(c, 4)}) + {round(d, 4)}"

    else:
        plotter.clearPlot()
        document.getElementById("best-fit-render").innerText = "--"
        return

#    fit = curve_fit(fxn, x_data, y_data)[0]
#    plotter.plot(lambda x: fxn(x, *fit))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    model = Model(fxn)
    params_dict = {argname: 1 for argname in inspect.signature(fxn).parameters.keys() if argname != "x"}
    params = model.make_params(**params_dict)
    try:
        result = model.fit(y_data, params, x=x_data)
    except ValueError:
        plotter.clearPlot()
        document.getElementById("best-fit-render").innerText = "Couldn't find valid fit"
        return
    plotter.plot(lambda x: fxn(x, **result.best_values))
    document.getElementById("best-fit-render").innerText = function_render(*result.best_values.values())

def clear_best_fit_selection(*args):
    plotter.clearPlot()
    document.getElementById("best-fit-render").innerText = "--"
    for radio in document.getElementsByName("interpolation-options"):
        radio.checked = False

document.getElementById("clear-plot").onclick = clear_best_fit_selection

document.getElementById("interpolation-options-select").addEventListener("change", lambda *args: plot_best_fit())


def showSaveDialog(filename="Untitled", extension="csv"):
    if OPERATING_SYSTEM == "darwin":
        result = subprocess.run(["/bin/bash", os.path.join(BASE_DIR, "static/saveDialog.sh"), filename, extension], stdout=subprocess.PIPE)
        return result.stdout.decode('utf-8').replace("\n", "")
    else:
        # print("Saving not yet supported.")
        pass

def showLoadDialog():
    if OPERATING_SYSTEM == "darwin":
        result = subprocess.run(["/bin/bash", os.path.join(BASE_DIR, "static/loadDialog.sh")], stdout=subprocess.PIPE)
        return result.stdout.decode('utf-8').replace("\n", "")
    else:
        # print("Loading not yet supported.")
        pass

CURRENT_FILE_NAME = None

def exportData():
    global CURRENT_FILE_NAME
    data = spreadsheet.getData()
    if CURRENT_FILE_NAME:
        target = showSaveDialog(filename=CURRENT_FILE_NAME)
    else:
        target = showSaveDialog()
    try:
        # TODO: test for valid paths
        if os.path.exists(target) or "/." not in target:
#            CURRENT_FILE_NAME = target
            with open(target, 'w', newline='') as f:
                writer = csv.DictWriter(f, ["x", "y"])
                writer.writeheader()
                for row in data:
                    if row[0] not in ['', None] and row[1] not in ['', None]:
                        writer.writerow({'x': row[0], 'y': row[1]})
    except Exception as e:
        print(e)

def importData():
    path = showLoadDialog()
    if not path:
        return
    if path == "cancelled":
        return
    with open(path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        try:
            data = [[float(row["x"]), float(row["y"])] for row in reader]
        except ValueError:
            # non-numeric data
            data = []
        if len(data) < 100:
            data += [['', ''] for _ in range(100 - len(data))]
        spreadsheet.table.loadData(data)
        zoomToFitPoints(x_data=[row[0] for row in data if row[0] not in ['', None]], y_data=[row[1] for row in data if row[1] not in ['', None]])

document.getElementById("exportData").onclick = lambda *args: exportData()
document.getElementById("importData").onclick = lambda *args: importData()

def showToast(title, message):
    document.getElementById("error-toast-title").innerText = title
    document.getElementById("error-toast-message").innerText = message
    document.getElementById("error-toast").classList.add("show")

# def connectLabquest():
#     if lq.open() == 0:
#         return True
#     else:
#         showToast("No LabQuest found", "Please connect a LabQuest device and try again.")
#         return False

def finalInit(*args):
    spreadsheet.updatePlotterFromSpreadsheet(plotter)
    zoomToFitPoints()

finalInit()



while True:
    if ServerManager.is_online:
        time.sleep(0.1)
    else:
        # ServerManager.server_thread.join()
        break
