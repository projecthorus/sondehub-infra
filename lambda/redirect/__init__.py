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
        return redirect('https://sondehub.org/#!site=' + site)
    if uri.startswith('/go/donate'):
        return redirect('https://www.paypal.com/donate/?hosted_button_id=4V7L43MD5CQ52')
    if uri.startswith('/go/status'):
        return redirect("https://grafana.v2.sondehub.org/d/bhdBI0KVz/infrastructure")
    if uri.startswith('/go/'):
        tinyurl = uri.replace("/go/", "")
        return redirect('https://tinyurl.com/' + tinyurl)
    if uri != '/':
        uri = re.sub(r"^\/","", uri)
        sonde = re.sub(r'^(DFM|M10|M20|IMET|IMET54|MRZ|LMS6)-',"", uri)
        return redirect('https://sondehub.org/?sondehub=1#!f=' + sonde + '&mz=9&qm=All&q=' + sonde)
    return request