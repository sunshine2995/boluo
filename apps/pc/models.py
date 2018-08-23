# -*- coding: UTF-8 -*-

import uuid
from apps.dbinstance import db


class Prize(db.Model):

    __tablename__ = "tjtyy_member_prize"

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(128))
    prize_id = db.Column(db.String(128), db.ForeignKey("tjtyy_prize.id"))
    time = db.Column(db.DateTime)
    is_grant = db.Column(db.Integer, nullable=0, default=0)
    activity_id = db.Column(db.String(128), db.ForeignKey("tjtyy_activity.id"))


class PrizeType(db.Model):

    __tablename__ = "tjtyy_prize"

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(128))
    hongbao_id = db.Column(db.String(128), db.ForeignKey("tjtyy_hongbao.id"))
    ptype = db.Column(db.String(128))
    money = db.Column(db.Float)
    sort = db.Column(db.Integer)
    status = db.Column(db.Integer)
    valid_desc = db.Column(db.String(256))
    deadline = db.Column(db.String(256))
    input_time = db.Column(db.String(256))
    score = db.Column(db.Integer)
    stock = db.Column(db.Integer)
    description = db.Column(db.String(256))
    probability = db.Column(db.Float)
    dice = db.Column(db.String(256))
    exchange_process = db.Column(db.String(1024))
    introduce = db.Column(db.String(256))


class Activity(db.Model):

    __tablename__ = "tjtyy_activity"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(128))
    end_time = db.Column(db.DateTime)
    start_time = db.Column(db.DateTime)
    prize_ids = db.Column(db.String(1024))
    default_num = db.Column(db.Integer, nullable=1, default=1)


class PrizeShare(db.Model):

   __tablename__ = "tjtyy_prize_num"

   id = db.Column(db.Integer, primary_key=True)
   phone = db.Column(db.String(128))
   is_share = db.Column(db.Integer, nullable=0, default=0)
   total_num = db.Column(db.Integer, nullable=1, default=1)
   activity_id = db.Column(db.String(128), db.ForeignKey("tjtyy_activity.id"))
