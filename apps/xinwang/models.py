# -*- coding:utf-8 -*-

import uuid
from datetime import datetime
from apps.dbinstance import db


# 回调信息记录表
class CallbackInformation(db.Model):

    __tablename__ = 'tjtyy_callback_information'

    id = db.Column(db.Integer, primary_key=True)
    requestNo = db.Column(db.String(100))
    code = db.Column(db.Integer, default=0)
    type = db.Column(db.Integer, default=0)
    status = db.Column(db.String(32), default="")
    phone = db.Column(db.String(32), default="")
    errorCode = db.Column(db.String(32), default="")
    errorMessage = db.Column(db.String(200), default="")
    accessType = db.Column(db.String(32), default="")
    create_time = db.Column(db.String(128), default=datetime.now)


