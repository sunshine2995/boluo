#!/use/bin/env python
# -*- coding: UTF-8 -*-

import urllib
import requests
from datetime import datetime, timedelta
from random import randint
import time

from flask import render_template
from flask import request, g
from flask_httpauth import HTTPBasicAuth
from sqlalchemy import and_, or_, func

from apps import app
from config import BOLUO_URL, AUTO_PRODUCT_URL
from apps.member.models import Member, Member_real_info, Member_login, Member_pay_info, Member_bank_logo, Member_invite_info
from apps.product.models import Product_info, Invest_info, Borrower_info, Product_image, \
                                Contract, Product_new, Feature_info, Account_info
from apps.product.utils import is_new_member
from apps.asset.models import Member_asset_info, Order_dict, Member_income_statement,\
                              Member_red_pocket, Member_red_pocket_type, Member_recharge_info, Member_reflect_info
from apps.news.models import News, Sort
from apps.rewards.models import Activity
from apps.utils import toolkit

from apps.utils.message import send_message
from apps.dbinstance import db
from apps.activity.models import Zillionaire_info, Points_change
from apps.activity.utils import update_activity_status
from apps.product.utils import cncurrency,check_idcard,check_rate
from apps.product.views import calculate_percentage
from apps.message.models import Error_log


def xw_activity_order(name_or_phone, order_id):
    invest_info = Invest_info.query.filter_by(order_id=order_id).first()

    total_fee = invest_info.money
    red_pocket_val = invest_info.hongbao
    product_id = invest_info.product_id

    pro = Product_info.query.filter_by(id = product_id).first()
    m = Member.query.filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).first()
    now_time = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
    try:
        rp = Member_red_pocket.query.filter_by(id=invest_info.hongbao_info_id).first()
        rpt = Member_red_pocket_type.query.filter_by(id=rp.sort_id).first()
        rpt_name = rpt.name
    except:
        rpt_name = ''

    # 是否送摇色子机会
    increasebool = False
    increase_num = 0

    total_fee_all = float(total_fee) + red_pocket_val

    if pro.product_type == '新手标':
        is_new_product = True
    else:
        is_new_product = False

    # 大富翁活动期间送骰子次数
    bldfw = Activity.query.filter_by(name='大富翁活动').first()
    if bldfw and bldfw.start_time < datetime.now() < bldfw.end_time and not is_new_product:
        bldfw_zill = Zillionaire_info.query.filter_by(phone=name_or_phone, activity_id=bldfw.id).first()
        if bldfw_zill is None:
            bldfw_zill = Zillionaire_info(phone=name_or_phone, activity_id=bldfw.id)
            db.session.add(bldfw_zill)
            db.session.commit()
        bldfw_zill.investment += total_fee_all

        if pro.time_limit == '30' and total_fee_all >= 5000:
            increasebool = True
            increase_num = int(total_fee_all / 5000)
        elif pro.time_limit == '60' and total_fee_all >= 5000:
            increasebool = True
            increase_num = int(total_fee_all / 5000)
        elif pro.time_limit == '90' and total_fee_all >= 5000:
            increasebool = True
            increase_num = int(total_fee_all / 5000)
        elif pro.time_limit == '180' and total_fee_all >= 5000:
            increasebool = True
            increase_num = int(total_fee_all / 5000)

        if increasebool:
            bldfw_zill.use_number += increase_num

        db.session.merge(bldfw_zill)

    asset = Member_asset_info.query.filter(Member_asset_info.member_id == str(m.id).replace('-','')).first()

    if not is_new_product:
        hscore = int(total_fee_all / 10)
        asset.score += hscore
        change = Points_change(phone=name_or_phone, time=datetime.now(), score=hscore, type=0, description='投资')
        db.session.add(change)

    if float(calculate_percentage(product_id)) == float(pro.total_mount):
        pro.product_status = "3"

    if asset.rechargeamount >= float(total_fee):
        asset.rechargeamount = float(asset.rechargeamount)-float(total_fee)
    else:
        asset.remainamount = asset.remainamount + asset.rechargeamount-float(total_fee)
        asset.rechargeamount = 0.0

    asset.freezeamount = float(asset.freezeamount) + float(total_fee) + red_pocket_val
    balance = asset.remainamount + asset.rechargeamount

    ttype = u"投资"
    info = u"冻结账户余额 %s" % total_fee
    ins = Member_income_statement(member_id=str(m.id).replace('-',''), type=ttype, money=total_fee, \
                                  balance=balance, time=now_time, info=info, order_id=order_id,\
                                  product_info=pro.product_name, phone=m.phone)
    db.session.add(ins)

    if red_pocket_val > 0.0:
        type = u"红包"
        info = u"冻结红包金额 %s" % red_pocket_val
        ins = Member_income_statement(member_id=str(m.id).replace('-',''), type=type, money=red_pocket_val, \
                                      balance=balance, time=now_time, info=info, order_id=order_id,\
                                      product_info=rpt_name,phone=m.phone)
        db.session.add(ins)

    db.session.merge(pro)
    db.session.merge(asset)
    db.session.commit()

    tem_id = 80335
    query_res = Member_real_info.query.join(Member).filter(
        or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()

    sex = str(query_res.sex)
    if sex == 'M':
        datas = [query_res.real_name[0:1].encode("utf-8") + u'先生']
    elif sex == 'F':
        datas = [query_res.real_name[0:1].encode("utf-8") + u'女士']
    else:
        datas = [query_res.real_name[0:1].encode("utf-8") + u'先生/女士']
    send_message(m.phone, datas, tem_id)


@app.route('/v1/xinwang/order/<name_or_phone>', methods=['GET', 'POST'])
def xinwang_order(name_or_phone, order_id=None, product_id=None, total_fee=None, red_pocket_id=None):
    product_id = request.form.get("product_id", product_id)
    total_fee = request.form.get("total_fee", total_fee)
    red_pocket_id = request.form.get("red_pocket_id", red_pocket_id)
    total_fee = float(total_fee)
    response_data = {}

    if not product_id or not total_fee:
        response_data["code"] = u"10001"
        response_data["desc"] = u"参数字段不能为空"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)
    m = Member.query.filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).first()

    if int(m.is_identity_bind) == 0:
        response_data["code"] = u"10018"
        response_data["desc"] = u"用户未认证"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)
    try:
        if total_fee < 1:
            response_data["code"] = u"10003"
            response_data["desc"] = u"交易金额不能小于1元"
            response_data["content"] = {}
            return toolkit.response(response_data, 200, None, True)
        elif float(total_fee) > 100000:
            response_data["code"] = u"10026"
            response_data["desc"] = u"交易金额不能大于100000元"
            response_data["content"] = {}
            return toolkit.response(response_data, 200, None, True)
    except:
        pass

    asset = Member_asset_info.query.filter(Member_asset_info.member_id == str(m.id).replace('-','')).first()



    pro = Product_info.query.filter_by(id = product_id).first()
    if pro is None:
        response_data["code"] = u"10021"
        response_data["desc"] = u"该产品不存在"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    if pro.product_type == '新手标':
        is_new_product = True
    else:
        is_new_product = False

    if is_new_product:
        if is_new_member(name_or_phone) == 'false':
            response_data["code"] = u"10022"
            response_data["desc"] = u"您已经不是新手了"
            response_data["content"] = {}
            return toolkit.response(response_data, 200, None, True)

    if total_fee > pro.limit_mount:
        response_data["code"] = u"10023"
        response_data["desc"] = u"新手标限额%s" % pro.limit_mount
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    has_total_total = total_fee + float(calculate_percentage(product_id))

    if has_total_total > float(pro.total_mount):
        response_data["code"] = u"10013"
        response_data["desc"] = u"投资总额已达上限"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    # -----------------------------使用红包------------------------------------


    rp = None
    rpt = None

    # 额外加息
    qg_rate = 0.0
    is_rate_pocket_val = False
    red_pocket_val = 0.0
    rate_security = 0.0
    # 可以用红包但不是新手
    hongbao_source = ''
    if red_pocket_id:
        if not is_new_product:
            query_top = db.session.query(Member_red_pocket_type, Member_red_pocket)
            query_res = query_top.filter(and_(Member_red_pocket.sort_id == Member_red_pocket_type.id, \
                                              Member_red_pocket.id == red_pocket_id)).all()
            if len(query_res)==0 or query_res is None:
                response_data["code"] = u"10008"
                response_data["desc"] = u"红包不存在,请检查错误"
                response_data["content"] = {}
                return toolkit.response(response_data, 200, None, True)
            elif len(query_res) > 1:
                response_data["code"] = u"10007"
                response_data["desc"] = u"存在多个红包,请检查错误"
                response_data["content"] = {}
                return toolkit.response(response_data, 200, None, True)
            else:
                rp = query_res[0][1]
                if rp.generate_time < datetime.now():
                    response_data["code"] = u"10008"
                    response_data["desc"] = u"红包不存在,请检查错误"
                    response_data["content"] = {}
                    return toolkit.response(response_data, 200, None, True)

                rpt = query_res[0][0]

                if int(rpt.invest_days) > int(pro.time_limit):
                    response_data["code"] = u"10008"
                    response_data["desc"] = u"该红包不适用于当前期限的项目"
                    response_data["content"] = {}
                    return toolkit.response(response_data, 200, None, True)

                if rpt.type == '99' and total_fee >= float(query_res[0][0].start_money):
                    rate_security = float(query_res[0][0].rate)
                    red_pocket_val = round(total_fee*rate_security*float(pro.time_limit)/360.0, 2)
                    total_fee_jhb = total_fee - red_pocket_val
                else:
                    red_pocket_val = float(query_res[0][0].money)
                    red_pocket_val_start_money = float(query_res[0][0].start_money)
                    total_fee_jhb = total_fee - red_pocket_val
                    if rp.is_freeze:
                        response_data["code"] = u"10007"
                        response_data["desc"] = u"红包已使用,请检查错误"
                        response_data["content"] = {}
                        return toolkit.response(response_data, 200, None, True)

                    if total_fee >= red_pocket_val_start_money:
                        pass
                    else:
                        response_data["code"] = u"10016"
                        response_data["desc"] = u"%s元红包的起投金额为%s, 请重新选择!" % (query_res[0][0].money, int(red_pocket_val_start_money+query_res[0][0].money))
                        response_data["content"] = {}
                        return toolkit.response(response_data, 200, None, True)
                hongbao_source = query_res[0][0].name
        else:
            response_data["code"] = u"10025"
            response_data["desc"] = u"新手不能使用红包"
            response_data["content"] = {}
            return toolkit.response(response_data, 200, None, True)
    else:
        total_fee_jhb = total_fee

    if asset.remainamount + asset.rechargeamount < total_fee_jhb:
        response_data["code"] = u"10015"
        response_data["desc"] = u"账户余额不够,请充值"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    # 抢购加息
    if total_fee <= 10000 and total_fee + float(calculate_percentage(product_id)) + 0.1 >= float(pro.total_mount):
        qg_rate += 0.01

    # 红包ID
    if rp:
        hongbao_info_id = rp.id
    else:
        hongbao_info_id = None

# -----------------------------end使用红包------------------------------------

    inv = Invest_info(member_id=str(m.id).replace('-',''), money=total_fee_jhb, hongbao=red_pocket_val,\
                      member_name=m.name, hongbao_source=hongbao_source, hongbao_info_id=hongbao_info_id)

    if Member_invite_info.query.filter_by(invited_id=str(m.id).replace('-','')).first():
        inv.yaoqing_money = round(total_fee_jhb*0.01*float(pro.time_limit)/360.0, 2)

    # 默认为投资中
    inv.status = 1
    inv.product_id = product_id
    inv.is_effect = 0
    # 会员加息
    if m.level == 1:
        qg_rate += 0.01

    # 计算总收益
    pro_fit = round(total_fee_jhb + red_pocket_val + float(total_fee_jhb*(float(pro.rate)+float(pro.rate_increase)+qg_rate)*float(pro.time_limit)/360.0),2)
    # 普通收益
    inv.interest = round(total_fee_jhb*float(pro.rate)*float(pro.time_limit)/360.0, 2)
    # 活动收益
    inv.activity_interest = round(total_fee_jhb*(float(pro.rate_increase)+qg_rate)*float(pro.time_limit)/360.0, 2)

    inv.profit = pro_fit
    inv.time = datetime.now()
    inv.expect_time = inv.time + timedelta(days=int(pro.time_limit))
    if order_id:
        inv.order_id = order_id
    else:
        inv.order_id = "%d%06d" % (time.time() * 1000000, randint(0, 999999))
    inv.bluuid = m.bluuid
    inv.rate_security = rate_security
    inv.extra_rate = qg_rate
    mlogin = Member_login.query.filter(Member_login.member_id==m.id).order_by(Member_login.last_time.desc()).first()
    if mlogin:
        inv.equipment = mlogin.equipment_name
    else:
        inv.equipment = 'app'
    inv.channel = m.channel_id

    try:
        db.session.add(inv)
        db.session.commit()
        db.session.merge(pro)
        db.session.commit()

        response_data['order_id'] = inv.order_id
        response_data['red_pocket_val'] = red_pocket_val
        response_data["code"] = u"10000"
        response_data["desc"] = u"数据库操作成功"
        response_data["content"] = {}
    except Exception, e:
        error = Error_log(phone=name_or_phone, type=u'下订单', description=str(e), creat_time=datetime.now())
        db.session.add(error)
        db.session.commit()
        response_data["code"] = u"10004"
        response_data["content"] = u"数据库操作失败"
        response_data["content"] = {}
    print response_data
    return toolkit.response(response_data, 200, None, True)


@app.route('/xinwang/invest/order/info/<path>', methods=['GET', 'POST'])
def xw_invest_info(path):
    response_data = {'is_effect': '0'}
    order_id = request.args.get('order_id')
    if path == 'user_pre_transaction':
        inv = Invest_info.query.filter_by(order_id=order_id).first()
        if inv:
            pro_info = Product_info.query.filter_by(id=inv.product_id).first()
            response_data['is_effect'] = inv.is_effect
            response_data['product_name'] = pro_info.product_name
            response_data['time_limit'] = '%s天' % pro_info.time_limit
            response_data['money'] = '%s元' % inv.money
            response_data['rate'] = '%s' % ((pro_info.rate+pro_info.rate_increase) * 100) + '%'
    elif path == 'recharge':
        mri = Member_recharge_info.query.filter_by(recharge_id=order_id).first()
        if mri:
            response_data['is_effect'] = mri.is_effect
            response_data['money'] = '%s元' % mri.money
    elif path == 'withdraw':
        mri = Member_reflect_info.query.filter_by(reflect_id=order_id).first()
        if mri:
            if mri.type == 1:
                response_data['is_effect'] = '1'
                response_data['money'] = '%s' % mri.money
            else:
                response_data['is_effect'] = '0'
    elif path == 'register':
        member = Member.query.filter_by(id=order_id).first()
        if member.is_register_xinwang == '1' and member.is_pay_bind == '1' and member.is_identity_bind == '1':
            response_data['is_effect'] = '1'

    return toolkit.response(response_data, 200, None, True)

