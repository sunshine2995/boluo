#!/use/bin/env python
# -*- coding: UTF-8 -*-

import json
from datetime import datetime, timedelta
import requests

from flask import request, render_template, g
from apps import app
from sqlalchemy import and_, or_, func
from flask_httpauth import HTTPBasicAuth
from config import BOLUO_URL, IS_REGISTER_SYNC, NEW_BOLUOLICAI_URL
from operator import itemgetter,attrgetter
from models import Member_recharge_info, Member_reflect_info, Member_asset_info,\
                   Order_dict,Member_income_statement, Member_red_pocket,\
                   Member_red_pocket_type, Province_city
from apps.member.models import Member, Member_real_info, Member_pay_info, Member_bank_logo, \
                               Member_invite_info, Member_login, Member_invite_profit
from apps.product.models import Invest_info, Product_info

from apps.member.utils import gen_reg_red_pocket
from apps.utils import toolkit
from apps.utils.toolkit import AlchemyEncoder
from apps.utils.lock import *
from apps.utils.payRestSdk import PayRest
from apps.utils.LLPayRestSdk import LLPayRest
from apps.utils.payconfig import BANK_CODE
from apps.dbinstance import db
from apps.activity.utils import send_hb, send_hb_today


auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username_or_token, password):
    # first try to authenticate by token
    user = Member.verify_auth_token(username_or_token)
    if not user:
        # try to authenticate with username/password
        user = Member.query.filter(or_(Member.name==username_or_token, Member.phone==username_or_token)).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True


@app.route('/v1/asset/llrecharge/<name_or_phone>/params', methods=['GET', 'POST'])
@sync(threading.Lock())
# @auth.login_required
def LL_Params(name_or_phone):
    response_data = {}
    response_data["code"] = u"10088"
    response_data["desc"] = u"平台已改版，请到渠道下载最新版菠萝理财"
    return toolkit.response(response_data, 200, None, True)
    bank_card  = request.form.get("bank_card", None)
    real_name = request.form.get("real_name", None)
    id_card = request.form.get("id_card", None)
    charge_money = request.form.get("charge_money", None)
    equipment_token = request.form.get('equipment_token', None)


    deadline_18 = int((datetime.today() - timedelta(days=365 * 18)).strftime("%Y%m%d"))
    if len(id_card) == 18:
        age = int(id_card[6:14])
        if age > deadline_18:
            response_data["code"] = u"10073"
            response_data["desc"] = u"不满18周岁，不能绑卡"
            return toolkit.response(response_data, 200, None, True)
    else:
        response_data["code"] = u"10072"
        response_data["desc"] = u"身份证号位数不对！"
        return toolkit.response(response_data, 200, None, True)

    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    mrii = Member_real_info.query.filter(Member_real_info.real_identid == id_card).first()
    mpii = Member_pay_info.query.filter(Member_pay_info.pay_bankcard == bank_card).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    if equipment_token:
        mll = Member_login.query.filter_by(member_name=name_or_phone).order_by(Member_login.last_time.desc()).first()
        if mll and mll.equipment_token != equipment_token:
            response_data["code"] = u"18"
            response_data["desc"] = u"请重新登录后再进行充值"
            return toolkit.response(response_data, 200, None, True)

    if mrii and str(mrii.member_id) != str(m.id):
        response_data["code"] = u"19"
        response_data["desc"] = u"身份证已绑定"
        return toolkit.response(response_data, 200, None, True)
    if mpii and str(mpii.member_id) != str(m.id):
        response_data["code"] = u"23"
        response_data["desc"] = u"银行卡已绑定"
        return toolkit.response(response_data, 200, None, True)
    try:
        if str(mrii.member_id) != str(m.id) or  str(mpii.member_id) != str(m.id):
            response_data["code"] = u"23"
            response_data["desc"] = u"银行卡已绑定"
            return toolkit.response(response_data, 200, None, True)
    except:
        pass

    try:
        if float(charge_money) < 1:
            response_data["code"] = u"23"
            response_data["desc"] = u"充值最小金额为1元"
            return toolkit.response(response_data, 200, None, True)
    except:
        pass


    if m is None:
        response_data["code"] = "10001"
        response_data["content"] = {}
        response_data["desc"] = u"请求失败"
        return toolkit.response(response_data, 200, None, True)

    charge_time = datetime.now()
    now_time = datetime.strftime(charge_time, '%Y-%m-%d %H:%M:%S')
    dt_order = datetime.strftime(charge_time, '%Y%m%d%H%M%S')
    order = Order_dict.query.filter_by(is_use = False).first()
    no_order = order.order_id


    ch = '*'
    phone_s = m.phone[0:3] +4*ch + m.phone[7:11]

    name_goods = u"充值"
    info_order = u"用户%s于%s充值%s元, 手机号%s" % (m.name, now_time, charge_money, phone_s)

    llpr = LLPayRest(user_id=str(m.id).replace('-', ''))
    res_dict = llpr.bank_card_auth_bin(bank_card)
    print res_dict["content"]["ret_code"]
    if str(res_dict["code"]) == "1":
        response_data["code"] = u"10071"
        response_data["content"] = {}
        response_data["desc"] = u"支付遇到网络错误"
        return toolkit.response(response_data, 200, None, True)
    elif res_dict["content"]["ret_code"] == "0000":
        bank_code = res_dict["content"]["bank_code"]
    else:
        response_data["code"] = u"10003"
        response_data["content"] = {}
        response_data["desc"] = u"该银行卡号bin信息查询有误"
        return toolkit.response(response_data, 200, None, True)

    try:
        response_data["code"] = u"10000"
        response_data["content"] = {}
        response_data["desc"] = u"请求成功"

        if bank_code in BANK_CODE:
            response_data["content"]["bank_flag"] = True
        else:
            response_data["content"]["bank_flag"] = False
        frms_ware_category = "2009"
        user_info_dt_register = datetime.strftime(m.reg_time, '%Y%m%d%H%M%S')
        user_info_mercht_userno = str(m.id).replace("-","")
        code = res_dict["content"]["ret_code"]

        try:
            ml = Member_login.query.filter_by(member_id=m.id).order_by(Member_login.last_time.desc()).first()
            equipment = ml.equipment_name
        except Exception, e:
            equipment = 'app'
            print e

        order.is_use = True
        db.session.merge(order)
        db.session.commit()

        llpr.setPayBaseParams()
        llpr.setOrderParam(no_order=no_order, dt_order=dt_order, name_goods=name_goods, info_order=info_order)
        llpr.setRiskItem(frms_ware_category, user_info_mercht_userno, user_info_dt_register, real_name, id_card, user_info_bind_phone=m.phone, \
                         user_info_identify_state="1", user_info_identify_type="1")
        params = llpr.mobilePay(real_name, id_card, bank_card, charge_money)

        mr = Member_recharge_info(member_id=str(m.id).replace('-', ''), member_name=m.name,
                          recharge_id=params['no_order'], time=now_time, is_effect=0, money=charge_money,type=2,
                              bangka=bank_card, code=code, equipment=equipment,
                             bluuid=m.bluuid, device_info=m.device_info, channel_id=m.channel_id)

        db.session.add(mr)
        db.session.commit()
        response_data["content"]["sub_mit"] = params

        return toolkit.response(response_data, 200, None, True)
    except Exception, e:
        print '================eeeeee====================='
        print e
        print '================eeeeee====================='
        response_data["code"] = u"10013"
        response_data["content"] = {}
        response_data["desc"] = u"操作异常"
        return toolkit.response(response_data, 200, None, True)


def after_this_request(bank_code):
    def wrapper(f):
        if not hasattr(g, 'after_request_callbacks'):
            g.after_request_callbacks = {}
            g.after_request_callbacks[bank_code] = f
        return f
    return wrapper


@app.after_request
def call_after_request_callbacks(response):
    for args, callback in getattr(g, 'after_request_callbacks', {}).items():
        callback(args)
    return response


def give_hongbao(member_id):
    # give hongbao
    inr = Member_invite_info.query.filter(Member_invite_info.invited_id == member_id).first()
    red_list = []
    if inr and inr.sign == 0:
        inm = Member.query.filter(Member.id == str(inr.inviter_id).replace('-','')).first()
        type = "2"
        red_list.append(gen_reg_red_pocket(type, inm.id, 990))
        red_list.append(gen_reg_red_pocket(type, inm.id, 1980))
        red_list.append(gen_reg_red_pocket(type, inm.id, 4980))
        for item in red_list:
            db.session.add(item)
            db.session.commit()
        inr.sign = 1
        db.session.merge(inr)
        db.session.commit()


@app.route('/v1/asset/<member_id>/<bank_card>/llrecharge/result', methods=['GET','POST'])
def LL_Charge_Result(member_id, bank_card):
    res_list = request.stream.readlines()
    res_dict = json.loads(res_list[0])
    oid_partner = res_dict.get("oid_partner", None)
    sign_type =res_dict.get("sign_type", None)
    sign = res_dict.get("sign", None)
    dt_order = res_dict.get("dt_order",None)
    no_order = res_dict.get("no_order", None)
    oid_paybill = res_dict.get("oid_paybill", None)
    money_order = res_dict.get("money_order", None)
    result_pay = res_dict.get("result_pay", None)
    settle_date = res_dict.get("settle_date", None)
    info_order = res_dict.get("info_order", None)
    pay_type = res_dict.get("pay_type", None)
    bank_code = res_dict.get("bank_code", None)
    no_agree = res_dict.get("no_agree", None)
    id_type = res_dict.get("id_type", None)
    id_no = res_dict.get("id_no", None)
    acct_name = res_dict.get("acct_name", None)
    card_no = res_dict.get("card_no", None)

    response_data = {}
    m = Member.query.filter(Member.id==member_id).first()
    if m is None:
        response_data["code"] = u"0001"
        response_data["content"] = u"交易失败,用户不存在"
        return toolkit.response(response_data, 200, None, True)

    print '===================支付回调接口:===================='
    print 'member_id=%s' % member_id
    print 'result_pay=%s' % result_pay
    print 'time=%s' % datetime.now()
    print '==================================================='

    if result_pay == "SUCCESS":
        @after_this_request(bank_card)
        def get_bank_card_bin(bank_card):
            llpr = LLPayRest(user_id=member_id)
            res_dict = llpr.bank_card_auth_bin(bank_card)
            if int(m.is_pay_bind) == 0:
                bank_code = res_dict["content"]["bank_code"]
                bank_logo = Member_bank_logo.query.filter_by(bank_code=bank_code).first()
                if not bank_logo:
                    bank_logo = Member_bank_logo.query.first()
                mpi = Member_pay_info(member_id=str(m.id).replace('-', ''), pay_bankcard=bank_card, account_holder=acct_name, \
                              bank_code=res_dict["content"]["bank_code"], bank_name=res_dict["content"]["bank_name"], \
                              card_type=res_dict["content"]["card_type"], single_amt=res_dict["content"]["single_amt"], \
                              day_amt=res_dict["content"]["day_amt"], month_amt=res_dict["content"]["month_amt"])
                db.session.add(mpi)
                db.session.commit()
                m.is_pay_bind = 1
                db.session.merge(m)
                db.session.commit()
                try:
                    if IS_REGISTER_SYNC:
                        new_url = NEW_BOLUOLICAI_URL + '/v1/member/%s/bank/sync' % member_id
                        post_para = {
                            "pay_bankcard": bank_card,
                            "account_holder": acct_name,
                            "bank_code": res_dict["content"]["bank_code"],
                            "bank_name": res_dict["content"]["bank_name"],
                            "card_type": res_dict["content"]["card_type"],
                            "single_amt": res_dict["content"]["single_amt"],
                            "day_amt": res_dict["content"]["day_amt"],
                            "month_amt": res_dict["content"]["month_amt"]
                        }
                        res = requests.post(new_url, data=post_para, timeout=5).json()
                        if res['code'] == '10000':
                            response_data["bank_sync"] = True
                        else:
                            response_data["bank_sync"] = False
                except:
                    response_data["bank_sync"] = False

            if int(m.is_identity_bind) == 0:
                mri = Member_real_info(member_id = str(m.id).replace('-', ''), real_name=acct_name, real_identid=id_no)
                db.session.add(mri)
                db.session.commit()
                m.is_identity_bind = 1
                db.session.merge(m)
                db.session.commit()
                try:
                    if IS_REGISTER_SYNC:
                        new_url = NEW_BOLUOLICAI_URL + '/v1/member/%s/verified/sync' % member_id
                        post_para = {
                            "real_name": acct_name,
                            "real_identid": id_no
                        }
                        res = requests.post(new_url, data=post_para, timeout=5).json()
                        if res['code'] == '10000':
                            response_data["verified_sync"] = True
                        else:
                            response_data["verified_sync"] = False
                except:
                    response_data["verified_sync"] = False

        mr = Member_recharge_info.query.filter(Member_recharge_info.recharge_id == no_order).first()
        if mr.is_effect == 1:
            response_data["ret_code"] = u"0000"
            response_data["ret_msg"] = u"交易成功"
            return toolkit.response(response_data, 200, None, True)

        mr.is_effect = 1
        
        ma = Member_asset_info.query.filter(Member_asset_info.member_id == str(m.id).replace('-','')).first()
        ma.rechargeamount += float(money_order)
        ma.totalamount += float(money_order)

        type = u"充值"
        balance = ma.rechargeamount + ma.remainamount + float(money_order)
        ins = Member_income_statement(member_id=str(m.id).replace('-',''), type=type, money=money_order, \
                                      balance=balance, time=dt_order, info=info_order, order_id=no_order,
                                      phone=m.phone, bin_order_id='c%s' % no_order)
        # give hongbao
        inr = Member_invite_info.query.filter(Member_invite_info.invited_id == str(m.id).replace('-','')).first()
        red_list = []
        if inr is not None and inr.sign == 0:
            inm = Member.query.filter(Member.id == str(inr.inviter_id).replace('-','')).first()
            type = "2"
            red_list.append(gen_reg_red_pocket(type, inm.id, 990))
            red_list.append(gen_reg_red_pocket(type, inm.id, 1980))
            red_list.append(gen_reg_red_pocket(type, inm.id, 4980))
            inr.sign = 1
        
        try:
            db.session.merge(mr)
            db.session.merge(ma)
            db.session.add(ins)
            db.session.commit()

            for item in red_list:
                db.session.add(item)
                db.session.commit()

            if inr is not None:
                db.session.merge(inr)
                db.session.commit()
            response_data["ret_code"] = u"0000"
            response_data["ret_msg"] = u"交易成功"
            return toolkit.response(response_data, 200, None, True)
        except:
            response_data["ret_code"] = u"0002"
            response_data["ret_msg"] = u"交易失败"
            return toolkit.response(response_data, 200, None, True)
    else:
        response_data["ret_code"] = u"0003"
        response_data["ret_msg"] = u"交易失败"
        return toolkit.response(response_data, 200, None, True)


@app.route('/v1/asset/<name_or_phone>/reflect', methods=['GET', 'POST'])
# @auth.login_required
def reflect(name_or_phone):
    bank_card = request.form.get("bank_card", None)
    reflect_money = request.form.get("reflect_money", None)
    province = request.form.get("province", None)
    city = request.form.get("city", None)
    bank_address = request.form.get("bank_address", None)
    bank_code = request.form.get("bank_code", None)
    pay_passwd = request.form.get("pay_passwd", None)
    reflect_money = float(reflect_money)
    response_data={}
    if reflect_money is None or reflect_money == "":
        response_data["code"] = u"10001"
        response_data["content"]={}
        response_data["desc"] = u"参数字段不能为空"
        return toolkit.response(response_data, 200, None, True)

    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    if m.is_pay_bind is False:
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"未绑定银行卡"
        return toolkit.response(response_data, 200, None, True)

    if m.pay_passwd is None:
        response_data["code"] = u"10021"
        response_data["content"]={}
        response_data["desc"] = u"交易密码为空，请先设置交易密码"
        return toolkit.response(response_data, 200, None, True)

    if not m.verify_pay_password(pay_passwd):
        response_data["code"] = u"10017"
        response_data["content"]={}
        response_data["desc"] = u"交易密码不正确"
        return toolkit.response(response_data, 200, None, True)

    if int(m.is_pay_bind)==1:
        mpi = Member_pay_info.query.filter(Member_pay_info.member_id == str(m.id).replace("-", "")).first()
        if str(mpi.bank_code) == bank_code and str(mpi.pay_bankcard) == bank_card:
            mpi.province = province
            mpi.city = city
            mpi.bank_address = bank_address
            db.session.merge(mpi)
            db.session.commit()
        else:
            response_data["code"] = u"10013"
            response_data["content"]={}
            response_data["desc"] = u"银行卡编码不匹配"
            return toolkit.response(response_data, 200, None, True)

    now_time = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')

    order = Order_dict.query.filter_by(is_use = False).first()

    type = u"提现"
    info = u"申请提现%s" % reflect_money

    ma = Member_asset_info.query.filter(Member_asset_info.member_id == str(m.id).replace('-','')).first()

    if ma.rechargeamount + ma.remainamount < float(reflect_money):
        response_data["code"] = u"10011"
        response_data["content"]={}
        response_data["desc"] = u"提现的金钱大于可用余额"
        return toolkit.response(response_data, 200, None, True)

    if float(reflect_money) < 100:
        response_data["code"] = u"10012"
        response_data["content"]={}
        response_data["desc"] = u"最小提现金额100"
        return toolkit.response(response_data, 200, None, True)

    #cal fee
    fee = 0.01
    small_fee = 0.0
    invest_fee = 0.0
    if float(reflect_money) < ma.remainamount and float(reflect_money) <= 1000:
        if invest_fee + small_fee > ma.rechargeamount + ma.remainamount:
            response_data["code"] = u"10012"
            response_data["content"]={}
            response_data["desc"] = u"提现的所产生利息大于可用余额"
            return toolkit.response(response_data, 200, None, True)
        else:
            ma.remainamount = ma.remainamount-float(reflect_money)
    elif float(reflect_money) < ma.remainamount and float(reflect_money) > 1000:
        if invest_fee + small_fee > ma.rechargeamount + ma.remainamount:
            response_data["code"] = u"10012"
            response_data["content"]={}
            response_data["desc"] = u"提现的所产生利息大于可用余额"
            return toolkit.response(response_data, 200, None, True)
        else:
            ma.remainamount = ma.remainamount-float(reflect_money)
    elif float(reflect_money) >= ma.remainamount and ma.remainamount < 1000 and float(reflect_money) >= 1000:
        small_fee = (float(reflect_money)-ma.remainamount)*fee
        ma.rechargeamount = ma.rechargeamount-(float(reflect_money)-ma.remainamount)
        if ma.rechargeamount < small_fee:
            reflect_money -= (small_fee - ma.rechargeamount)
            ma.rechargeamount = 0
        else:
            ma.rechargeamount = ma.rechargeamount - small_fee
        ma.remainamount = 0.0

    elif float(reflect_money) >= ma.remainamount and ma.remainamount >= 1000 and float(reflect_money) >= 1000:
        small_fee = (float(reflect_money)-ma.remainamount)*fee
        ma.rechargeamount = ma.rechargeamount-(float(reflect_money)-ma.remainamount)
        if ma.rechargeamount < small_fee:
            reflect_money -= (small_fee - ma.rechargeamount)
            ma.rechargeamount = 0
        else:
            ma.rechargeamount = ma.rechargeamount - small_fee
        ma.remainamount = 0.0

    elif float(reflect_money) >= ma.remainamount and float(reflect_money) < 1000:
        small_fee = (float(reflect_money)-ma.remainamount)*fee
        ma.rechargeamount = ma.rechargeamount-(float(reflect_money)-ma.remainamount)
        if ma.rechargeamount < small_fee:
            reflect_money -= (small_fee - ma.rechargeamount)
            ma.rechargeamount = 0
        else:
            ma.rechargeamount = ma.rechargeamount - small_fee
        ma.remainamount = 0.0
        
    balance = ma.remainamount + ma.rechargeamount
    ins = Member_income_statement(member_id=str(m.id).replace('-', ''), type=type,
                                  money=reflect_money, balance=balance, time=now_time, info=info, order_id=order.order_id,phone=m.phone)

    # type02 = u"提现手续费"
    # info02 = u"提现手续费%s" % small_fee
    # ins02 = Member_income_statement(member_id=str(m.id).replace('-', ''), type=type02,
    #                               money=small_fee, balance=balance, time=now_time, info=info02, order_id=order.order_id)

    ma.freezeamount = ma.freezeamount + float(reflect_money)
    # fee = small_fee+invest_fee
    mr = Member_reflect_info(member_id=str(m.id).replace('-', ''), member_name=m.name,
                             reflect_id=order.order_id, money=float(reflect_money), time=now_time, fee=small_fee, type=1,
                             bluuid=m.bluuid, device_info=m.device_info, channel_id=m.channel_id)

    try:
        db.session.add(mr)
        db.session.commit()
        order.is_use = True
        db.session.merge(order)
        db.session.commit()
        db.session.merge(ma)
        db.session.commit()
        db.session.add(ins)
        # db.session.add(ins02)
        db.session.commit()

        response_data["code"] = u"10000"
        response_data["content"]={}
        response_data["desc"] = u"请求成功"
        return toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"] = u"10019"
        response_data["content"]={}
        response_data["desc"] = u"未知异常"
        return toolkit.response(response_data, 200, None, True)


@app.route('/v1/asset/<name_or_phone>/1/list/<page_num>', methods=['GET', 'POST'])
#@auth.login_required
def list_charge(name_or_phone, page_num):

    if page_num is None:
        page_num = 1
    pnum = int(page_num.encode('ascii'))
    pnum = (pnum-1) *10
    query_res = Member_recharge_info.query.join(Member, Member.id == Member_recharge_info.member_id) \
            .filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).order_by(Member_recharge_info.time.desc()).all()[pnum:pnum+10]


    response_data = {}
    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    response_data["content"] = json.loads(json.dumps(query_res,cls=AlchemyEncoder, sort_keys=True,indent=4,separators=(',',":")))
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/asset/<name_or_phone>/recharge/sum', methods=['GET', 'POST'])
@auth.login_required
def list_charge_sum(name_or_phone):

    query_res = Member_recharge_info.query.join(Member, Member.id == Member_recharge_info.member_id) \
            .filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).order_by(Member_recharge_info.time.desc()).all()

    response_data = {}
    response_data["code"] = u"0"
    response_data["count"] =unicode(len(query_res))
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/asset/<name_or_phone>/2/list/<page_num>', methods=['GET', 'POST'])
#@auth.login_required
def list_reflect(name_or_phone, page_num):

    
    if page_num is None:
        page_num = 1
    pnum = int(page_num.encode('ascii'))
    pnum = (pnum-1) *10
    query_res = Member_reflect_info.query.join(Member, Member.id == Member_reflect_info.member_id) \
            .filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).order_by(Member_reflect_info.time.desc()).all()[pnum:pnum+10]

    response_data = {}
    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    response_data["content"] = []
    response_data["content"] = json.loads(json.dumps(query_res,cls=AlchemyEncoder, sort_keys=True,indent=4,separators=(',',":")))
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/asset/<name_or_phone>/reflect/sum', methods=['GET', 'POST'])
@auth.login_required
def list_reflect_sum(name_or_phone):

    query_res = Member_reflect_info.query.join(Member, Member.id == Member_reflect_info.member_id) \
            .filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).order_by(Member_reflect_info.time.desc()).all()

    response_data = {}
    response_data["code"] = u"0"
    response_data["count"] =unicode(len(query_res))
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/asset/<name_or_phone>/account/detail', methods=['GET', 'POST'])
# @auth.login_required
def asset_detail(name_or_phone):
    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    member_id = str(m.id).replace('-', '')
    query_top = db.session.query(Member_asset_info.remainamount, Member_asset_info.rechargeamount, Member_pay_info.pay_bankcard, \
                                 Member_pay_info.single_amt, Member_pay_info.day_amt, Member_pay_info.month_amt, Member_pay_info.account_holder, \
                                 Member_pay_info.bank_code, Member_pay_info.bank_name, Member_real_info.real_identid, \
                                 Member_real_info.real_name, Member_pay_info.province, Member_pay_info.city, Member_pay_info.bank_address)
    query_res = query_top.filter(and_(Member_asset_info.member_id == member_id, Member_pay_info.member_id == member_id, \
                                 Member_real_info.member_id == member_id)).first()

        
    response_data = {}
    response_data["code"]=u"10000"
    response_data["content"] = {}
    bank_list = ["01020000", "01040000", "01030000", "03080000", "03030000", "03100000"]
    if query_res is not None:
        city = None
        province = None
        if query_res[12] is not None:
            city = Province_city.query.filter(Province_city.code==query_res[12]).first()
        if query_res[11] is not None:
            province = Province_city.query.filter(Province_city.code==query_res[11]).first()
        bank_logo = Member_bank_logo.query.filter_by(bank_code=query_res[7]).first()
        response_data["content"]["bank_address"] = BOLUO_URL + bank_logo.logo if bank_logo else ''
        if query_res[7] in bank_list:
            response_data["content"]["is_six_bank"] = True
        else:
            response_data["content"]["is_six_bank"] = False

        response_data["content"]["remain_balance"] = float(query_res[0]) + float(query_res[1])
        response_data["content"]["pay_bankcard"] = query_res[2]
        response_data["content"]["single_amt"] = float(bank_logo.single_amt) if bank_logo else ''
        response_data["content"]["day_amt"] = float(bank_logo.day_amt) if bank_logo else ''
        response_data["content"]["month_amt"] = float(bank_logo.month_amt) if bank_logo else ''
        response_data["content"]["holder"] = query_res[6]
        response_data["content"]["bank_code"] = query_res[7]
        response_data["content"]["bank_name"] = query_res[8]
        response_data["content"]["id_card"] = query_res[9]
        response_data["content"]["real_name"] = query_res[10]
        response_data["content"]["province"] = (city and city.city) or ""
        response_data["content"]["city"] = (province and province.province) or ""
        response_data["content"]["province_code"] = query_res[11]
        response_data["content"]["city_code"] = query_res[12]
        response_data["content"]["rechargeamount"] = float(query_res.rechargeamount)
        response_data["content"]["remainamount"] = float(query_res.remainamount)
        response_data["content"]["is_register_xinwang"] = m.is_register_xinwang
        if m.isblack == 'Sync':
            response_data["content"]["remain_balance"] = 0.0
            response_data["content"]['rechargeamount'] = 0.0
            response_data["content"]['remainamount'] = 0.0

        response_data["desc"] = u"请求成功"
    else:
        response_data["code"]=u"10001"
        response_data["desc"] = u"用户不存在"
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/asset/<name_or_phone>/account/asset', methods=['GET', 'POST'])
# @auth.login_required
def account_asset(name_or_phone):
    response_data = {}
    response_data["content"] = {}
    response_data["code"]=u"10000"

    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    if not m:
        response_data["code"] = u"10002"
        response_data["desc"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)
    response_data["content"]["is_pay_bind"] = m.is_pay_bind  # 未激活

    member_id = str(m.id).replace('-', '')

    query_top = db.session.query(Member_asset_info)
    query_res = query_top.filter(Member_asset_info.member_id == member_id).first()

    if not query_res:
        ma = Member_asset_info(member_id=m.id, member_name=phone)
        db.session.add(ma)
        db.session.commit()

    # query_ins = db.session.query(func.sum(Invest_info.profit-Invest_info.money), Member.name, Member.phone)
    # query_ins_res = query_ins.filter(and_(Invest_info.member_id == Member.id, \
    #                                  or_(Member.name==name_or_phone, Member.phone==name_or_phone))).first()

    # 订单表加息收益
    query_ins02 = db.session.query(func.sum(Invest_info.interest), func.sum(Invest_info.activity_interest),
                                   func.sum(Invest_info.hongbao))
    query_ins02_res = query_ins02.filter(Invest_info.member_id==member_id, Invest_info.is_effect==1).first()

    # 邀请收益
    query_ins03 = db.session.query(func.sum(Member_invite_profit.invite_profit))
    query_ins03_res = query_ins03.filter(Member_invite_profit.inviter_id==member_id).first()

    # 红包个数
    now_time = datetime.now()
    # query_hongbao_top = db.session.query(Member_red_pocket_type, Member_red_pocket, Member.name, Member.phone)
    # query_hongbao_ques = query_hongbao_top.filter(and_(Member_red_pocket.generate_time>now_time,Member_red_pocket.member_id == Member.id, \
    #                                   Member_red_pocket.sort_id == Member_red_pocket_type.id, or_(Member.name==name_or_phone, \
    #                                   Member.phone == name_or_phone), and_(Member_red_pocket.is_use==0, Member_red_pocket.is_freeze==0))).all()
    query_hongbao_ques_count = db.session.query(Member_red_pocket).filter(and_(Member_red_pocket.member_id==member_id,Member_red_pocket.is_use==0,
                                                    Member_red_pocket.is_freeze==0,Member_red_pocket.generate_time>now_time)).count()


    response_data["content"]['z_interest'] = query_ins02_res[0] or 0
    response_data["content"]['z_activity_interest'] = query_ins02_res[1] or 0
    response_data["content"]['z_hongbao'] = query_ins02_res[2] or 0
    response_data["content"]['z_yaoqing_shouyi'] = query_ins03_res[0] or 0

    sum_profit = response_data["content"]['z_interest'] + response_data["content"]['z_activity_interest'] + \
                               response_data["content"]['z_hongbao'] + response_data["content"]['z_yaoqing_shouyi']

    if query_res is not None:
        response_data["content"]["remain_balance"] = float(query_res.rechargeamount) + float(query_res.remainamount)
        response_data["content"]["freezeamount"] = float(query_res.freezeamount)
        response_data["content"]["uncollectedamount"] = float(query_res.uncollectedamount)
        response_data["content"]["name"] = m.name
        response_data["content"]["sum_profit"] = sum_profit
        response_data["content"]["is_vip"] = m.level
        response_data["content"]["touxiang_image"] = m.touxiang_image or ''
        response_data["content"]["has_hongbao_num"] = query_hongbao_ques_count
        response_data["content"]['rechargeamount'] = float(query_res.rechargeamount)
        response_data["content"]['remainamount'] = float(query_res.remainamount)
        response_data["content"]["is_register_xinwang"] = m.is_register_xinwang if m.is_register_xinwang else 0
        response_data["content"]['type'] = m.fxpinggu if m.fxpinggu else ""
        if m.isblack == 'Sync':
            response_data["content"]["remain_balance"] = 0.0
            response_data["content"]['rechargeamount'] = 0.0
            response_data["content"]['remainamount'] = 0.0
        response_data["desc"] = u"请求成功"
    else:
        response_data["code"] = u"10001"
        response_data["desc"] = u"用户不存在"

    try:
        send_hb_today(member_id, '私人专属', '1.8%私人专属加息券')
    except Exception, e:
        print e
    return toolkit.response(response_data, 200, None, True)



@app.route('/v1/asset/<name_or_phone>/0/detail/<page_num>', methods=['GET', 'POST'])
# @auth.login_required
def get_income_detail(name_or_phone, page_num):

    if page_num is None:
        page_num = 1
    pnum = int(page_num.encode('ascii'))
    pnum = (pnum-1) *10
    query_res = Member_income_statement.query.filter(Member_income_statement.phone == name_or_phone).order_by(Member_income_statement.time.desc()).all()[pnum:pnum+10]

    response_data = {}
    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    response_data["content"] = []
    response_data["content"] = json.loads(json.dumps(query_res,cls=AlchemyEncoder, sort_keys=True,indent=4,separators=(',',":")))
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/asset/<name_or_phone>/income/sum', methods=['GET', 'POST'])
@auth.login_required
def get_income_detail_sum(name_or_phone):

    query_res = Member_income_statement.query.join(Member, Member.id == Member_income_statement.member_id) \
            .filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).order_by(Member_income_statement.time.desc()).all()

    response_data = {}
    response_data["code"] = u"0"
    response_data["count"] =unicode(len(query_res))
    return toolkit.response(response_data, 200, None, True)


# 可用红包有哪些
@app.route('/v1/asset/<name_or_phone>/account/red/pocket', methods=['GET', 'POST'])
# @auth.login_required
def get_red_pocket(name_or_phone):
    start_money = request.form.get("start_money", None)
    product_id = request.form.get("product_id", None)

    now_time = datetime.now()
    response_data = {}
    if start_money is None:
        response_data["code"] = u"10002"
        response_data["desc"] = u"参数不能为空"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)

    not_use = []

    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    if not m:
        response_data["code"] = u"10003"
        response_data["desc"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)

    product_info = Product_info.query.filter_by(id=product_id).first()


    member_id = str(m.id).replace('-', '')
    hongbao_info = Member_red_pocket.query.filter_by(member_id=member_id).order_by(
        Member_red_pocket.generate_time.desc()).all()


    start_money_float = float(str(start_money).rstrip('元'))
    for i in hongbao_info:
        mrpt = Member_red_pocket_type.query.filter_by(id=i.sort_id).first()
        if int(mrpt.type) != 99:
            i.name = mrpt.name
            i.rules = mrpt.rules
            i.money = mrpt.money
            i.start_money = mrpt.start_money
            i.invest_days = mrpt.invest_days
            if product_info:
                if i.is_use == 0 and i.is_freeze == 0 and i.generate_time >= now_time and mrpt.start_money + mrpt.money <= start_money_float and int(mrpt.invest_days) <= int(product_info.time_limit):
                    not_use.append(i)
            else:
                if i.is_use == 0 and i.is_freeze == 0 and i.generate_time >= now_time and mrpt.start_money + mrpt.money <= start_money_float:
                    not_use.append(i)
        else:
            pass

    response_data = {}
    if not_use is None:
        response_data["code"] = u"10001"
        response_data["desc"] = u"该用户的数据不存在"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)

    response_data["code"] = u"10000"
    response_data["content"] =[]
    for item in sorted(not_use,key=attrgetter('money'),reverse=True):
        response_data["content"].append(dict(id=item.id, name=item.name, money=item.money, \
                                        rules=item.rules, start_money=item.start_money+item.money, dead_time=str(item.generate_time), \
                                        is_freeze=item.is_freeze, is_use=item.is_use,invest_days=item.invest_days if item.invest_days else '30'))
    response_data["desc"] = u"请求成功"
    return toolkit.response(response_data, 200, None, True)


# 可用加息劵有哪些
@app.route('/v1/asset/<name_or_phone>/account/rate/pocket', methods=['GET', 'POST'])
# @auth.login_required
def get_rate_pocket(name_or_phone):

    start_money = request.form.get("start_money", None)
    product_id = request.form.get("product_id", None)

    now_time = datetime.now()
    response_data = {}
    if start_money is None:
        response_data["code"] = u"10002"
        response_data["desc"] = u"参数不能未空"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)

    start_money_float = float(str(start_money).rstrip('元'))
    not_use = []

    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    if not m:
        response_data["code"] = u"10003"
        response_data["desc"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)
    member_id = str(m.id).replace('-', '')

    product_info = Product_info.query.filter_by(id=product_id).first()

    hongbao_info = Member_red_pocket.query.filter_by(member_id=member_id).order_by(
        Member_red_pocket.generate_time.desc()).all()

    for i in hongbao_info:
        mrpt = Member_red_pocket_type.query.filter_by(id=i.sort_id).first()
        if int(mrpt.type) == 99:
            i.name = mrpt.name
            i.rules = mrpt.rules
            i.money = mrpt.money
            i.start_money = mrpt.start_money
            i.rate = mrpt.rate
            i.invest_days = mrpt.invest_days
            if product_info:
                if i.is_use == 0 and i.is_freeze == 0 and i.generate_time >= now_time and mrpt.start_money <= start_money_float and int(mrpt.invest_days) <= int(product_info.time_limit):
                    not_use.append(i)
            else:
                if i.is_use == 0 and i.is_freeze == 0 and i.generate_time >= now_time and mrpt.start_money <= start_money_float:
                    not_use.append(i)
        else:
            pass


    response_data = {}
    if not_use is None:
        response_data["code"] = u"10001"
        response_data["desc"] = u"该用户的数据不存在"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    response_data["code"] = u"10000"
    response_data["content"] = []
    for item in not_use:
        response_data["content"].append(dict(id=item.id, name=item.name, rate=str(item.rate),\
                                             rules=item.rules, start_money=item.start_money + item.money,
                                             dead_time=str(item.generate_time), \
                                             is_freeze=item.is_freeze, is_use=item.is_use,invest_days=item.invest_days if item.invest_days else '30'))
    response_data["desc"] = u"请求成功"


    return toolkit.response(response_data, 200, None, True)


# 我的优惠劵有哪些红包
@app.route('/v1/asset/<name_or_phone>/red/pocket', methods=['GET', 'POST'])
# @auth.login_required
def get_red_pocket_detail(name_or_phone):
    response_data = {}
    now_time = datetime.now()

    not_use = []
    already_use = []
    expire_date = []

    m = Member.query.filter(or_(Member.name==name_or_phone,Member.phone == name_or_phone)).first()
    if not m:
        response_data["code"] = u"10002"
        response_data["desc"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)
    member_id = str(m.id).replace('-','')
    hongbao_info = Member_red_pocket.query.filter_by(member_id=member_id).order_by(Member_red_pocket.generate_time.desc()).all()

    for i in hongbao_info:
        mrpt = Member_red_pocket_type.query.filter_by(id=i.sort_id).first()
        if int(mrpt.type) != 99 and int(mrpt.type) != 7:
            i.name = mrpt.name
            i.rules = mrpt.rules
            i.money = mrpt.money
            i.start_money = mrpt.start_money
            i.invest_days= mrpt.invest_days
            if i.is_use == 0 and i.is_freeze == 0 and i.generate_time >= now_time:
                not_use.append(i)
            elif i.is_use == 1 or i.is_freeze == 1:
                already_use.append(i)
            elif i.is_use == 0 and i.generate_time < now_time:
                expire_date.append(i)
        else:
            pass

    response_data = {}

    Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    query_top_123 = db.session.query(Product_info.id, Product_info.product_name, Product_info.product_type, Product_info.feature_id, Product_info.rate, Product_info.sell_time,
                                     Product_info.time_limit, Product_info.product_status, Product_info.raise_limit, Product_info.total_mount, Product_info.limit_mount, Product_info.is_recommend, Product_info.rate_increase)
    products_123 = query_top_123.filter(and_(Product_info.start_time <= Now,
                                            or_(Product_info.product_status == '2', Product_info.product_status == '3')
                                       )).order_by(Product_info.time_limit.desc(), Product_info.start_time.desc()).limit(20).first()

    response_data["code"] = u"10000"                                
    response_data["content"] =[]
    for item in not_use:
        response_data["content"].append(dict(id=item.id, name=item.name, money=item.money, \
                                        rules=item.rules, start_money=item.start_money+item.money, dead_time=str(item.generate_time), \
                                        is_freeze=item.is_freeze, is_use=item.is_use, type=0, product_id=str(products_123.id).replace("-", ""),is_new_product='1' if products_123.product_type == '新手标' else '0',invest_days=item.invest_days if item.invest_days else '30'))
    for item in already_use:
        response_data["content"].append(dict(id=item.id, name=item.name, money=item.money, \
                                        rules=item.rules, start_money=item.start_money+item.money, dead_time=str(item.generate_time), \
                                        is_freeze=item.is_freeze, is_use=item.is_use, type=1,is_new_product='',invest_days=item.invest_days if item.invest_days else '30'))
    for item in expire_date:
        response_data["content"].append(dict(id=item.id, name=item.name, money=item.money, \
                                        rules=item.rules, start_money=item.start_money+item.money, dead_time=str(item.generate_time), \
                                        is_freeze=item.is_freeze, is_use=item.is_use, type=2,is_new_product='',invest_days=item.invest_days if item.invest_days else '30'))
    response_data["desc"] = u"请求成功"
    return  toolkit.response(response_data, 200, None, True)


# 我的优惠劵有哪些加息劵
@app.route('/v1/asset/<name_or_phone>/rate/pocket', methods=['GET', 'POST'])
# @auth.login_required
def get_rate_pocket_detail(name_or_phone):
    response_data = {}
    now_time = datetime.now()

    not_use = []
    already_use = []
    expire_date = []
    # # 未使用加息劵
    response_data = {}

    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    if not m:
        response_data["code"] = u"10002"
        response_data["desc"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)
    member_id = str(m.id).replace('-', '')
    hongbao_info = Member_red_pocket.query.filter_by(member_id=member_id).order_by(
        Member_red_pocket.generate_time.desc()).all()

    for i in hongbao_info:
        mrpt = Member_red_pocket_type.query.filter_by(id=i.sort_id).first()
        if int(mrpt.type) == 99:
            i.name = mrpt.name
            i.rules = mrpt.rules
            i.money = mrpt.money
            i.start_money = mrpt.start_money
            i.rate = mrpt.rate
            i.invest_days = mrpt.invest_days
            if i.is_use == 0 and i.is_freeze == 0 and i.generate_time >= now_time:
                not_use.append(i)
            elif i.is_use == 1 or i.is_freeze == 1:
                already_use.append(i)
            elif i.is_use == 0 and i.generate_time < now_time:
                expire_date.append(i)
        else:
            pass

    Now = datetime.now()

    query_top_123 = db.session.query(Product_info.id, Product_info.product_name, Product_info.product_type, Product_info.feature_id, Product_info.rate, Product_info.sell_time,
                                     Product_info.time_limit, Product_info.product_status, Product_info.raise_limit, Product_info.total_mount, Product_info.limit_mount, Product_info.is_recommend, Product_info.rate_increase)
    products_123 = query_top_123.filter(and_(Product_info.start_time <= Now,
                                            or_(Product_info.product_status == '2', Product_info.product_status == '3')
                                       )).order_by(Product_info.time_limit.desc(), Product_info.start_time.desc()).limit(20).first()

    response_data["code"] = u"10000"
    response_data["content"] =[]
    for item in not_use:

        response_data["content"].append(dict(id=item.id, name=item.name, rate=str(item.rate), \
                                        rules=item.rules, start_money=item.start_money+item.money, dead_time=str(item.generate_time), \
                                        is_freeze=item.is_freeze, is_use=item.is_use, type=0, product_id=str(products_123.id).replace("-", ""),is_new_product='1' if products_123.product_type == '新手标' else '0',invest_days=item.invest_days if item.invest_days else '30'))
    for item in already_use:
        response_data["content"].append(dict(id=item.id, name=item.name, rate=str(item.rate), \
                                        rules=item.rules, start_money=item.start_money+item.money, dead_time=str(item.generate_time), \
                                        is_freeze=item.is_freeze, is_use=item.is_use, type=1,is_new_product='',invest_days=item.invest_days if item.invest_days else '30'))
    for item in expire_date:
        response_data["content"].append(dict(id=item.id, name=item.name, rate=str(item.rate), \
                                        rules=item.rules, start_money=item.start_money+item.money, dead_time=str(item.generate_time), \
                                        is_freeze=item.is_freeze, is_use=item.is_use, type=2,is_new_product='',invest_days=item.invest_days if item.invest_days else '30'))

    response_data["desc"] = u"请求成功"
    return  toolkit.response(response_data, 200, None, True)


@app.route('/v1/asset/branch/bank/name', methods=['GET', 'POST'])
def get_branch_bank_name():

    llpr = LLPayRest()
    bank_code = request.form.get("bank_code", None)
    brabank_name = request.form.get("brabank_name", None)
    city_code = request.form.get("city_code", None)
    if bank_code is None or brabank_name is None or city_code is None:
        response_data = {}
        response_data["code"] = u"10001"
        response_data["desc"] = u"请求成功"
        response_data["content"] = []
        return  toolkit.response(response_data, 200, None, True)  
    res_dict = llpr.CNAPSCodeQuery(bank_code, brabank_name, city_code)
    return  toolkit.response(res_dict, 200, None, True)

@app.route('/v1/asset/member/top/five', methods=['GET', 'POST'])
def get_top_five():

    query_top = db.session.query(Member_asset_info.rechargeamount, Member_asset_info.remainamount, Member_asset_info.freezeamount, Member_asset_info.uncollectedamount,  Member.name)
    query_res = query_top.filter(Member.id == Member_asset_info.member_id).order_by((Member_asset_info.rechargeamount+Member_asset_info.remainamount+Member_asset_info.freezeamount+Member_asset_info.uncollectedamount).desc()).limit(5).all()

    return  toolkit.response(query_res, 200, None, True)

@app.route('/v1/asset/province/list', methods=['GET', 'POST'])
def get_province():

    query_top = db.session.query(Province_city.province, Province_city.code)
    query_res = query_top.filter().order_by(Province_city.code.asc()). group_by(Province_city.province).all()
    
    response_data = {}
    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    response_data["content"] = []
    for item in query_res:
        response_data["content"].append(dict(province=item[0], code=item[1]))

    return toolkit.response(response_data, 200, None, True)

@app.route('/v1/asset/province/or/city/<code>', methods=['GET', 'POST'])
def get_province_and_city_by_code(code):

    query_top = db.session.query(Province_city.province, Province_city.city)
    query_res = query_top.filter(Province_city.code == code).all()

    response_data = {}
    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    response_data["content"] = []
    for item in query_res:
        response_data["content"].append(dict(province=item[0], city=item[1]))
 
    return  toolkit.response(response_data, 200, None, True)

@app.route('/v1/asset/city/<code>', methods=['GET', 'POST'])
def get_city(code):

    p = Province_city.query.filter(Province_city.code == code).first()
    if p is not None:
        query_top = db.session.query(Province_city.city, Province_city.code)
        query_res = query_top.filter(Province_city.province == p.province).order_by(Province_city.code.desc()).all()
        response_data = {}
        response_data["code"] = u"10000"
        response_data["desc"] = u"请求成功"
        response_data["content"] = []
        for item in query_res:
            response_data["content"].append(dict(province=item[1], city=item[0]))

        return  toolkit.response(response_data, 200, None, True)
    else:
        response_data = {}
        response_data["code"] = u"0"
        response_data["code"] = u"city is not exist"
        return  toolkit.response(response_data, 200, None, True)

@app.route('/v1/asset/<name_or_phone>/WAP_llrecharge', methods=['GET', 'POST'])
@auth.login_required
def WAP_LL_charge(name_or_phone):

    real_name = request.form.get("real_name", None)
    id_card = request.form.get("id_card", None)
    charge_money = request.form.get("charge_money", None)
    bank_card = request.form.get("bank_card", None)
    user_ip = request.form.get("user_ip", None)
    charge_time = datetime.now()
    now_time = datetime.strftime(charge_time, '%Y-%m-%d %H:%M:%S')
    dt_order = datetime.strftime(charge_time, '%Y%m%d%H%M%S')
    response_data = {}
    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    llpr = LLPayRest(user_id=str(m.id).replace('-', ''))

    mrii = Member_real_info.query.filter(Member_real_info.real_identid == id_card).first()
    mpii = Member_pay_info.query.filter(Member_pay_info.pay_bankcard == bank_card).first()
    if mrii is not None and str(mrii.member_id) != str(m.id):
            response_data["code"] = u"19"
            response_data["content"] = u"身份证非法绑定"
            return toolkit.response(response_data, 200, None, True)
    if mpii is not None and str(mpii.member_id) != str(m.id):
            response_data["code"] = u"23"
            response_data["content"] = u"银行卡非法绑定"
            return toolkit.response(response_data, 200, None, True)


    order = Order_dict.query.filter_by(is_use = False).first()
    ch = '*'
    phone_s = m.phone[0:3] +4*ch + m.phone[7:11]

    name_goods = u"充值"
    info_order = u"用户%s于%s充值%s元, 手机号%s" % (m.name, now_time, charge_money, phone_s)
    no_order = order.order_id

    frms_ware_category = "2009"
    user_info_dt_register = datetime.strftime(m.reg_time, '%Y%m%d%H%M%S')
    # mport pdb
    # pdb.set_trace()

    llpr.setPayBaseParams_WX()
    llpr.setOrderParam(no_order=no_order, dt_order=dt_order, name_goods=name_goods, info_order=info_order, userreq_ip=user_ip.replace('.', '_'))
    llpr.setRiskItem_WAP(frms_ware_category, str(m.id).replace("-",""), user_info_dt_register, real_name, \
                     id_card,user_info_bind_phone=m.phone, user_info_identify_state="1", user_info_identify_type="1")

    mr = Member_recharge_info(member_id=str(m.id).replace('-', ''), member_name=m.name,
                              recharge_id=order.order_id, time=now_time, is_effect=0, money=charge_money,type=2)

    try:
        response_data = llpr.WAP_authPay(real_name, id_card, bank_card, charge_money )
        db.session.add(mr)
        db.session.commit()
        order.is_use = True
        db.session.merge(order)
        db.session.commit()

        return toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"] = u"3"
        response_data["content"] = u"数据库操作异常"
        return toolkit.response(response_data, 200, None, True)




# 抢红包攻略
@app.route('/v1/asset/strategy')
def strategy():
    return  render_template('/assets/rule.html')


# 注册协议
@app.route('/v1/asset/register/xieyi')
def zhucexieyi():
    render_data = {}
    render_data['time'] = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
    return  render_template('/assets/zhucexieyi.html', render_data=render_data)


# 平台声明
@app.route('/v1/asset/register/pingtaishengming')
def pingtaishengming():
    return  render_template('/assets/pingtaishengming.html')


# 银行限额
@app.route('/v1/asset/bank/xiane/<phone>')
def bank_xiane(phone):
    render_data = {'phone':phone}
    info_top = db.session.query(Member_pay_info.pay_bankcard,Member_pay_info.bank_name,Member,Member_bank_logo)
    info = info_top.filter(and_(Member.phone == phone,Member_pay_info.member_id == Member.id,
                                Member_pay_info.bank_code == Member_bank_logo.bank_code)).first()
    if info:
        card_number = info.pay_bankcard
        render_data['card_number'] = card_number[0:4] + ' **** **** '+ card_number[-4:]
        render_data['bank_name'] = info.bank_name
        render_data['signle_amt']  = float(info[3].single_amt) / 10000.0
        render_data['day_amt'] = float(info[3].day_amt) / 10000.0
        render_data['month_amt'] = float(info[3].month_amt) / 10000.0
        render_data['bank_img'] = 'BANK' + info[3].bank_code + '.png'
    return render_template('/bank/xiane.html', render_data=render_data)

# 银行限额json
@app.route('/v1/asset/bank/info/<phone>')
def bank_info(phone):
    render_data = {'phone':phone}
    info_top = db.session.query(Member_pay_info.pay_bankcard,Member_pay_info.bank_name,Member,Member_bank_logo)
    info = info_top.filter(and_(Member.phone == phone,Member_pay_info.member_id == Member.id,
                                Member_pay_info.bank_code == Member_bank_logo.bank_code)).first()
    if info:
        card_number = info.pay_bankcard
        render_data['card_number'] = card_number[0:4] + ' **** **** '+ card_number[-4:]
        render_data['bank_name'] = info.bank_name
        render_data['signle_amt']  = float(info[3].single_amt) / 10000.0
        render_data['day_amt'] = float(info[3].day_amt) / 10000.0
        render_data['month_amt'] = float(info[3].month_amt) / 10000.0
        render_data['bank_img'] = BOLUO_URL + info[3].logo
    return toolkit.response(render_data, 200, None, True)

# 提现声明
@app.route('/v1/asset/fetch')
def fetch():
    return render_template('/assets/fetch.html')


# 返回银行卡logo
@app.route('/v1/asset/bank_logo')
def bank_logo():
    code = request.form.get('code',None)
    response_data = {}
    bank_logo = Member_bank_logo.query.filter_by(bank_code=code).first()
    if bank_logo:
        response_data['code'] = u'10000'
        response_data['desc'] = u'成功'
        response_data['address'] = BOLUO_URL + bank_logo.logo
    else:
        response_data['code'] = u'10001'
        response_data['desc'] = u'code值不存在'
        response_data[''] = u''
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/asset/bank_support/<page>',methods=['GET', 'POST'])
def bank_support(page):
    offset = (int(page) - 1) * 10
    response_data = {}
    try:
        bank_info = db.session.query(Member_bank_logo).offset(offset).limit(10).all()
        resultarray = []
        for bank in bank_info:
            resultdict = {}
            resultdict['url'] = BOLUO_URL + bank.logo
            resultdict['name'] = bank.bank
            resultdict['single_amt'] = bank.single_amt
            resultdict['day_amt'] = bank.day_amt
            resultdict['month_amt'] = bank.month_amt
            resultarray.append(resultdict)
        response_data['code'] = u'10000'
        response_data['desc'] = u'成功'
        response_data['content'] = resultarray
    except Exception as e:
        response_data['code'] = u'10004'
        response_data['desc'] = u'数据库操作失败'
        response_data['content'] = []
    return toolkit.response(response_data, 200, None, True)
