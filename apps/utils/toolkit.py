#!/use/bin/env python
# -*- coding: UTF-8 -*-


import base64
import functools
import json
import flask
import datetime
from uuid import UUID
from sqlalchemy.ext.declarative import DeclarativeMeta

def response(data=None, code=200, headers=None, raw=False):
    if data is None:
        data = True
    h = {
        'Cache-Control': 'no-cache',
        'Expires': '-1',
        'Content-Type': 'application/json'
    }
    if headers:
        h.update(headers)

    if h['Cache-Control'] == 'no-cache':
        h['Pragma'] = 'no-cache'

    try:
        if raw is False:
            data = json.dumps(data, sort_keys=True, skipkeys=True)
    except TypeError:
        data = str(data)
    return flask.current_app.make_response((json.dumps(data,sort_keys=True,
                                                       indent=4,separators=(',',":"), skipkeys=True), code, h))

def json_optimizer(content):
    def optimizer(dict):
        for key, value in zip(dict.keys(), dict.values()):
            dict[key] = str(value) if value is not None else ''
    try:
        if isinstance(content,dict):
            optimizer(content)
        elif isinstance(content,list):
            for theElementOfDict in content:
                optimizer(theElementOfDict)
    except:
        pass
    return content


def get_remote_ip():
    if 'X-Forwarded-For' in flask.request.headers:
        return flask.request.headers.getlist('X-Forwarded-For')[0]
    if 'X-Real-Ip' in flask.request.headers:
        return flask.request.headers.getlist('X-Real-Ip')[0]
    return flask.request.remote_addr


def api_error(message, code=400, headers=None):
    return response({'error': message}, code, headers)

def check_auth_header():
    auth = flask.request.headers.get('authorization', '')
    auth_str = None
    auth_info = None
    if auth:
        try:
            # parse the auth, for http protocal, it is base64 code.
            # the auth_str is the namespace of repository too.
            auth_str = base64.decodestring(auth.split(" ")[1]).split(":")[0]
            auth_info = {"repository": auth_str}
        except:
            pass
    return auth_info

def requires_auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if check_auth_header() is True:
            return f(*args, **kwargs)
        headers = {'WWW-Authenticate': 'Token'}
        return api_error('Requires authorization', 401, headers)
    return wrapper


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, UUID):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)

class AlchemyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    json.dumps(data)
                    fields[field] = data
                except TypeError:
                    if isinstance(data, UUID):
                        fields[field] = str(data)
                    elif isinstance(data, datetime.datetime):
                        fields[field] = data.isoformat()
                    elif isinstance(data, datetime.date):
                        fields[field] = data.isoformat()
                    elif isinstance(data, datetime.timedelta):
                        fields[field] = (datetime.datetime.min + data).time().isoformat()
                    else:
                        fields[field] = None
            return fields

        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S') 
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, UUID):
            return str(obj)

        return json.JSONEncoder.default(self, obj)


def query_result_to_json(query_result):
    if isinstance(query_result, list):
        return json.dumps(query_result,cls=AlchemyEncoder, sort_keys=True,indent=4,separators=(',',":"))
    return "False"


def query_result_to_dict(query_result):
    if isinstance(query_result, list):
        return json.dumps(query_result,cls=AlchemyEncoder, sort_keys=True,indent=4,separators=(',',":"))
    return None


def obj_to_json(obj_list):
    out = [q.__dict__ for q in obj_list]
    for objs, instance in zip(out, obj_list):
        for obj in objs.values():
            if isinstance(obj, UUID):
                obj=str(obj)
            if callable(obj):
                for name in obj.mapper.relationships.keys():
                    tmp = getattr(instance, name).__dict__
                    if "_sa_instance_state" in tmp.keys():
                        tmp.pop("_sa_instance_state")
                        tmp.pop("id")
                        objs.update(tmp)
                    objs.pop(name)
        if "_sa_instance_state" in objs.keys():
            objs.pop("_sa_instance_state")
    return out


def query_result_json(query_result):
    """
    Convert query result to json format
    """
    if isinstance(query_result, list):
        result = obj_to_json(query_result)
    elif getattr(query_result, '__dict__', ''):
        result = obj_to_json([query_result])
    else:
        result = {'result': query_result}
    return json.dumps(result, cls=ComplexEncoder, sort_keys=True,indent=4,separators=(',',":"))



