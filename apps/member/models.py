#!/use/bin/env python
# -*- coding: UTF-8 -*-

import uuid

from apps.dbinstance import db
from itsdangerous import (TimedJSONWebSignatureSerializer
                         as Serializer, BadSignature, SignatureExpired)
from passlib.apps import custom_app_context as pwd_context
SECRET_KEY = 'the quick brown fox jumps over the lazy dog'

#this is all the table and data structure relate to member

class Member(db.Model):

    __tablename__ = 'tjtyy_member'

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(128))
    passwd = db.Column(db.String(256))
    pay_passwd = db.Column(db.String(256))
    phone = db.Column(db.String(128))
    reg_ip = db.Column(db.String(128))
    reg_time = db.Column(db.DateTime)
    is_email_bind = db.Column(db.Integer, nullable=0, default=0)
    is_pay_bind = db.Column(db.Integer, nullable=0, default=0)
    is_identity_bind = db.Column(db.Integer, nullable=0, default=0)
    is_activate = db.Column(db.Integer, default=1)
    level = db.Column(db.Integer, nullable=1, default=0)
    invitation_code = db.Column(db.String(5))
    qrcode = db.Column(db.String(128))
    sign = db.Column(db.String(128))
    channel_id = db.Column(db.String(50))
    device_info = db.Column(db.String(50))
    token = db.Column(db.String(50))
    login_time = db.Column(db.DateTime)
    logs = db.relationship("Member_log", backref="tjtyy_member", lazy="dynamic")
    pay_info = db.relationship('Member_pay_info',backref="tjtyy_member", uselist=False)
    real_info = db.relationship('Member_real_info', backref="tjtyy_member", uselist=False)
    invest_infos = db.relationship('Invest_info', backref='tjtyy_member', lazy='dynamic')
    bluuid = db.Column(db.String(200))
    isblack = db.Column(db.String(128))
    touxiang_image = db.Column(db.String(128))
    fxpinggu = db.Column(db.String(128))
    is_register_xinwang = db.Column(db.Integer, nullable=0, default=0)
    xinwang_create_time = db.Column(db.DateTime)
    userRole = db.Column(db.String(64))
    userType = db.Column(db.String(4))
    isImportUserActivate = db.Column(db.String(4))



    def hash_pay_password(self, pay_password):
        self.pay_passwd = pwd_context.encrypt(pay_password)

    def verify_pay_password(self, pay_password):
        return pwd_context.verify(pay_password, self.pay_passwd)

    def hash_password(self, password):
        self.passwd = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.passwd)

    def generate_auth_token(self, expiration=1440):
        s = Serializer(SECRET_KEY, expires_in=expiration)
        return s.dumps({'id': str(self.id)})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(SECRET_KEY)
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None    # valid token, but expired
        except BadSignature:
            return None    # invalid token
        m = Member.query.get(data['id'])
        return m

    @classmethod
    def get_member_id(cls, phone):
        member = cls.query.filter_by(phone=phone).first()
        if member:
            return str(member.id).replace('-', '')
        else:
            return ''


class Member_login(db.Model):

    __tablename__ = 'tjtyy_member_login'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.GUID, db.ForeignKey(Member.id))
    member_name = db.Column(db.String(128))
    login_times = db.Column(db.Integer)
    last_ip = db.Column(db.String(128))
    last_time = db.Column(db.String(128))
    up_ip = db.Column(db.String(128))
    up_time = db.Column(db.String(128))
    equipment_name = db.Column(db.String(128))
    equipment_token = db.Column(db.String(128), default='123456789')
    login_token = db.Column(db.String(128))
    isblack = db.Column(db.String(128))
    over_time = db.Column(db.String(128))
    is_hdimg = db.Column(db.Integer, default=0)


class Member_log(db.Model):

    __tablename__ = 'tjtyy_member_log'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("tjtyy_member.id"))
    log_ip = db.Column(db.String(128))
    log_time = db.Column(db.String(128))
    log_event = db.Column(db.String(128))
    log_result = db.Column(db.String(128))


class Member_pay_info(db.Model):

    __tablename__ = "tjtyy_member_pay_info"

    id=db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    member_id = db.Column(db.GUID, db.ForeignKey("tjtyy_member.id"))
    pay_bankcard=db.Column(db.String(128))
    account_holder = db.Column(db.String(128))
    bank_name = db.Column(db.String(128))
    bank_deposit = db.Column(db.String(128))
    bank_address = db.Column(db.String(128))
    bank_code = db.Column(db.String(128))
    phone = db.Column(db.String(16))
    card_type = db.Column(db.String(16))
    province = db.Column(db.String(128))
    city = db.Column(db.String(128))
    sort = db.Column(db.Integer,nullable=0, default=0)
    single_amt = db.Column(db.String(128))
    day_amt = db.Column(db.String(128))
    month_amt = db.Column(db.String(128))


class Member_bank_logo(db.Model):

    __tablename__ = "tjtyy_bank_logo"

    id = db.Column(db.GUID, primary_key=True,default=uuid.uuid4)
    bank = db.Column(db.String(128))
    logo = db.Column(db.String(128))
    sign = db.Column(db.String(1))
    bank_code = db.Column(db.String(32))
    single_amt = db.Column(db.String(128))
    day_amt = db.Column(db.String(128))
    month_amt = db.Column(db.String(128))
    bank_code2 = db.Column(db.String(32))  # 新网bank_code



class Member_real_info(db.Model):

    __tablename__ = "tjtyy_member_real_info"

    id=db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    member_id = db.Column(db.GUID, db.ForeignKey("tjtyy_member.id"))
    real_name = db.Column(db.String(128))
    real_identid = db.Column(db.String(128))
    real_idcar_image = db.Column(db.String(128))
    address = db.Column(db.String(128))
    sex = db.Column(db.String(1))
    birthday = db.Column(db.String(10))
    create_time = db.Column(db.String(128))
    people_name = db.Column(db.String(50))
    people_phone = db.Column(db.String(20))
    people_address= db.Column(db.String(200))


class Member_email_info(db.Model):

    __tablename__ = "tjtyy_member_email"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    member_id = db.Column(db.GUID, db.ForeignKey("tjtyy_member.id"))
    email = db.Column(db.String(128))


class Message_code(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.String(128))
    phone = db.Column(db.String(128))
    verify_code = db.Column(db.String(10))
    create_time = db.Column(db.DateTime)


class Member_invite(db.Model):
    __tablename__ = "tjtyy_invite"

    id = db.Column(db.Integer, primary_key=True)
    invitation_code = db.Column(db.String(5))
    is_use = db.Column(db.Integer)


class Member_bussnes(db.Model):
    __tablename__ = "tjtyy_business"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    business_name = db.Column(db.String(128))
    linkman = db.Column(db.String(128))
    phone = db.Column(db.String(128))
    linkman_post = db.Column(db.String(128))
    money = db.Column(db.Integer)
    cycle = db.Column(db.Integer)
    content = db.Column(db.String(128))


class Member_invite_info(db.Model):

    __tablename__ = "tjtyy_invite_info"

    id = db.Column(db.Integer, primary_key=True)
    inviter_id = db.Column(db.GUID, db.ForeignKey("tjtyy_member.id"))
    invited_id = db.Column(db.GUID, db.ForeignKey("tjtyy_member.id"))
    sign = db.Column(db.Integer, nullable=0, default=0)
    inviter_time = db.Column(db.DateTime)
    is_invest = db.Column(db.Integer, nullable=0, default=0)


class Member_invite_profit(db.Model):

    __tablename__ = "tjtyy_invite_profit"

    id = db.Column(db.Integer, primary_key=True)
    inviter_id = db.Column(db.GUID, db.ForeignKey("tjtyy_member.id"))
    invited_id = db.Column(db.GUID, db.ForeignKey("tjtyy_member.id"))
    order_id = db.Column(db.GUID, db.ForeignKey("tjtyy_invest_info.id"))
    product_id = db.Column(db.GUID, db.ForeignKey("tjtyy_borrow.id"))
    # time = db.Column(db.DateTime)
    # money = db.Column(db.Float)
    invite_profit = db.Column(db.Float)


class Member_loan(db.Model):

    __tablename__ = "tjtyy_member_loan"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    member_id = db.Column(db.String(50), db.ForeignKey("tjtyy_member.id"))
    money_loan = db.Column(db.Float)
    loaner_name = db.Column(db.String(50))
    limit_loan = db.Column(db.String(20))
    time_loan = db.Column(db.DateTime)
    loan_status = db.Column(db.String(32), default=0)
    nature_house = db.Column(db.String(50))
    village_name = db.Column(db.String(50))
    area_house = db.Column(db.Float)
    remain_loan = db.Column(db.Float)
    property_id = db.Column(db.String(32))
    property_name = db.Column(db.String(32))
    property_idnum = db.Column(db.String(32))
