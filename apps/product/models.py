#!/use/bin/env python
# -*- coding: UTF-8 -*-

import uuid
from apps.dbinstance import db


class Invest_info(db.Model):

    __tablename__ = "tjtyy_invest_info"

    id = db.Column(db.Integer, primary_key= True)
    member_id = db.Column(db.String(36), db.ForeignKey('tjtyy_member.id'))
    product_id = db.Column(db.String(36), db.ForeignKey('tjtyy_borrow.id'))
    money = db.Column(db.Float)
    hongbao = db.Column(db.Float, nullable=0, default=0)
    profit = db.Column(db.Float)
    interest = db.Column(db.Float)
    activity_interest = db.Column(db.Float)
    contract = db.Column(db.String(36), db.ForeignKey("tjtyy_contract.id"))
    time = db.Column(db.DateTime)
    expect_time = db.Column(db.DateTime)
    is_effect = db.Column(db.SmallInteger)
    status = db.Column(db.String(1))
    order_id = db.Column(db.String(50))
    member_name = db.Column(db.String(128))
    NEWHAND_ID = db.Column(db.String(36), db.ForeignKey('tjtyy_newhand.id'))
    bluuid = db.Column(db.String(200))
    equipment = db.Column(db.String(128))
    channel_id = db.Column(db.String(10))
    preservationId = db.Column(db.String(128))
    activity = db.Column(db.String(256))
    rate_security = db.Column(db.Float)
    extra_rate = db.Column(db.Float)
    yaoqing_money = db.Column(db.Float)
    hongbao_source = db.Column(db.String(256))
    hongbao_info_id = db.Column(db.String(128))


class Contract(db.Model):

    __tablename__ = "tjtyy_contract"

    id = db.Column(db.GUID, primary_key= True)
    content = db.Column(db.Text)
    contract_name = db.Column(db.String(128))


class Organ_info(db.Model):

    __tablename__ = "tjtyy_organ"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(128))
    type = db.Column(db.String(128))
    descri = db.Column(db.String(128))
    logo = db.Column(db.String(128))
    start_time = db.Column(db.Date)
    end_time = db.Column(db.Date)
    recommend = db.Column(db.Boolean)
    coop_time = db.Column(db.Date)
    build_time = db.Column(db.Date)
    address = db.Column(db.String(128))
    reg_fund = db.Column(db.String(128))
    product_infos = db.relationship('Product_info',backref="tjtyy_organ", lazy="dynamic")


class Borrower_info(db.Model):

    __tablename__ = "tjtyy_borrower_info"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    borrower_name =  db.Column(db.String(128))
    company_name = db.Column(db.String(128))
    company_detail = db.Column(db.String(512))
    sex = db.Column(db.Boolean)
    age = db.Column(db.Integer)
    id_card = db.Column(db.String(128))
    borrow_type = db.Column(db.Integer)
    house_register = db.Column(db.String(128))
    edu_background = db.Column(db.String(128))
    health = db.Column(db.String(128))
    marriage = db.Column(db.Integer)
    moral_quality = db.Column(db.String(128))
    credit_registry = db.Column(db.String(128))
    year_income = db.Column(db.String(128))
    per_income = db.Column(db.String(128))
    family_opinion = db.Column(db.String(128))
    unit_nature = db.Column(db.String(128))
    industry = db.Column(db.String(128))
    stability = db.Column(db.String(128))
    position = db.Column(db.String(128))
    house_status = db.Column(db.String(128))
    estate_status = db.Column(db.String(128))
    repay_source = db.Column(db.String(128))
    borrow_amount = db.Column(db.Float)
    borrow_use = db.Column(db.String(128))
    borrower_address = db.Column(db.String(255))
    mobile = db.Column(db.String(255))
    product_infos = db.relationship('Product_info', backref="tjtyy_borrower_info", lazy="dynamic")


class Feature_info(db.Model):

    __tablename__ = "tjtyy_feature_info"

    id = db.Column(db.GUID, primary_key=True,default=uuid.uuid4)
    feature_name = db.Column(db.String(128))
    detail = db.Column(db.String(128))
    logo = db.Column(db.String(128))
    #product_infos = db.relationship('Product_info',backref="tjtyy_feature_info", lazy="dynamic")


class Product_image(db.Model):

    __tablename__ = "tjtyy_borrow_image"

    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(128))
    borrow_id = db.Column(db.String(36), db.ForeignKey("tjtyy_borrow.id"))


class Product_info(db.Model):

    __tablename__ = "tjtyy_borrow"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    product_name = db.Column(db.String(128))
    product_type = db.Column(db.String(128))
    organ_id = db.Column(db.String(36), db.ForeignKey("tjtyy_organ.id"))
    borrow_id = db.Column(db.String(36), db.ForeignKey("tjtyy_borrower_info.id"))
    feature_id = db.Column(db.String(512))
    rate = db.Column(db.Float)
    time_limit = db.Column(db.String(128))
    total_mount = db.Column(db.Float)
    limit_mount = db.Column(db.Float)
    rate_increase = db.Column(db.Float)
    start_time = db.Column(db.DateTime)
    sell_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    pro_time = db.Column(db.DateTime)
    audit_time =db.Column(db.DateTime)# 审计时间
    product_status = db.Column(db.String(128))# 产品状态（1为审核中、2为融资中、3为满标、4为还款中，5为已结束，6为未筹集成功，7为已退款，8为待上线）
    product_detail = db.Column(db.String(128))
    loan_use = db.Column(db.String(128))
    repay_type = db.Column(db.String(128))
    raise_limit = db.Column(db.String(128))
    interest_num = db.Column(db.Integer)
    interest_time = db.Column(db.DateTime)
    invest_infos = db.relationship('Invest_info', backref='tjtyy_borrow', lazy="dynamic")
    product_images = db.relationship('Product_image',backref="tjtyy_borrow", lazy="dynamic")
    is_recommend = db.Column(db.Integer)
    guarantee_id = db.Column(db.String(50))
    car_message = db.Column(db.String(255))


class Product_borrower_image(db.Model):

    __tablename__ = "tjtyy_borrower_image"

    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(256))
    borrower_id = db.Column(db.String(36), db.ForeignKey("tjtyy_borrower_info.id"))


class Product_new(db.Model):

    __tablename__ = "tjtyy_newhand"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    product_name = db.Column(db.String(128))
    rate = db.Column(db.Float)
    time_limit = db.Column(db.String(128))
    limit_mount = db.Column(db.Float)
    rate_increase = db.Column(db.Float, default=0)
    product_status = db.Column(db.String(128))
    product_detail = db.Column(db.String(128))
    repay_type = db.Column(db.String(128))


class DoLine(db.Model):

    __tablename__ = "tjtyy_doLine"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    member_id = db.Column(db.String(36), db.ForeignKey('tjtyy_member.id'))
    member_name = db.Column(db.String(128))
    money = db.Column(db.Float)
    time = db.Column(db.String(128))
    inspector = db.Column(db.String(50))
    order_id = db.Column(db.String(32))


class Borrow_attachment(db.Model):

    __tablename__ = "t_s_attachment"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    attachmenttitle = db.Column(db.String(128))
    realpath = db.Column(db.String(128))


class Borrow_file(db.Model):

    __tablename__ = "tjtyy_borrow_files"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    borrowId = db.Column(db.String(32))


# 担保人信息
class Account_info(db.Model):

    __tablename__ = "tjtyy_account_info"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    user_name =  db.Column(db.String(255))  # 担保人姓名
    account = db.Column(db.String(50))  # 银行卡号
    product_id = db.Column(db.String(50))  # 产品ID
    borrow_id = db.Column(db.String(50))  # 借款人ID
    MEMBER_ID = db.Column(db.String(50))
    id_card = db.Column(db.String(50))  # 身份证号