var pageId = "";

window.addEventListener('load', function() {
    this.window.trackedObjects = [];
    this.window.trackedFunctions = [];

    const socket = io();

    this.window.socket = socket;

    socket.on('connect', () => {
//        console.log("Connected to server.")
    });

    socket.on('disconnect', () => {
//        console.log("Disconnected from server.");
//        window.open('','_self').close();
//          Try to reconnect to server
        socket.connect();
    });

    socket.on('commands', (msg) => {
        var uuid = msg.slice(0, 36);
        var cmds = msg.slice(36);
//        console.log("Received commands:", cmds);
//        console.log("UUID:", uuid);
        try {
            var result = JSON.stringify(eval(cmds));
           }
        catch (e) {
            console.log("Error while running the following command:\n", cmds);
            console.log(e);
           var result = JSON.stringify(e);
        }
        finally {
//            console.log("Result:", result);
            console.log();
            console.log(cmds);
            console.log(result);
            socket.emit('results', uuid + result);
        }
    });
});

function formatJSResult(result, depth=0) {
    try {
        if (depth > 100) {
            throw new Error('Maximum recursion depth reached.');
        }

//        var result = eval(jsString);
        if (result === null || result === undefined) {
            return 'None'
        }
        var resultType = typeof result;
        if (resultType === 'object') {
            // Eager array evaluation
            // TODO: if big arrays, then could store stringified version and return reference to it
            // if (Array.isArray(result)) {
            //     let ret = 'array [' + result.map(function(x) {
            //         // create a Python-style list containing the contents of the array; if they are objects, should include the constructor to create them via the Python API
            //         let newResultFull = formatJSResult(x, depth + 1).split(' ');
            //         let newResultType = newResultFull[0];
            //         let newResult = newResultFull.slice(1).join(' ');
            //         if (newResultType === 'object') {
            //             return 'self.get_js_object("' + newResult + '")';
            //         }
            //         else {
            //             return newResult;
            //         }
            //     }).join(', ') + ']';
            //     console.log(ret);
            //     return ret;
            // }
            if (window.trackedObjects.includes(result)) {
                // returns a string that can be evaluated to get a Python class that mirrors the JS object
                return 'WindowManager.window_objects[' + pageId + '].get_js_object("window.trackedObjects[' + JSON.stringify(window.trackedObjects.indexOf(result)) + ']")';
            }
            else {
                // same as previous, but for new objects stores them at a permanent location in the trackedObjects array
                return 'WindowManager.window_objects[' + pageId + '].get_js_object("window.trackedObjects[' + JSON.stringify(window.trackedObjects.push(result) - 1) + ']")';
            }
        }
        else if (resultType === 'function') {
            // returns an anonymous python function that calls the JS function with arguments converted from Python to JS
//            return `lambda *args: WindowManager.window_objects[` + pageId + `].run_js_function(f"(` + result.toString().replaceAll('"', '\\"').replaceAll("}", "}}").replaceAll("{", "{{") + `)( {', '.join([WindowManager.window_objects[` + pageId + `].convert_to_js(x) for x in args])} )")`;
            return `lambda *args: WindowManager.window_objects[` + pageId + `].run_js_function(f"return (window.trackedFunctions[` + JSON.stringify(window.trackedFunctions.push(result) - 1) + `])( {', '.join([WindowManager.window_objects[` + pageId + `].convert_to_js(x) for x in args])} )")`;
}
        else {
            // returns a string that can be evaluated to get a Python equivalent of the JS result (i.e. null -> None)
            return 'json.loads(\'' + JSON.stringify(result).replaceAll('"', '\\"') + '\')';
        }
    }
    catch (e) {
        return JSON.stringify(e, Object.getOwnPropertyNames(e));
    }
}



//function formatJSResult(result, depth=0) {
//    try {
//        if (depth > 100) {
//            throw new Error('Maximum recursion depth reached.');
//        }
//
////        var result = eval(jsString);
//        if (result === null) {
//            return 'undefined null'
//        }
//        var resultType = typeof result;
//        if (resultType === 'object') {
//            // Eager array evaluation
//            // TODO: if big arrays, then could store stringified version and return reference to it
//            // if (Array.isArray(result)) {
//            //     let ret = 'array [' + result.map(function(x) {
//            //         // create a Python-style list containing the contents of the array; if they are objects, should include the constructor to create them via the Python API
//            //         let newResultFull = formatJSResult(x, depth + 1).split(' ');
//            //         let newResultType = newResultFull[0];
//            //         let newResult = newResultFull.slice(1).join(' ');
//            //         if (newResultType === 'object') {
//            //             return 'self.get_js_object("' + newResult + '")';
//            //         }
//            //         else {
//            //             return newResult;
//            //         }
//            //     }).join(', ') + ']';
//            //     console.log(ret);
//            //     return ret;
//            // }
//            if (window.trackedObjects.includes(result)) {
//                return 'object window.trackedObjects[' + window.trackedObjects.indexOf(result) + ']';
//            }
//            else {
//                return 'object window.trackedObjects[' + (window.trackedObjects.push(result) - 1) + ']';
//            }
//        }
//        else {
//            return resultType + ' ' + JSON.stringify(result);
//        }
//    }
//    catch (e) {
//        return 'error ' + JSON.stringify(e, Object.getOwnPropertyNames(e));
//    }
//}
