import json

from BrowserAPI import *
import functools


keywordsPyToJS = {"className": "class"}
keywordsJSToPy = {v: k for k, v in keywordsPyToJS.items()}

def toJSKeyword(string):
    # some attributes and styles have names that are reserved words in Python
    if string in keywordsPyToJS.keys():
        return keywordsPyToJS[string]
    else:
        return string


class FrontendJavascriptError(Exception):
    pass

# Wrapper for Window class that controls its frontend JS with a Python API
class PyWindow(Window):
    def __init__(self, title, html, height=None, width=None, fullscreen=False, included_scripts=[]):
        super().__init__(title, html, height, width, fullscreen, included_scripts)
        self.js_objects = {}
        self._cb_name_counter_new = 0
        self._cb_functions = {}

    def open(self):
        super().open()
#        self.js("(() => { window.trackedObjects = []})()")
        self.js(f"pageId = '{self.page}';")
        self.document = self.run_js_function("return document", await_result=True)

    # def getElementById(self, id):
    #     return self.load_elements(f"document.getElementById('{id}')")
    #
    # def getElementsByClassName(self, className):
    #     return self.load_elements(f"document.getElementsByClassName('{className}')")
    #
    # def getElementsByTagName(self, tagName):
    #     return self.load_elements(f"document.getElementsByTagName('{tagName}')")
    #
    # def getElementsByName(self, name):
    #     return self.load_elements(f"document.getElementsByName('{name}')")
    #
    # def querySelector(self, selector):
    #     return self.load_elements(f"document.querySelector('{selector}')")
    #
    # def getElementByPythonID(self, PyID):
    #     return self.load_elements(f"document.querySelector('[python_id=\"{PyID}\"]')")

    def run_js_function(self, js, await_result=True, decode_result=True):
        if await_result:
            if decode_result:
                # runs the provided javascript, finds the result and its type, and returns the result
                # To avoid too many communications through the socket channel, all the contents of Array objects will be evaluated and turned into a Python list, even though in JS they're objects

                full_js = f"""(() => {{
    try {{
        let result = ( () => {{ {js} }})();
        return formatJSResult(result);
    }}
    catch (e) {{
        return formatJSResult(e);
    }}
}})();"""
                result = self.js(full_js, await_result=True)
                if result.startswith('"') and result.endswith('"'):
                    result = result[1:-1]
                result = result.replace("\\", "")
                result = eval(result)
                return result
#                 type, result = result[1:-1].split(' ', 1)
# #                print(type, result)
#                 return self.decode_js(js, type, result)
            else:
                return self.js(f"( () => {{ {js} }})()", await_result=True)
        else:
            self.js(js, await_result=False)


    def decode_js(self, statement, type, result):
                if type == "object":
                    return self.get_js_object(result)
                elif type == "array":
                    return eval(result.replace('\\"', '"'))
                elif type == "function":
                    return lambda *args, **kwargs: self.run_js_function(f"{statement}(" + ', '.join([json.dumps(arg) for arg in args]) + ')', await_result=True)
                elif type == "undefined":
                    return None
                elif type == "error":
                    result = result.replace("\\\"", "\"").replace("\\\\n", "\n").replace("\\t", "\t").replace("\\r", "\r").replace("\\\\", "\\")
                    thrown_error = json.loads(result, strict=False)
                    raise FrontendJavascriptError(thrown_error["stack"])
                else:
                    result = result.replace("\\\"", "\"").replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r").replace("\\\\", "\\")
                    try:
                        result = json.loads(result)
                        if type(result) == str:
                            if result.startswith("\"") and result.endswith("\""):
                                result = result[2:-2]
                        return result
                    except:
                        return result


    def get_js_object(self, js_tracker):
        if js_tracker in self.js_objects:
            return self.js_objects[js_tracker]
        else:
            self.js_objects[js_tracker] = JSObject(self, js_tracker)
            return self.js_objects[js_tracker]

    def convert_to_js(self, python_object):
        return encodeJS(python_object, self)
        # if isinstance(python_object, JSObject):
        #     return python_object.javascript_pointer
        # elif callable(python_object):
        #     return self.register_callback(python_object)
        # else:
        #     return json.dumps(python_object)

    def register_callback(self, func):
        self._cb_name_counter_new += 1
        self._cb_functions[self._cb_name_counter_new] = func
        return f"""( (...args) => {{
        let returnArgs = "[";
        for (arg of args) {{
            returnArgs += formatJSResult(arg);
            returnArgs += ", ";
        }}
        returnArgs += "]";
        window.socket.emit("callback", "WindowManager.window_objects[{self.page}]._cb_functions[{self._cb_name_counter_new}](" + returnArgs +  ")");
}} )"""

REMOVEQUOTE = "REMOVEQUOTE"

def encodeJS(statement, window):
    return json.dumps(statement, cls=IntegratedJSONEncoder, window=window).replace('\"'+REMOVEQUOTE, "").replace(REMOVEQUOTE+'\"', "")

class IntegratedJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        self.window = kwargs.pop('window', None)
        super().__init__(*args, **kwargs)

    def default(self, obj):
        if isinstance(obj, JSObject):
            return REMOVEQUOTE + "eval('" + obj.javascript_pointer + "')" + REMOVEQUOTE
        elif isinstance(obj, JSModule):
            return REMOVEQUOTE + "eval('" + obj.base_class_name + "')" + REMOVEQUOTE
        elif callable(obj):
            return REMOVEQUOTE + "eval('" + self.window.register_callback(obj) + "')" + REMOVEQUOTE
        else:
            return super().default(obj)

class JSModule:
    def __init__(self, window, name: str):
        self.window = window
        self.base_class_name = name

    def __call__(self, *args):
        js_arguments = encodeJS(args, self.window)
        js = f"return new {self.base_class_name}(...{js_arguments});"
        created_object = self.window.run_js_function(js, await_result=True, decode_result=True)
        created_object.constructor_name = self.base_class_name
        return created_object



class JSObject:
    reserved_attributes = ["pythonWindow", "javascript_pointer", "reserved_attributes", "constructor_name", "_array_values", "getLiteral"]
    def __init__(self, window, pointer: str, constructor_name=None):
        self.pythonWindow = window
        self.javascript_pointer = pointer
        self.constructor_name = constructor_name
        self._array_values = []

    def __getattribute__(self, item):
        if item in super().__getattribute__("reserved_attributes"):
            return super().__getattribute__(item)
        else:
            return self.pythonWindow.run_js_function(f"""let ret = {self.javascript_pointer}.{item};
if (typeof ret === 'function') {{
            return ret.bind({self.javascript_pointer});
}}
            return ret;""", await_result=True)

    def __setattr__(self, key, value):
        if key in super().__getattribute__("reserved_attributes"):
            super().__setattr__(key, value)
        else:
            if isinstance(value, JSObject):
                self.pythonWindow.run_js_function(f'{self.javascript_pointer}.{key} = ' + value.javascript_pointer, await_result=False)
            elif callable(value):
                self.pythonWindow.run_js_function(f'{self.javascript_pointer}.{key} = ' + self.pythonWindow.register_callback(value), await_result=False)
            else:
                self.pythonWindow.run_js_function(f'{self.javascript_pointer}.{key} = ' + json.dumps(value), await_result=False)

    def __getitem__(self, item):
        return self.pythonWindow.run_js_function(f'return {self.javascript_pointer}[{json.dumps(item)}]', await_result=True)

    def __setitem__(self, key, value):
        self.pythonWindow.run_js_function(f'{self.javascript_pointer}[{json.dumps(key)}] = ' + json.dumps(value), await_result=False)

    def __repr__(self):
        # Doing it this way to avoid loading more objects than necessary
        # if not self.constructor_name:
        #     self.constructor_name = self.pythonWindow.run_js_function(f'return {self.javascript_pointer}.constructor.name', await_result=True)
        # return self.constructor_name
        return "JSObject"

    def __str__(self):
        # if not self.constructor_name:
        #     self.constructor_name = self.pythonWindow.run_js_function(f'return {self.javascript_pointer}.constructor.name', await_result=True)
        # return self.constructor_name
        return "JSObject"

    def __iter__(self):
        # TODO: get all array values at once
        for i in range(len(self)):
            yield self[i]

    def __len__(self):
        return self.pythonWindow.run_js_function(f'return {self.javascript_pointer}.length', await_result=True)

    def getLiteral(self):
        # Uses less socket communication than just getting data normally, but doesn't work for all objects
        return json.loads(self.pythonWindow.js(f"( () => {{return JSON.stringify({self.javascript_pointer}) }})()", await_result=True))
#
# if __name__ == '__main__':
#     html = """<!DOCTYPE html>
#     <html>
#         <head>
#             <link rel="stylesheet" href="./static/handsontable.min.css">
#             <script src="./static/handsontable.min.js"></script>
#             <script src="./static/chart.js"></script>
#             <script src="./static/hammer.js"></script>
#             <script src="./static/chartjs-plugin-zoom.js"></script>
#             <title>Page Title</title>
#         </head>
#         <body>
#             <h1>This is a Heading</h1>
#             <p id="getData">click to get table data</p>
#             <div id="table" style="width: 30vw; height: 75vh; padding: 0px; margin: 0px;"></div>
#             <div id="chart" style="width: 50vw; height: 75vh;">
#                 <canvas id="myChart"></canvas>
#             </div>
#         </body>
#     </html>"""
#     w = PyWindow("Test", html)
#     w.open()
#     w.document.getElementsByTagName('h1')[0].innerHTML = "Hello from Python!"
#
#     parent_element = w.document.getElementsByTagName('div')[0]
#     Handsontable = JSModule(w, "Handsontable")
#     table = Handsontable(parent_element, {'data': None, "rowHeaders":True, "columnHeaders":False, "width": '30vw', "height": '75vh', "licenseKey": "non-commercial-and-evaluation", "columns":[{"type": 'numeric', "format": '0,0.00'}, {"type": 'numeric', "format": '0,0.00'}]})
#     w.document.getElementById('getData').onclick = lambda: print(table.getData().getLiteral())
#
#     Chart = JSModule(w, "Chart")
#     canvas = w.document.getElementById('myChart')
#     chart = Chart(canvas.getContext('2d'), {'type': 'scatter', 'data': {'datasets': [{'label': 'Function', 'data': [], 'backgroundColor': 'rgba(255,99,132,1)', 'borderColor': 'rgba(255,99,132,1)', 'showLine': True, 'pointRadius': 0}, {'label': 'Dataset1', 'data': [], 'backgroundColor': 'rgba(0,0,255,1)', 'borderColor': 'rgba(0,0,255,1)', 'showLine': False}]}, 'options': {'pan': {'enabled': True, 'mode': 'xy', 'speed': 10, 'threshold': 10}, 'maintainAspectRatio': False, 'responsive': True, 'scales': {'x': {'type': 'linear', 'position': 'bottom'}}, 'plugins': {'zoom': {'zoom': {'wheel': {'enabled': True}, 'pinch': {'enabled': False}, 'onZoom': ''}, 'pan': {'enabled': True, 'mode': 'xy', 'speed': 10, 'threshold': 10, 'onPan': lambda *args: print(args[0][0].chart.width)}}, 'legend': {'display': False}}}})
#     chart.data.datasets[0].data = [{'x': 1, 'y': 2}, {'x': 2, 'y': 3}, {'x': 3, 'y': 4}]
#     chart.resetZoom()
#
