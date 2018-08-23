#!/use/bin/env python
# -*- coding: UTF-8 -*-
from functools import wraps
from flask import request
from apps.member.models import Member_login
from apps.utils import toolkit
import datetime



def login_token(func):
    @wraps(func)
    def _deco(*args, **kwargs):
        response_data = {}
        lt = request.headers.get('LoginToken', None)
        ml = Member_login.query.filter_by(login_token=lt).first()
        if lt and ml and ml.over_time:
            now = datetime.datetime.now()
            if now > ml.over_time:
                response_data["code"] = '10077'
                response_data["desc"] = u"请重新登录"
                return toolkit.response(response_data, 200, None, True)
        else:
            response_data["code"] = '10077'
            response_data["desc"] = u"请重新登录"
            return toolkit.response(response_data, 200, None, True)
        ret = func(*args, **kwargs)
        return ret
    return _deco