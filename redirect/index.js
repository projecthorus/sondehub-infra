'use strict';

exports.handler = (event, context, callback) => {
    /*
     * Generate HTTP redirect response with 302 status code and Location header.
     */
    const request = event.Records[0].cf.request;
    if (request.uri.startsWith('/aprs/')) {
        var sonde = request.uri.replace(/^\/aprs\//, "");
        var specific_response = {
            status: '302',
            statusDescription: 'Found',
            headers: {
                location: [{
                    key: 'Location',
                    value: 'https://aprs.fi/#!call=' + sonde + '&timerange=36000&tail=36000'
                }],
            },
        };
        callback(null, specific_response);
        return;
    }
    if (request.uri.startsWith('/site/')) {
        var site = request.uri.replace(/^\/site\//, "");
        var specific_response = {
            status: '302',
            statusDescription: 'Found',
            headers: {
                location: [{
                    key: 'Location',
                    value: 'https://sondehub.org/#!site=' + site
                }],
            },
        };
        callback(null, specific_response);
        return;
    }
    if (request.uri.startsWith('/go/')) {
        var name = request.uri.replace(/^\/go\//, "");
        if (name == "donate") {
            var specific_response = {
                status: '302',
                statusDescription: 'Found',
                headers: {
                    location: [{
                        key: 'Location',
                        value: 'https://www.paypal.com/donate?business=YK2WHT6RNSYH8&item_name=SondeHub+Database+funding&currency_code=USD'
                    }],
                },
            };
            callback(null, specific_response);
            return;
        }
        if (name == "status") {
            var specific_response = {
                status: '302',
                statusDescription: 'Found',
                headers: {
                    location: [{
                        key: 'Location',
                        value: 'https://cloudwatch.amazonaws.com/dashboard.html?dashboard=SondeHub&context=eyJSIjoidXMtZWFzdC0xIiwiRCI6ImN3LWRiLTE0Mzg0MTk0MTc3MyIsIlUiOiJ1cy1lYXN0LTFfZ2NlT3hwUnp0IiwiQyI6IjNuOWV0Y2ZxZm9zdm11aTc0NTYwMWFzajVzIiwiSSI6InVzLWVhc3QtMTo0ODI5YmQ4MC0yZmYzLTQ0MDktYjI1ZS0yOTE4MTM5YTgwM2MiLCJNIjoiUHVibGljIn0%3D'
                    }],
                },
            };
            callback(null, specific_response);
            return;
        }
        var specific_response = {
            status: '302',
            statusDescription: 'Found',
            headers: {
                location: [{
                    key: 'Location',
                    value: 'https://tinyurl.com/' + name
                }],
            },
        };
        callback(null, specific_response);
        return;
    }
    if (request.uri !== '/') {
        var sonde = request.uri.replace(/^\//, "").replace(/^(DFM|M10|M20|IMET|IMET54|MRZ|LMS6)-/, "");
        var specific_response = {
            status: '302',
            statusDescription: 'Found',
            headers: {
                location: [{
                    key: 'Location',
                    value: 'https://sondehub.org/?sondehub=1#!f=' + sonde + '&mz=9&qm=All&q=' + sonde
                }],
            },
        };
        callback(null, specific_response);
        return;
    }

    if (request.querystring !== '' && request.querystring !== undefined) {
        // do not process if this is not an A-B test request
        callback(null, request);
        return;
    }
    callback(null, request);
};
