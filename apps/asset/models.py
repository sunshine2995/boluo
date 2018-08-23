
import uuid
from apps.dbinstance import db


class Member_asset_info(db.Model):

    __tablename__ = "tjtyy_member_assets"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    member_id = db.Column(db.GUID, db.ForeignKey("tjtyy_member.id"))
    member_name = db.Column(db.String(128))
    rechargeamount = db.Column(db.Float,nullable=0, default=0)
    remainamount = db.Column(db.Float, nullable=0, default=0)
    freezeamount = db.Column(db.Float, nullable=0, default=0)
    uncollectedamount = db.Column(db.Float, nullable=0, default=0)
    totalamount = db.Column(db.Float, nullable=0, default=0)
    experiamount = db.Column(db.Float, nullable=0, default=0)
    score = db.Column(db.Integer,default=0)
    bluuid = db.Column(db.String(200))
    inveter_profile = db.Column(db.Float, nullable=0, default=0)
    order_id = db.Column(db.String(50))


class Member_recharge_info(db.Model):

    __tablename__ = 'tjtyy_member_recharge'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.GUID, db.ForeignKey("tjtyy_member.id"))
    member_name = db.Column(db.String(128))
    recharge_id = db.Column(db.String(128))
    time = db.Column(db.DateTime)
    is_effect = db.Column(db.Integer)
    money = db.Column(db.Float, nullable=0, default=0)
    type = db.Column(db.String(128))
    equipment = db.Column(db.String(128))
    bangka = db.Column(db.String(128))
    code = db.Column(db.String(128))
    bluuid = db.Column(db.String(200))
    device_info = db.Column(db.String(50))
    channel_id = db.Column(db.String(50))


class Member_reflect_info(db.Model):

    __tablename__ = "tjtyy_member_reflect_info"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.GUID, db.ForeignKey("tjtyy_member.id"))
    member_name = db.Column(db.String(128))
    reflect_id = db.Column(db.String(128))
    money = db.Column(db.Float, nullable=0, default=0)
    fee = db.Column(db.Float,nullable=0, default=0)
    time = db.Column(db.DateTime)
    type = db.Column(db.String(128))
    batchdate = db.Column(db.DateTime)
    batchcurrnum = db.Column(db.String(128))
    reason = db.Column(db.String(128))
    bluuid = db.Column(db.String(200))
    device_info = db.Column(db.String(50))
    channel_id = db.Column(db.String(50))


class Order_dict(db.Model):

    __tablename__ = "tjtyy_hashcode"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20))
    is_use = db.Column(db.Boolean)


class Member_income_statement(db.Model):

    __tablename__ = "tjtyy_user_log"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    member_id = db.Column(db.GUID, db.ForeignKey("tjtyy_member.id"))
    type = db.Column(db.String(128))
    money = db.Column(db.Float)
    balance = db.Column(db.Float)
    time = db.Column(db.DateTime)
    info = db.Column(db.String(128))
    order_id = db.Column(db.String(20))
    product_info = db.Column(db.String(128))
    phone = db.Column(db.String(128))
    bin_order_id = db.Column(db.String(128))


class Member_red_pocket_type(db.Model):

    __tablename__ = "tjtyy_hongbao"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    type = db.Column(db.String(128))
    name = db.Column(db.String(128))
    rules = db.Column(db.String(128))
    validtime = db.Column(db.String(128))
    money = db.Column(db.Float)
    start_money = db.Column(db.Float)
    invest_days = db.Column(db.Float)
    code = db.Column(db.String(24))
    rate = db.Column(db.Float)


class Member_red_pocket(db.Model):

    __tablename__ = "tjtyy_hongbao_info"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.GUID, db.ForeignKey("tjtyy_member.id"))
    is_use = db.Column(db.Integer, nullable=0, default=0)
    sort_id = db.Column(db.GUID, db.ForeignKey("tjtyy_hongbao.id"))
    product_id = db.Column(db.GUID, db.ForeignKey("tjtyy_borrow.id"))
    generate_time = db.Column(db.DateTime)
    is_freeze = db.Column(db.Integer, nullable=0, default=0)
    INSPECTOR = db.Column(db.String(50))
    SEND_TIME = db.Column(db.DateTime)


class Province_city(db.Model):

    __tablename__ = "tjtyy_city"

    id = db.Column(db.Integer, primary_key=True)
    province = db.Column(db.String(128))
    city = db.Column(db.String(128))
    code = db.Column(db.String(128))
