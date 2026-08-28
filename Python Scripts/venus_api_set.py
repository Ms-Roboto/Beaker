"""
venus_api_set.py — Set variables on a remote VENUS instance and optionally resume it.

Usage:
    python venus_api_set.py <host> <name1=value1> [name2=value2 ...] [--resume]

Examples:
    python venus_api_set.py 128.137.123.66 GV_str_command=open_door --resume
    python venus_api_set.py 128.137.123.66 GV_str_command=close_and_read GV_str_protocol=6pw_test.prt GV_str_plate_type="COSTAR_6 well- Gen ID" GV_str_plate_barcode=BC001 --resume

Exit codes: 0 = success, 1 = failure
"""

import sys
import time
import json

HTTP_RETRIES = 3
HTTP_RETRY_DELAY = 5

try:
    import requests
except ImportError:
    import urllib.request
    import urllib.error

    class SimpleRequests:
        class Response:
            def __init__(self, data, status):
                self.text = data
                self.status_code = status
                self.ok = 200 <= status < 300

        def _call(self, method, url, json_data=None):
            headers = {"Content-Type": "application/json"}
            body = json.dumps(json_data).encode() if json_data else None
            for attempt in range(HTTP_RETRIES):
                req = urllib.request.Request(url, data=body, headers=headers, method=method)
                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        return self.Response(resp.read().decode(), resp.status)
                except urllib.error.HTTPError as e:
                    return self.Response(e.read().decode(), e.code)
                except (urllib.error.URLError, OSError) as e:
                    if attempt < HTTP_RETRIES - 1:
                        print("HTTP retry {}/{}: {}".format(attempt + 1, HTTP_RETRIES, e))
                        time.sleep(HTTP_RETRY_DELAY)
                    else:
                        return self.Response(str(e), 0)

        def put(self, url, json=None):
            return self._call("PUT", url, json)
        def post(self, url, json=None):
            return self._call("POST", url, json)

    requests = SimpleRequests()


def _http(fn):
    exc = None
    for i in range(HTTP_RETRIES):
        try:
            return fn()
        except Exception as e:
            exc = e
            if i < HTTP_RETRIES - 1:
                print("HTTP retry {}/{}: {}".format(i + 1, HTTP_RETRIES, e))
                time.sleep(HTTP_RETRY_DELAY)
    raise exc


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    host = sys.argv[1]
    port = "51745"
    api = "http://{}:{}/api/v1/vector".format(host, port)

    do_resume = "--resume" in sys.argv
    pairs = [a for a in sys.argv[2:] if a != "--resume"]

    names = []
    values = []
    for pair in pairs:
        n, v = pair.split("=", 1)
        names.append(n)
        values.append(v)

    # Set variables
    try:
        r = _http(lambda: requests.put("{}/execution/input".format(api), json={
            "variableNames": names,
            "variableValues": values
        }))
    except Exception as e:
        print("ERROR set connection: {}".format(e))
        sys.exit(1)
    if not r.ok:
        print("ERROR set: {} {}".format(r.status_code, r.text))
        sys.exit(1)

    # Resume if requested
    if do_resume:
        try:
            r = _http(lambda: requests.post("{}/execution/resume".format(api)))
        except Exception as e:
            print("ERROR resume connection: {}".format(e))
            sys.exit(1)
        if not r.ok:
            print("ERROR resume: {} {}".format(r.status_code, r.text))
            sys.exit(1)

    sys.exit(0)
