# -*- coding:utf-8 -*-

import uuid
from datetime import datetime
from apps.dbinstance import db


# 活动表
class Zillionaire_info(db.Model):

    __tablename__ = 'tjtyy_activity_zillionaire'

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(32))
    activity_id = db.Column(db.GUID, db.ForeignKey("tjtyy_activity.id"))
    use_number = db.Column(db.Integer,default=0)
    use_number02 = db.Column(db.Integer, default=0)
    investment = db.Column(db.Float,default=0.0)
    integral_total = db.Column(db.Integer,default=0)
    has_friends = db.Column(db.Integer,default=0)
    create_time = db.Column(db.String(128), default=datetime.now())
    prize_id = db.Column(db.String(50), default='0')
    sign_number = db.Column(db.Integer, default=0)
    use_number_max = db.Column(db.Integer, default=0)
    investment02 = db.Column(db.Float,default=0.0)
    pineapple_small = db.Column(db.Integer, default=0)
    pineapple_big = db.Column(db.Integer, default=0)
    national_store = db.Column(db.Float,default=0.0)


# 签到记录表
class Sign_record(db.Model):

    __tablename__ = 'tjtyy_activity_sign_record'

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(32))
    check_time = db.Column(db.String(128))
    check_number = db.Column(db.Integer,default=1)
    integral = db.Column(db.Integer,default=2)


# 会员积分收支表
class Points_change(db.Model):

    __tablename__ = 'tjtyy_activity_points_change'

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(32))
    type = db.Column(db.Integer, default=0)
    num = db.Column(db.Integer, default=0)
    time = db.Column(db.String(128), default=datetime.now())
    score = db.Column(db.Integer, default=0)
    description = db.Column(db.String(128))


# 积分订单表
class Prize_order(db.Model):

    __tablename__ = 'tjtyy_activity_prize_order'

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(32))
    prize_id = db.Column(db.String(32),db.ForeignKey("tjtyy_prize.id"))
    prize_name = db.Column(db.String(128))
    score = db.Column(db.Integer,default=0)
    money = db.Column(db.Float,default=0.0)
    status = db.Column(db.Integer,default=0)
    time = db.Column(db.String(32))
    activity_id = db.Column(db.String(128),db.ForeignKey("tjtyy_activity.id"))
    channel_num = db.Column(db.Integer)


# 商品图片表
class Prize_image(db.Model):

    __tablename__ = 'tjtyy_activity_prize_image'

    id = db.Column(db.Integer, primary_key=True)
    prize_id = db.Column(db.String(32),db.ForeignKey("tjtyy_prize.id"))
    image = db.Column(db.String(256))


# 商品标
class Prize_product(db.Model):

    __tablename__ = 'tjtyy_activity_prize_product'

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(128))
    number = db.Column(db.Integer)# 期号
    remain = db.Column(db.Integer)# 剩余
    total = db.Column(db.Integer)# 总共需要的菠萝
    type = db.Column(db.Integer)
    start_time = db.Column(db.String(128))
    end_time = db.Column(db.String(128))
    location = db.Column(db.Integer)
    issue = db.Column(db.String(128))


# 菠萝投资列表
class Prize_product_invest(db.Model):

    __tablename__ = 'tjtyy_activity_product_invest'

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    phone = db.Column(db.String(128))
    product_number = db.Column(db.String(128))
    number = db.Column(db.Integer)
    is_lucky = db.Column(db.Integer,default=0)
    create_time = db.Column(db.String(128))
    prize = db.Column(db.String(128))
    order_id = db.Column(db.String(128))


class Rank_list(db.Model):

    __tablename__ = 'tjtyy_rank'

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    phone = db.Column(db.String(128))
    money = db.Column(db.Integer)
    is_send = db.Column(db.Float)
    month = db.Column(db.String(128))
    rank = db.Column(db.Integer)


class Integral_record(db.Model):

    __tablename__ = 'tjtyy_integral_record'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.String(28))
    events = db.Column(db.String(28))
    integral = db.Column(db.Integer)
    time = db.Column(db.DateTime)
    activity_id = db.Column(db.String(28))


class Activity_status(db.Model):

    __tablename__ = 'tjtyy_activity_status'

    id = db.Column(db.Integer,primary_key=True)
    member_id = db.Column(db.String(28))
    events = db.Column(db.String(28))
    remain = db.Column(db.Float)
    score = db.Column(db.Integer)
    activity_id = db.Column(db.String(28))


# 抽奖记录表
class Lottery_record(db.Model):

    __tablename__ = 'tjtyy_activity_lottery_log'

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(32))
    activity_id = db.Column(db.String(32))
    lottery_time = db.Column(db.String(128), default=datetime.now())
    lottery_result = db.Column(db.String(255))
    money = db.Column(db.Float, default=0.0)
    type = db.Column(db.Integer, default=0)



