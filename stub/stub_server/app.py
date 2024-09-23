import json
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from stub_server.models import AuthModel


app = FastAPI()
tz = ZoneInfo("Asia/Yekaterinburg")


def spin(chance: int) -> bool:
    r = random.randint(1, 100)
    return r <= chance


def read_json(path):
    with open(path, 'r') as f:
        return json.load(f)


latch_messages = read_json('latch_messages.json')


@app.post('/api2/auth/open')
def auth(data: AuthModel):
    if data.login == 'admin@example.com' and data.password == 'Jb21uHa73omYia':
        return JSONResponse({"token": "5XZI6I7I_Erge7sJy2s19PzqksYGvkMU"})
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@app.get('/api2/company')
def get_company_list():
    return JSONResponse([
        {
            "id": 179,
            "name": "ГУ ОГАЧО"
        }
    ])


@app.get('/api2/company/objects')
def get_objects(id: int):
    return JSONResponse(read_json('company-objects.json'))


@app.get('/api2/device/limit-log')
def get_limit_logs(id: int, start_dt: datetime, end_dt: datetime):
    if id == 88584 or id == 88698:
        return JSONResponse([
            {
                "limit_id": random.randint(10000, 100000),
                "latch_dt": datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S"),
                "latch_message": latch_messages[random.randint(0, len(latch_messages) - 1)]
            }
        ])

    return JSONResponse([])


@app.get('/api2/object')
def get_device_list(id: int):
    return JSONResponse(read_json('device-list.json'))


@app.get('/api2/device/values')
def get_device_values(id: int):
    return JSONResponse(read_json('device-values.json'))

