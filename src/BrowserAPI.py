import flask
import flask_socketio
from flask import Flask
from flask_socketio import SocketIO
from markupsafe import escape
import platform
import subprocess
from contextlib import suppress
import os, sys, signal
import uuid
import gevent
from gevent.event import Event as gevent_event
import gevent.threading as gthreading
from gevent import monkey, sleep
import json
monkey.patch_all()

# https://stackoverflow.com/questions/54150895/valueerror-invalid-async-mode-specified-when-bundling-a-flask-app-using-cx-fr
from engineio.async_drivers import gevent

# TODO
#    Apple Developer ID
#    Returning event data
#    Handsontable licencing
#    Functions with asymptotes

# Stop Flask spam
# logging.getLogger('werkzeug').disabled = True

SUPPRESS_PRINT = False
if SUPPRESS_PRINT:
    sys.stdout = open(os.devnull, 'w')


OPERATING_SYSTEM = platform.system().lower()
if getattr(sys, 'frozen', False):
    # Running in a bundle
    BASE_DIR = sys._MEIPASS
else:
    # Running in normal Python environment
    PY = sys.executable
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class WindowManager:
    window_objects = {}
    page_number = 0
    browser_path = None

    @classmethod
    def get_new_page_number(cls):
        cls.page_number += 1
        return cls.page_number

    @classmethod
    def maybe_close_app(cls):
        if not cls.window_objects:
            ServerManager.stop()

    @classmethod
    def find_browser(cls):
        if OPERATING_SYSTEM == "windows":
            paths = [
                "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                "C:\Program Files\Google\Chrome\Application\chrome.exe",
                "C:\Program Files\BraveSoftware\Brave-Browser\Application\\brave.exe",
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
            return None
        elif OPERATING_SYSTEM == "linux":
            paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/microsoft-edge-stable",
                "/usr/bin/microsoft-edge",
                "/usr/bin/brave-browser",
            ]
            for path in paths:
                if os.path.exists(path):
                    return path

            for path in paths:
                with suppress(subprocess.CalledProcessError):
                    bp = (
                        subprocess.check_output(["which", path.split("/")[-1]])
                        .decode("utf-8")
                        .strip()
                    )
                    if os.path.exists(bp):
                        return bp

            return None
        elif OPERATING_SYSTEM == "darwin":
            paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                "/Applications/Safari.app/Contents/MacOS/Safari",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
            return None
        return None


    @classmethod
    def open_browser(cls, url, width=None, height=None, fullscreen=False):
        # Open a browser window
#        f"--user-data-dir={profile_dir}",
        if not cls.browser_path:
            cls.browser_path = cls.find_browser()
        flags = [
            cls.browser_path,
            "--new-window",
            "--no-first-run",
        ]
        if width and height:
            flags.extend([f"--window-size={width},{height}"])
        elif fullscreen:
            flags.extend(["--start-maximized"])
        flags.extend([f"--app={url}"])
        subprocess.run(flags, stdout=subprocess.DEVNULL)


class ServerManager:
    page_not_found = "<h1>Looks like there's nothing here...</h1><p>Have you been playing around with the URL?</p><p>Try relaunching the app.</p>"
    is_online = False
    server_thread = None
    request_id_counter = 0

    @classmethod
    def get_free_port(cls):
        import socketserver
        with socketserver.TCPServer(("localhost", 0), None) as s:
            free_port = s.server_address[1]
        return free_port

    @classmethod
    def start(cls):
        if not cls.is_online:
            cls.is_online = True
            print(f"Running on port {PORT}")
#            gthreading.Thread(target=socketio.run, args=(app,), kwargs={"debug": False, "port": PORT}).start()
            cls.server_thread = gthreading.Thread(target=cls._server_thread)
            cls.server_thread.start()

    @classmethod
    def start_on_main_thread(cls):
        if not cls.is_online:
            cls.is_online = True
            print(f"Running on port {PORT}")
            try:
                socketio.run(app, debug=False, port=PORT)
            except (KeyboardInterrupt, SystemExit):
                pass

    @classmethod
    def stop(cls):
        cls.is_online = False
        socketio.stop()

    @classmethod
    def _server_thread(cls):
        try:
            socketio.run(app, debug=False, port=PORT)
        except (KeyboardInterrupt, SystemExit):
            pass

    @classmethod
    def _cleanup(cls, signum, frame):
        cls.stop()
        with suppress(SystemExit):
            sys.exit(0)


app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "static"))
socketio = SocketIO(app)
PORT = ServerManager.get_free_port()

signal.signal(signal.SIGINT, ServerManager._cleanup)
signal.signal(signal.SIGTERM, ServerManager._cleanup)


# This doesn't have to be secure as the only client will be one's own web browser
app.secret_key = "BREAKING NEWS: Man hacks into his own computer by entering the correct password"

@app.route("/")
def handle_default():
    return ServerManager.page_not_found, 404

@app.errorhandler(404)
def not_found(*args, **kwargs):
    return ServerManager.page_not_found, 404

# Route to serve html for Window objects
@app.route("/<int:page>")
def handle(page):
    flask.session["page"] = page
    if page in WindowManager.window_objects:
        window = WindowManager.window_objects[page]
        result = window.serve_html()
        if result:
            return result
    return ServerManager.page_not_found, 404


@socketio.on("connect")
def handle_connect():
    if "page" in flask.session:
        window = WindowManager.window_objects[flask.session['page']]
        if window.on_socket_connect():
            flask_socketio.join_room(str(flask.session['page']))
            # print(f"Client connected: {flask.session['page']}")


@socketio.on("disconnect")
def handle_disconnect():
    if "page" in flask.session:
#        print(f"Client disconnected: {flask.session['page']}")
        window = WindowManager.window_objects[flask.session['page']]
        window.on_socket_disconnect()



@socketio.on("results")
def handle_response(data):
#    print("Received response from client")
    if "page" in flask.session:
        window = WindowManager.window_objects[flask.session['page']]
        conversation_uuid = data[:36]
        result = data[36:]
        if conversation_uuid in window.js_result_events:
            window.js_results[conversation_uuid] = result
            window.js_result_events[conversation_uuid].set()

@socketio.on("callbackOld")
def handle_callback(data):
    if "page" in flask.session:
        window = WindowManager.window_objects[flask.session['page']]
        if data in window.frontend_callbacks:
            window.frontend_callbacks[data.replace("'", "")]()

@socketio.on("callback")
def handle_callback(data):
    # I'm a little fed up with Electron-like restrictions; this is not secure, but the only thing you'll be able to hack into is your own computer
    # print(data)
    return exec(data)

# JS to include: <script type='text/javascript' src='/static/PyBrowserAPI/socketio.min.js'></script>
#                <script type='text/javascript' src='/static/PyBrowserAPI/clientsocketmanager.js'></script>

class Window:
    def __init__(self, name, html, height=None, width=None, fullscreen=False, included_scripts=[]):
        if 'static/PyBrowserAPI/clientsocketmanager.js' not in html:
            if '<head>' in html:
                html = html.replace('<head>', f"<head><script type='text/javascript' src='static/socketio.min.js'></script><script type='text/javascript' src='/static/clientsocketmanager.js'></script>")
            else:
                html = f"<head><script type='text/javascript' src='static/socketio.min.js'></script><script type='text/javascript' src='/static/clientsocketmanager.js'></script></head>{html}"
        included_scripts.reverse()
        for script in included_scripts:
            if script not in html:
                html = html.replace('<head>', f"<head><script src='{script}'></script>")
        self.name = name
        self.html = html
        self.page = WindowManager.get_new_page_number()
        self.has_served_html = False
        self.connection_complete = False
        self.has_closed = False
        self.height = height
        self.width = width
        self.fullscreen = fullscreen
        self.frontend_callbacks = {}
        self._cb_name_counter = 0
        self.js_result_events = {}
        self.js_results = {}

        WindowManager.window_objects[self.page] = self

    def open(self):

        # if the backend isn't on yet, start it
        if not ServerManager.is_online:
            ServerManager.start()

        # open the browser window
        WindowManager.open_browser(f"http://127.0.0.1:{PORT}/{str(self.page)}", self.width, self.height, self.fullscreen)
#        subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--new-window",
#                        f"--app=http://127.0.0.1:{PORT}/{self.page}"])
        # Wait until everything is connected
        self.when_ready = gevent_event()
        self.when_ready.wait()

    def open_on_main_thread(self):
        # if the backend isn't on yet, start it
        if not ServerManager.is_online:
            ServerManager.start_on_main_thread()


    def serve_html(self):
        # When the frontend page is opened, it will request its HTML from this function
        # With current configuration, only one frontend window can be opened
        if self.has_closed:
            return False
        if not self.has_served_html:
            self.has_served_html = True
            return self.html

    def on_socket_connect(self):
        # Once the frontend page has loaded its content from the server, it will ask the server to connect via WebSocket
        # This function will tell the WebSocket server to accept the connection
        if self.has_closed:
            return False
        if self.connection_complete or not self.has_served_html:
            return False
        self.connection_complete = True
        self.when_ready.set()
        return True

    def on_socket_disconnect(self):
        # When the frontend page is closed, it will disconnect from the server
        self.has_closed = True
        WindowManager.window_objects.pop(self.page, None)
        WindowManager.maybe_close_app()

    def kill(self):
        pass

    def js(self, js, await_result=True):
        if not self.has_closed and self.connection_complete:
            if not await_result:
                self.js_result_event = None
#            print("Sending command to client")
            conversation_uuid = str(uuid.uuid4())
            socketio.emit("commands", conversation_uuid + js, room=str(self.page))
            if await_result:
                self.js_result_events[conversation_uuid] = gevent_event()
                self.js_result_events[conversation_uuid].wait()
                del self.js_result_events[conversation_uuid]
                ret = self.js_results.pop(conversation_uuid, None)
                return ret

    def register_callback(self, callback):
        self._cb_name_counter += 1
        self.frontend_callbacks[str(self._cb_name_counter)] = callback
        return f"() => {{socket.emit('callbackOld', '{self._cb_name_counter}')}}"


# if __name__ == '__main__':
#     window = Window("Test", "<h1>Test</h1><p>Test</p>")
#     # window.open()
#     window.open_on_main_thread()