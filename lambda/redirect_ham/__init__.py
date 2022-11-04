import re
def redirect(location):
    return {
            "status": '302',
            "statusDescription": 'Found',
            "headers": {
                "location": [{
                    "key": 'Location',
                    "value": location
                }],
            },
        }

def handler(event, context):
    request = event["Records"][0]["cf"]["request"]
    uri = request["uri"]
    if  uri.startswith('/aprs/'):
        sonde = uri.replace("/aprs/","")
        return redirect('https://aprs.fi/#!call=' + sonde + '&timerange=36000&tail=36000')
    if uri.startswith('/site/'): 
        site = uri.replace("/site/", "")
        return redirect('https://amateur.sondehub.org/#!site=' + site)
    if uri.startswith('/go/donate'):
        return redirect('https://www.paypal.com/donate/?hosted_button_id=4V7L43MD5CQ52')
    if uri.startswith('/go/status'):
        return redirect("https://cloudwatch.amazonaws.com/dashboard.html?dashboard=SondeHub&context=eyJSIjoidXMtZWFzdC0xIiwiRCI6ImN3LWRiLTE0Mzg0MTk0MTc3MyIsIlUiOiJ1cy1lYXN0LTFfZ2NlT3hwUnp0IiwiQyI6IjNuOWV0Y2ZxZm9zdm11aTc0NTYwMWFzajVzIiwiSSI6InVzLWVhc3QtMTo0ODI5YmQ4MC0yZmYzLTQ0MDktYjI1ZS0yOTE4MTM5YTgwM2MiLCJNIjoiUHVibGljIn0%3D")
    if uri != '/':
        uri = re.sub(r"^\/","", uri)
        return redirect('https://amateur.sondehub.org/?sondehub=1#!f=' + sonde + '&mz=9&qm=All&q=' + sonde)
    return request