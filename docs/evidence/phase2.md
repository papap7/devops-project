# Phase 2 evidence: containerize the Flask app

**Status:** in progress. This file covers the app running locally on my Mac. The container, the test and the VM run are added as I do them.

**Date started:** 2026-11-06 | **Host:** Mac (Apple Silicon), Python 3.15.2, Flask 3.1.3

**Built from:** `app/app.py` at commit `fb4f6de`

---

## 1. App runs locally and answers on `/`

**Claim:** the Flask app starts and `/` returns 200 with valid HTML.

**Command:**
```
flask --app app/app:app run
curl -i http://127.0.0.1:5000/
```

**Output:**
```
(.venv) jhonpaulotenorio@Paulos-MacBook-Air devops-project % curl -i http://127.0.0.1:5000/      
HTTP/1.1 200 OK
Server: Werkzeug/3.1.9 Python/3.15.2
Date: Fri, 06 Nov 2026 01:05:18 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 19
Connection: close

<p>Hello World!</p>%
```

## 2. `/health`

**Claim:** `/health` returns 200 with a JSON body a script can read.

**Command:**
```
curl -i http://127.0.0.1:5000/health
```

**Output:**
```
HTTP/1.1 200 OK
Server: Werkzeug/3.1.9 Python/3.15.2
Date: Fri, 06 Nov 2026 00:03:01 GMT
Content-Type: application/json
Content-Length: 16
Connection: close

{"status":"ok"}
```

**Notes:** the development server is only used here. The container will use gunicorn.

## 3. `/version` when `COMMIT_SHA` is not set

**Claim:** `/version` returns a placeholder instead of crashing.

**Command:**
```
curl -i http://127.0.0.1:5000/version
```

**Output:**
```
HTTP/1.1 200 OK
Server: Werkzeug/3.1.9 Python/3.15.2
Date: Fri, 06 Nov 2026 00:39:38 GMT
Content-Type: application/json
Content-Length: 22
Connection: close

{"version":"unknown"}
```

**Notes:** `os.environ.get("COMMIT_SHA", "unknown")`. It stays 200 because the request succeeded; the deploy script (Phase 4) compares the value with the expected SHA, so `unknown` makes that check fail.

## 4. `/version` when `COMMIT_SHA` is set

**Claim:** `/version` returns the value of the environment variable.

**Command:**
```
COMMIT_SHA=63ceba5 flask --app app/app:app run
curl -i http://127.0.0.1:5000/version
```

**Output:**
```
HTTP/1.1 200 OK
Server: Werkzeug/3.1.9 Python/3.15.2
Date: Fri, 06 Nov 2026 01:18:19 GMT
Content-Type: application/json
Content-Length: 22
Connection: close

{"version":"63ceba5"}
```

**Notes:** the variable is set for that one server process only. `63ceba5` is a real commit of this repo, used as a realistic test value. After stopping the server and starting it again without the variable, the same `curl -i` returned `{"version":"unknown"}` (section 3), so the value comes from the environment and not from the code. `echo $COMMIT_SHA` printed nothing, which confirms the variable is not set in my shell.
