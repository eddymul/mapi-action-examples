from fastapi import HTTPException, FastAPI, Request, Response
import os
import sqlite3
from os.path import isfile

app = FastAPI()
con = sqlite3.connect(':memory:')

import backtracepython as bt

# In dev & testing only, include the stacktrace in the response on internal
# server errors
if os.getenv("FASTAPI_ENV") in ["dev", "test"]:
    @app.exception_handler(Exception)
    async def debug_exception_handler(request: Request, exc: Exception):
        report = bt.BacktraceReport()
        report.set_exception(type(exc), exc, exc.__traceback__)
        for name, value in request.headers.items():
            report.set_attribute(name, value)
        report.send()

        import traceback
        return Response(
            status_code=500,
            content="".join(
                traceback.format_exception(
                    type(exc), exc, exc.__traceback__
                )
            )
        )

@app.on_event("startup")
async def startup_event():
    bt_attributes = {"environment": os.getenv("FASTAPI_ENV"), "serverId": "foo"}
    bt.initialize(
        endpoint="https://submit.backtrace.io/forallsecure/9257d693955bc94e704aeca5a3c697d6eaefc666c307e8998513848de6c0ca96/json",
        token="9257d693955bc94e704aeca5a3c697d6eaefc666c307e8998513848de6c0ca96",
        attributes=bt_attributes,
        #debug_backtrace=True
    )
    bt.send_report("startup event")

    """Creates an in-memory database with a user table, and populate it with
    one account"""
    cur = con.cursor()
    cur.execute('''CREATE TABLE users (email text, password text)''')
    cur.execute('''INSERT INTO users VALUES ('me@me.com', '123456')''')
    con.commit()

@app.get("/")
async def root():
    bt.send_report("root event")
    return {"message": "Hello World"}

@app.get("/login")
async def login(email: str, password: str):
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE email = '%s' and password = '%s'" % (email, password))
    return cur.fetchone() is not None

@app.get("/logout")
async def root(email: str):
    return {"message": "Logged out %s!" % email}

@app.get("/attachment")
async def attachment(attachment_name: str):
    attachment_path = 'attachments/' + attachment_name
    if not isfile(attachment_path):
        raise HTTPException(status_code=404, detail="Attachment not found")

    with open(attachment_path) as f:
        return f.readlines()