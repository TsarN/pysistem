# -*- coding: utf-8 -*-
from flask import g, request, jsonify
from pysistem import app
from functools import wraps

apires = jsonify

def fieldify(arg='fields', default=None, allowed=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            fields = kwargs.get(arg, default or [])
            if allowed:
                for field in fields:
                    if field not in allowed:
                        return apires({
                            "error": -2,
                            "message": "No such field: %s" % field
                        }, 404)
            raw = f(*args, **kwargs)
            result = []
            if type(raw) is not list:
                raw = [raw]
            for record in raw:
                res = {}
                for field in fields:
                    res[field] = record[field]
                result.append(res)
            if len(result) == 1:
                result = result[0]
            else:
                result = {
                    "count": len(result),
                    "result": result
                }
            return apires(result)
        return decorated_function
    return decorator

_api_loaded = True

from pysistem.users.api import api as users_api
app.register_blueprint(users_api)