#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import time
import json
import base64
from random import randint
from random import choice
import uuid
import functools

from sqlalchemy import and_, or_, func

from flask import request, make_response, redirect, url_for
import requests
from M2Crypto.RSA import RSAError

from apps import app
from apps.utils import toolkit
from .xwsdk.sign import sha1withRSA, check_sign
from apps.dbinstance import db
from .models import CallbackInformation
from apps.member.models import Member, Member_real_info, Member_pay_info, Member_login, Member_bank_logo
from .id_card.id import get_address, id_card_verify
from apps.asset.models import Member_recharge_info, Member_reflect_info, Member_asset_info, \
    Member_income_statement, Member_red_pocket, Member_red_pocket_type
import config
from flask import render_template
from apps.product.views import order
from apps.product.xinv import xw_activity_order

import urllib, urllib2
from apps.product.models import Invest_info, Product_info, Borrower_info
from config import PLATFORMNO, XW_API_URI, XW_URI_HTML, XW_JAVA_URL, PayCompany

############################################################
#
#   utils
#
############################################################


# 用户类型
USER_ROLE = {
    "GUARANTEECORP": "担保机构",
    "INVESTOR": "投资人",
    "BORROWERS": "借款人",
    "INTERMEDIATOR": "居间人",
    "COLLABORATOR": "合作机构",
    "SUPPLIER": "供应商",
    "PLATFORM_COMPENSATORY": "平台代偿账户",
    "PLATFORM_MARKETING": "平台营销款账户",
    "PLATFORM_PROFIT": "平台分润账户",
    "PLATFORM_INCOME": "平台收入账户",
    "PLATFORM_INTEREST": "平台派息账户",
    "PLATFORM_ALTERNATIVE_RECHARGE": "平台代充值账户",
    "PLATFORM_FUNDS_TRANSFER": "平台总账户",
}


# 授权类型
AUTH_TYPE = {
    "TENDER": "自动投标",
    "REPAYMENT": "自动还款",
    "CREDIT_ASSIGNMENT": "自动债权认购",
    "COMPENSATORY": "自动代偿",
    "WITHDRAW": "自动提现",
    "RECHARGE": "自动充值",
}


# 银行编码
BANK_CODE = {
    "ABOC": "农业银行",  # 中国农业银行
    "BKCH": "中国银行",
    "CIBK": "中信银行",
    "EVER": "光大银行", # 中国光大银行
    "FJIB": "兴业银行",  #
    "GDBK": "广发银行",
    "HXBK": "华夏银行",
    "ICBK": "工商银行",  # 中国工商银行
    "MSBC": "民生银行",  # 中国民生银行
    "SZDB": "平安银行",
    "SPDB": "浦发银行",
    "CMBC": "招商银行",
    "PCBC": "建设银行",  # 中国建设银行
    "PSBC": "邮政储蓄银行",  # 中国邮政储蓄银行Y
    "BJCN": "北京银行",
    "COMM": "交通银行",
}


# 鉴权通过类型
ACCESS_TYPE = {
    "FULL_CHECKED": "四要素验证通过",
    "NOT_AUTH": "未鉴权",
    "AUDIT_AUTH": "特殊用户认证",
}

# 审核状态
AUDIT_STATUS = {
    "AUDIT": "审核中",
    "PASSED": "审核通过",
    "BACK": "审核回退",
    "REFUSED": "审核拒绝",
}


# 偏好支付公司
PAY_COMPANY = {
    "YEEPAY": "易宝支付",
    "FUIOU": "富友支付",
    "ALLINPAY": "通联支付",
    "CHINAGPAY": "爱农支付",
    "TFTPAY": "腾付通",
    "UCFPAY": "先锋支付",
    "BAOFOO": "宝付",
}


# 支付方式
RECHARGE_WAY = {
    "WEB": "网银",
    "SWIFT": "快捷支付",
    "BANK": "转账充值，仅适用迁移场景，调用单笔充值订单查询接口返回",
    "BACKROLL": "资金回退充值",
    "PROXY": "自动充值",
}


# 支付方式
PAY_TYPE = {
    "B2C": "个人网银",
    "B2B": "企业网银",
}


# 交易类型
TRADE_TYPE = {
    "TENDER": "投标",
    "REPAYMENT": "还款",
    "CREDIT_ASSIGNMENT": "债权认购",
    "COMPENSATORY": "直接代偿",
    "INDIRECT_COMPENSATORY": "间接代偿",
    "PLATFORM_INDEPENDENT_PROFIT": "独立分润",
    "MARKETING": "平台营销款",
    "PLATFORM_SERVICE_DEDUCT": "收费",
    "FUNDS_TRANSFER": "平台资金划拨",
}


# 预处理类型
PRE_TRANSACTION_TYPE = {
    "TENDER": "投标",
    "REPAYMENT": "还款",
    "CREDIT_ASSIGNMENT": "债权认购",
    "COMPENSATORY": "代偿"
}


# 提现方式
WITHDRAW_TYPE = {
    "NORMAL": "正常提现，T+1 天到账",
}


# 提现交易状态
WITHDRAW_STATUS = {
    "CONFIRMING": "待确认",
    "ACCEPT": "已受理",
    "REMITING": "出款中",
    "SUCCESS": "提现成功",
    "FAIL": "提现失败",
    "ACCEPT_FAIL": "受理失败",
}


def get_callback_url02(request):
    """
    获取回调地址，在当前请求地址后加上_callback

    :return: 回调地址
    :rtype: str
    """
    return config.BOLUO_URL + request.path + "/callback/html"


class toolkitxxx():
    @classmethod
    def response(cls, request_data, code, _, True):
        request_data['XW_URI_HTML'] = XW_URI_HTML
        return render_template('xinwang/gateway.html', **request_data)


def base_params(serviceName, reqData):
    """
    请求参数格式

    :param serviceName: 接口名称，见每个接口的详细定义
    :param reqData: 业务数据报文，JSON 格式，具体见各接口定义
    :return:
    """
    reqData = json.dumps(reqData)
    result = {
        "serviceName": serviceName,
        "platformNo": PLATFORMNO,
        "reqData": reqData,
        "userDevice": 'MOBILE',
        "keySerial": 1,
        "sign": sha1withRSA(reqData)
    }
    return result


def parse_callback(request):
    """
    解析回调结果

    :param request:
    :return:
    """
    params = {}
    if request.data:
        for line in request.data.split("&"):
            key, value = line.split("=")
            key = unquote(key)
            value = unquote(value)
            params[key] = value
    else:
        for key in ("platformNo", "serviceName", "responseType", "keySerial", "respData", "userDevice", "sign"):
            params[key] = request.form.get(key, None)
    respData = params["respData"]
    if isinstance(respData, unicode):
        respData = respData.encode("utf8")
    sign = base64.decodestring(params["sign"])
    try:
        if check_sign(respData, sign) == 0:
            # TODO: 签名未验证通过，可能是伪造请求
            print "签名不正确"
    except RSAError:
        # TODO: 验证不通过
        print "签名不正确2"
    params["respData"] = json.loads(params["respData"])
    return params


CALLBACK_TYPE = {
    "PERSONAL_REGISTER_EXPAND": 1,  # 注册绑卡回调
    "PERSONAL_BIND_BANKCARD_EXPAND": 2,  # 个人绑卡回调
    "UNBIND_BANKCARD": 3,  # 银行卡解绑回调
    "RECHARGE": 4,  # 充值回调
    "WITHDRAW": 5,  # 提现回调
    "RESET_PASSWORD": 6,  # 修改密码回调
    "USER_AUTHORIZATION": 7,   # 用户授权回调
    "MODIFY_MOBILE_EXPAND": 8,  # 预留手机号更新
    "CHECK_PASSWORD": 9, # 验证密码
    "USER_PRE_TRANSACTION": 10,  # 用户预处理
    "ACTIVATE_STOCKED_USER": 11,  # 用户激活
    "USER_AUTO_PRE_TRANSACTION": 12  # 充值授权下订单
}


def xinwang_register_required(func):
    """
    用户ID需要在新网注册过的装饰器

    :param func:
    :return:
    """

    @functools.wraps(func)
    def wrapper():
        """
        检查是用户ID是否在新网注册过的闭包函数
        """
        # TODO: user_id 应该是 session 中获取的
        phone = request.args.get("phone", None)
        response_data = {}
        if len(phone) != 11:
            return make_response("Not Found", 404)

        user = Member.query.filter(Member.phone == phone).first()
        if not user:
            print '-------------------%s--------------------用户不存在' % phone
            response_data["code"] = u"10002"
            response_data["desc"] = u"用户不存在"
            return toolkit.response(response_data, 200, None, True)
        elif not user.is_register_xinwang :
            print '-------------------%s--------------------用户未在新网注册，请注册后再操作' % phone
            response_data["code"] = u"10001"
            response_data["desc"] = u"用户未在新网注册，请注册后再操作"
            return toolkit.response(response_data, 200, None, True)

        # FIXME:
        request.xinwang_user = user
        return func()

    return wrapper


def gen_request_no():
    """
    生成 请求流水号

    :return:
    """
    return "%d%06d" % (time.time() * 1000000, randint(0, 999999))


def is_handled(requestNo):
    """
    判断 callback 是否处理过，因为 callback 会同时通过 浏览器回调和服务通知

    :param requestNo: 请求流水号
    """
    callback = CallbackInformation.query.filter(CallbackInformation.requestNo == requestNo).first()

    if callback:
        response_data = {
            "code": u"10014",
            "desc": "已处理过的请求",
            "content": {}
        }
        return toolkit.response(response_data, 200, None, True)
    return None


def get_callback_url(request):
    return config.BOLUO_URL + "/xinwang/callback/html/" + request.path.replace('/v1/xinwang/', '')


@app.route('/xinwang/callback/html/<url_name>', methods=["GET", "POST"])
def callback_html(url_name):
    order_id = request.args.get('order_id')
    return redirect(config.BOLUO_URL +
                    '/static/h5/xinwang/%s/%s.html?order_id=%s' % (url_name, url_name, order_id))


############################################################
#
#   用户注册绑卡
#
############################################################


# -----------------------------------------------用户注册绑卡-----------------------------------------------
# -----------------------------------------------用户注册绑卡-----------------------------------------------
# -----------------------------------------------用户注册绑卡-----------------------------------------------

# 用户注册绑卡
@app.route('/v1/xinwang/register', methods=["GET", "POST"])
def xw_register():
    callback = get_callback_url(request)
    serviceName = "PERSONAL_REGISTER_EXPAND"

    phone = request.args.get("phone", "")   # 绑卡注册的用户ID
    user_role = request.args.get("user_role", "INVESTOR")
    binfo_has = Borrower_info.query.filter_by(mobile=phone).first()
    if binfo_has:
        user_role = 'BORROWERS'

    if len(phone) != 11:
        return make_response("Not Found", 404)

    user = Member.query.filter(Member.phone == phone).first()
    response_data = {}
    if not user:
        response_data["code"] = u"10002"
        response_data["desc"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)
    elif user.is_register_xinwang == 1:
        response_data["code"] = u"10003"
        response_data["desc"] = u"用户已在新网注册，不用再注册"
        return toolkit.response(response_data, 200, None, True)

    auth_list = request.args.get("auth_list", "WITHDRAW")
    auth_list = auth_list.upper()

    reqData = {
        "platformUserNo": str(user.id).replace('-', ''),     # 用户ID
        # "platformUserNo": '31fb0bfb50214fc2b4cd0365992adcf1',     # 用户ID
        "requestNo": gen_request_no(),          # 请求流水号
        "idCardType": "PRC_ID",         # 身份证
        "userRole": user_role,        # USER_ROLE 类型
        "checkType": "LIMIT",           # 鉴权验证类型，默认填 LIMIT(强制四要素)，即四要素完全通过(姓名、身份证 号、银行卡号，银行预留手机号) 方可更新手机号成功
        "redirectUrl": callback + '?order_id=%s' % str(user.id).replace('-', ''),        # 回调地址
        "userLimitType": "ID_CARD_NO_UNIQUE",
        "authList": auth_list,          # 用户权限， AUTH_TYPE 列表
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }
    request_data = base_params(serviceName, reqData)
    request_data['xw_url'] = XW_URI_HTML
    return toolkit.response(request_data, 200, None, True)


def register_callback():
    response_data = parse_callback(request)
    respData = response_data["respData"]

    # 根据请求流水号判断是哪次请求
    requestNo = respData["requestNo"]  # 请求流水号
    code = respData["code"]  # 调用状态(0 为调用成功、1 为失败，返回 1 时请看【调用失败错误码】及错误码 描述)
    status = respData[
        "status"]  # 业务处理状态(处理失败 INIT;处理成功 SUCCESS)，平台可根据非 SUCCESS 状态做相应处理，处理失败时可参考错误码及描述
    errorCode = respData.get("errorCode", "")  # 错误码
    errorMessage = respData.get("errorMessage", "")  # 错误码描述
    platformUserNo = str(respData["platformUserNo"])  # 平台用户编号
    realName = respData["realName"]  # 用户真实姓名
    idCardType = respData["idCardType"]  # 见【证件类型】
    userRole = respData["userRole"]  # 见【用户角色】, USER_ROLE
    idCardNo = respData["idCardNo"]  # 用户证件号
    mobile = respData["mobile"]  # 银行预留手机号
    bankcardNo = respData["bankcardNo"]  # 银行卡号
    bankcode = respData["bankcode"]  # 银行编码, BANK_CODE
    accessType = respData["accessType"]  # 见【鉴权通过类型】, ACCESS_TYPE

    # TODO: 用户审核状态可能没通过
    auditStatus = respData["auditStatus"]  # 见【审核状态】, AUDIT_STATUS

    handled = is_handled(requestNo)
    if handled:
        return handled
    callback = CallbackInformation(
        requestNo='%s-%s' % (requestNo, platformUserNo),
        code=code,
        type=CALLBACK_TYPE[response_data["serviceName"]],
        status=status,
        phone=mobile,
        errorCode=errorCode,
        errorMessage=errorMessage,
        accessType=accessType
    )
    db.session.add(callback)
    db.session.commit()

    mbl = Member_bank_logo.query.filter_by(bank_code2=bankcode).first()
    bank_name = mbl.bank
    user = Member.query.filter_by(id=platformUserNo).first()

    if user and status == 'SUCCESS':
        province, city, district = get_address(idCardNo)
        address = province + city + district
        birthday = idCardNo[6:14]
        # 性别位为奇数是男性
        if int(idCardNo[-2]) / 2  == 0:
            sex = "f"
        else:
            sex = "m"

        mri = Member_real_info.query.filter(Member_real_info.member_id==platformUserNo).first()
        # 记录不存在，则创建
        if not mri:
            mri = Member_real_info(
                member_id=platformUserNo, real_name=realName, real_identid=idCardNo,
                address=address, sex=sex, birthday=birthday, create_time=datetime.datetime.now())
            db.session.add(mri)
        else:
            mri.real_name=realName
            mri.real_identid=idCardNo
            mri.address=address
            mri.sex=sex
            mri.birthday=birthday
            db.session.merge(mri)

        user.is_register_xinwang = 1
        user.is_pay_bind = 1
        user.is_identity_bind = 1
        user.xinwang_create_time = datetime.datetime.now()
        db.session.merge(user)

        # 创建用户绑卡信息表
        member_pay_info = Member_pay_info.query.filter(Member_pay_info.member_id==platformUserNo).first()
        if member_pay_info:
            member_pay_info.pay_bankcard=bankcardNo
            member_pay_info.account_holder=realName
            member_pay_info.bank_name=bank_name
            member_pay_info.bank_code=bankcode
            member_pay_info.phone=mobile
            member_pay_info.card_type=idCardType
            member_pay_info.province=province
            member_pay_info.city=city
            db.session.merge(member_pay_info)
        else:
            member_pay_info = Member_pay_info(
                member_id=platformUserNo, pay_bankcard=bankcardNo, account_holder=realName,
                bank_name=bank_name, bank_deposit="", bank_address="",
                bank_code=bankcode, phone=mobile, card_type=idCardType, province=province, city=city,
                single_amt="", day_amt="", month_amt=""
            )
            db.session.add(member_pay_info)

    db.session.commit()

    return toolkit.response(response_data, 200, None, True)


# -----------------------------------------------充值-----------------------------------------------
# -----------------------------------------------充值-----------------------------------------------
# -----------------------------------------------充值-----------------------------------------------


# 充值
@app.route('/v1/xinwang/recharge', methods=["GET", "POST"])
@xinwang_register_required
def recharge():
    callback = get_callback_url(request)
    serviceName = "RECHARGE"
    phone = request.args.get("phone")  # 绑卡注册的用户ID
    amount = request.args.get("amount", "1")
    red_pocket_id = request.args.get("red_pocket_id", None)
    # commission = "%.2f" % (float(amount) * 0.01)  # 手续费
    authtenderAmount = request.args.get("authtenderAmount", None)
    projectNo = request.args.get("projectNo", None)

    member = Member.query.filter(Member.phone == phone).first()
    member_pay_info = Member_pay_info.query.filter(Member_pay_info.member_id == member.id).first()

    if member.is_pay_bind == 0:
        response_data = {
            "code": u"10004",
            "content": {},
            "desc": u"未绑定银行卡"}
        return toolkit.response(response_data, 200, None, True)

    recharge_id = gen_request_no()

    mri = Member_recharge_info.query.filter_by(recharge_id=recharge_id).first()
    if mri:
        response_data = {
            "code": u"10001",
            "content": {},
            "desc": u"订单号已存在"}
        return toolkit.response(response_data, 200, None, True)

    mbl = Member_bank_logo.query.filter_by(bank_code=member_pay_info.bank_code).first()
    if mbl:
        member_pay_info.bank_code = mbl.bank_code2
        db.session.merge(member_pay_info)

    member_id = str(member.id).replace('-', '')
    amount = float(amount)

    reqData = {
        "platformUserNo": member_id,  # 用户ID
        "requestNo": recharge_id,  # 请求流水号
        "amount": amount,  # 充值金额
        # "commission": commission,  # 平台佣金
        "expectPayCompany": PayCompany, # choice(PAY_COMPANY.keys()),  # 偏好支付公司，见【支付公司】
        "rechargeWay": "SWIFT",  # 【支付方式】，支持网银(WEB)、快捷支付(SWIFT)
        "bankcode": member_pay_info.bank_code,   # 若支付方式为快捷支付，此处必填;若支付方式为网银，此处可以 不填;网银支付方式下，若此处填写，则直接跳转至银行页面，不填则跳转至支付公司收银台页面;
        "payType": 'B2C',  # 若支付方式填写为网银，且对【银行编码】进行了填写，则此处必填。
        # "authtradeType": choice(TRADE_TYPE.keys()),  #【授权交易类型】，若想实现充值+投标单次授权，则此参数必传，固定“TENDER”,
        # "authtenderAmount": ["1.0", "500000.0"],  # 授权投标金额，充值成功后可操作对应金额范围内的投标授权预处理;若传入了【授 权交易类型】，则此参数必传;,
        # "projectNo": "10001", # 标的号;若传入了【授权交易类型】，则此参数必传。,
        "expired": (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y%m%d%H%M%S"),   # 超过此时间即页面过期,
        # "callbackMode": "DIRECT_CALLBACK",  # 快捷充值回调模式，如传入 DIRECT_CALLBACK，则订单支付不论成功、失败、 处理中均直接同步、异步通知商户;未传入订单仅在支付成功时通知商户;,
        # "redirectUrl": callback,  # 回调地址
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }

    if projectNo:
        redata = {'phone': phone, 'projectNo': projectNo, 'authtenderAmount': authtenderAmount, 'recharge_id': recharge_id}
        if red_pocket_id:
            query_top = db.session.query(Member_red_pocket_type, Member_red_pocket)
            query_res = query_top.filter(and_(Member_red_pocket.sort_id == Member_red_pocket_type.id, \
                                              Member_red_pocket.id == red_pocket_id)).all()
            rpt = query_res[0][0]
            if rpt.type == '99':
                rate_security = float(query_res[0][0].rate)
                product_info = Product_info.query.filter_by(id=projectNo).first()
                red_pocket_val = round(float(authtenderAmount)*rate_security*float(product_info.time_limit)/360.0, 2)
                if amount >= red_pocket_val:
                    reqData['amount'] = round(amount - float(red_pocket_val), 2)
            redata['red_pocket_id'] = red_pocket_id

        reqData['authtradeType'] = 'TENDER'
        reqData['authtenderAmount'] = authtenderAmount
        reqData['projectNo'] = projectNo
        reqData['redirectUrl'] = callback + '/invest?data=%s' % redata
    else:
        reqData['redirectUrl'] = callback + '?order_id=%s' % recharge_id

    try:
        ml = Member_login.query.filter_by(member_id=member.id).order_by(Member_login.last_time.desc()).first()
        equipment = ml.equipment_name
        if not equipment:
            equipment = 'app'
    except Exception, e:
        equipment = 'app'

    mr = Member_recharge_info(
        member_id=str(member.id).replace('-', ''), member_name=member.name,
        recharge_id=recharge_id, time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        is_effect=0, money=amount, type=5, bangka=member_pay_info.pay_bankcard,
        code="", equipment=equipment, bluuid=member.bluuid)
    db.session.add(mr)
    db.session.commit()
    request_data = base_params(serviceName, reqData)
    request_data['xw_url'] = XW_URI_HTML
    return toolkit.response(request_data, 200, None, True)


# 快速充值回调
@app.route('/xinwang/callback/html/recharge/invest', methods=["GET", "POST"])
def recharge_callback_html():
    from apps.product.xinv import xinwang_order
    data = request.args.get("data")
    redata = eval(data)
    phone = redata['phone']
    projectNo = redata['projectNo']
    amount = redata['authtenderAmount']
    recharge_id = redata['recharge_id']
    if redata.has_key('red_pocket_id'):
        red_pocket_id = redata['red_pocket_id']
    else:
        red_pocket_id = None
    order_id = gen_request_no()
    xinwang_order(phone, order_id, projectNo, amount, red_pocket_id)
    order_data = user_auto_pre_transaction(order_id, recharge_id)
    return redirect(config.BOLUO_URL +
                    '/static/h5/xinwang/user_pre_transaction/user_pre_transaction.html?order_id=%s' % order_data['order_id'])


# 充值回调
def recharge_callback():
    response_data = parse_callback(request)
    respData = response_data["respData"]
    requestNo = respData["requestNo"]  # 请求流水号
    code = respData["code"]  # 调用状态(0 为调用成功、1 为失败，返回 1 时请看【调用失败错误码】及错误码 描述)
    status = respData[
        "status"]  # 业务处理状态(处理失败 INIT;处理成功 SUCCESS)，平台可根据非 SUCCESS 状态做相应处理，处理失败时可参考错误码及描述
    errorCode = respData.get("errorCode", "")  # 错误码
    errorMessage = respData.get("errorMessage", "")  # 错误码描述
    rechargeStatus = respData["rechargeStatus"]  # 充值状态;SUCCESS 支付成功、FAIL 支付失败、PENDDING 支付中
    platformUserNo = respData["platformUserNo"]  # 平台用户编号
    amount = respData["amount"]  # 充值金额
    commission = respData["commission"]  # 平台佣金
    payCompany = respData["payCompany"]  # 见【支付公司】
    rechargeWay = respData["rechargeWay"]  # 见【支付方式】
    bankcode = respData.get("bankcode")  # 见【银行编码】(只有快捷会返回)
    payMobile = respData.get("payMobile")  # 本次充值手机号，网银为空
    transactionTime = respData.get("transactionTime")  # 交易完成时间
    channelErrorCode = respData.get(
        "channelErrorCode", "")  # 见【支付通道错误码】(若快捷充值回调方式传入 DIRECT_CALLBACK，则返回 此参数)技术支持单独提供
    channelErrorMessa = respData.get(
        "channelErrorMessa", "")  # 见【支付通道返回错误消息】(若快捷充值回调方式传入 DIRECT_CALLBACK， ge 则返回此参数)技术支持单独提供

    handled = is_handled(requestNo)
    if handled:
        return handled

    callback = CallbackInformation(
        phone=payMobile,
        requestNo=requestNo,
        code=code,
        type=CALLBACK_TYPE[response_data["serviceName"]],
        status=rechargeStatus,
        errorCode=errorCode,
        errorMessage=errorMessage
    )
    mri = Member_recharge_info.query.filter(Member_recharge_info.recharge_id == requestNo).first()
    if mri:
        print '~~~~~~~~~~'
        print rechargeStatus, mri.is_effect
        print '~~~~~~~~~~'
        if rechargeStatus == "SUCCESS" and mri.is_effect == 0:
            mri.is_effect = 1
            # Member asset 表中增加余额
            ma = Member_asset_info.query.filter(
                Member_asset_info.member_id == platformUserNo).first()
            if ma:
                ma.rechargeamount += float(amount) - float(commission)
                db.session.merge(ma)
            db.session.merge(mri)
            balance = ma.rechargeamount + ma.remainamount + mri.money
            info_order = u"充值%s元, 手机号%s" % (mri.money, payMobile)
            ins = Member_income_statement(member_id=mri.member_id, type=u"充值", money=mri.money, \
                                      balance=balance, time=transactionTime, info=info_order,
                                      order_id=requestNo, phone=payMobile)
            from apps.asset.views import give_hongbao
            give_hongbao(mri.member_id)
            db.session.merge(ins)
    db.session.add(callback)
    db.session.commit()

    return toolkit.response(response_data, 200, None, True)


# -----------------------------------------------提现-----------------------------------------------
# -----------------------------------------------提现-----------------------------------------------
# -----------------------------------------------提现-----------------------------------------------

# 提现
@app.route('/v1/xinwang/withdraw', methods=["GET", "POST"])
@xinwang_register_required
def withdraw():
    callback = get_callback_url(request)
    serviceName = "WITHDRAW"

    phone = request.args.get("phone")  # 绑卡注册的用户ID
    amount = request.args.get("amount", 100)

    member = Member.query.filter(Member.phone == phone).first()
    fee = request.args.get("fee", None)           # 手续费
    mai = Member_asset_info.query.filter(Member_asset_info.member_id == member.id).first()

    requestNo = gen_request_no()
    reqData = {
        "platformUserNo": str(member.id).replace('-', ''),  # 用户ID
        "requestNo": requestNo,  # 请求流水号
        "expired": (datetime.datetime.now() + datetime.timedelta(seconds=300)).strftime("%Y%m%d%H%M%S"),  # 超过此时间即页面过期,
        "redirectUrl": callback + '?order_id=%s' % requestNo,  # 回调地址
        "withdrawType": 'NORMAL',
        "withdrawForm": "CONFIRMED",
        # "commission":  fee,  # 平台佣金
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }

    try:
        if float(fee) > 0:
            fee = "%.2f" % float(fee)
            reqData['commission'] = fee
    except:
        fee = 0

    if mai.remainamount + mai.rechargeamount > float(amount) + float(fee):
        reqData['amount'] = float(amount) + float(fee)
    else:
        reqData['amount'] = float(amount)

    print reqData

    response_data = {}
    if member.isblack == 'True':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您已经被拉入黑名单"
        return toolkit.response(response_data, 200, None, True)

    if member.is_pay_bind == 0:
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"未绑定银行卡"
        return toolkit.response(response_data, 200, None, True)

    request_data = base_params(serviceName, reqData)
    request_data['xw_url'] = XW_URI_HTML
    return toolkit.response(request_data, 200, None, True)


# 提现回调
def withdraw_callback():
    response_data = parse_callback(request)
    respData = response_data["respData"]
    code = respData["code"]  # 调用状态(0 为调用成功、1 为失败，返回 1 时请看【调用失败错误码】及错误码 描述)
    status = respData[
        "status"]  # 业务处理状态(处理失败 INIT;处理成功 SUCCESS)，平台可根据非 SUCCESS 状态做相应处理，处理失败时可参考错误码及描述
    errorCode = respData.get("errorCode", "")  # 错误码
    errorMessage = respData.get("errorMessage", "")  # 错误码描述
    withdrawStatus = respData["withdrawStatus"]  # 提现交易状态, WITHDRAW_STATUS
    requestNo = respData["requestNo"]  # 请求流水号
    platformUserNo = respData["platformUserNo"]  # 平台用户编号
    commission = respData.get("commission", 0)  # 平台佣金
    amount = respData["amount"]  # 提现金额，提现类型为“待确认提现”时为冻结金额
    withdrawWay = respData["withdrawWay"]  # 提现方式, WITHDRAW_TYPE
    withdrawForm = respData["withdrawForm"]  # 提现类型
    bankcardNo = respData["bankcardNo"]  # 提现银行卡号
    bankcode = respData["bankcode"]  # 见【银行编码】(只有快捷会返回)
    createTime = respData["createTime"]  # 交易发起时间
    createTime = datetime.datetime.strptime(createTime, "%Y%m%d%H%M%S")
    transactionTime = respData.get("transactionTime", None)  # 交易完成时间
    if transactionTime:
        transactionTime = datetime.datetime.strptime(transactionTime, "%Y%m%d%H%M%S")

    handled = is_handled(requestNo)
    if handled:
        return handled

    callback = CallbackInformation(
        requestNo=requestNo,
        code=code,
        type=CALLBACK_TYPE[response_data["serviceName"]],
        status=withdrawStatus,
        errorCode=errorCode,
        errorMessage=errorMessage,
    )
    db.session.add(callback)

    now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    reflect_money = float(amount)
    fee = float(commission)

    member = Member.query.filter(Member.id == platformUserNo).first()
    ma = Member_asset_info.query.filter(Member_asset_info.member_id == platformUserNo).first()
    total_amount = reflect_money# 要扣除的钱
    if withdrawStatus == 'CONFIRMING':
        if total_amount > ma.remainamount + ma.rechargeamount:
            response_data = {"code": u"10012", "desc": u"提现金额大于可用余额", "content": {}}
            return toolkit.response(response_data, 200, None, True)
        else:
            ma.freezeamount += total_amount - fee
            if ma.remainamount >= total_amount:
                ma.remainamount -= total_amount
            else:
                # 先从 remainamount 扣钱
                total_amount -= ma.remainamount
                ma.remainamount = 0

                # 再从 rechargeamount 扣钱
                ma.rechargeamount -= total_amount
            db.session.merge(ma)

        balance = ma.remainamount + ma.rechargeamount
        type = u"提现"
        info = u"申请提现%s" % reflect_money
        ins = Member_income_statement(
            member_id=platformUserNo, type=type, money=reflect_money-fee, balance=balance, time=now_time,
            info=info, order_id=requestNo, phone=member.phone)
        db.session.add(ins)

        mr = Member_reflect_info(
            member_id=platformUserNo, member_name=member.name, reflect_id=requestNo, money=reflect_money-fee,
            time=now_time, fee=fee, type=1, bluuid=member.bluuid, device_info=member.device_info,
            channel_id=member.channel_id)

        db.session.add(mr)
    db.session.commit()

    return toolkit.response(response_data, 200, None, True)


# ------------------------------------提现结果通知-------------------------------------------------
# ------------------------------------提现结果通知-------------------------------------------------
# ------------------------------------提现结果通知-------------------------------------------------


def withdraw_notify(respData):
    """
    提现结果通知

    :return:
    """
    code = respData["code"]  # 调用状态(0 为调用成功、1 为失败，返回 1 时请看【调用失败错误码】及错误码 描述)
    status = respData[
        "status"]  # 业务处理状态(处理失败 INIT;处理成功 SUCCESS)，平台可根据非 SUCCESS 状态做相应处理，处理失败时可参考错误码及描述
    errorCode = respData.get("errorCode", "")  # 错误码
    errorMessage = respData.get("errorMessage", "")  # 错误码描述
    withdrawStatus = respData["withdrawStatus"]  # 提现交易状态, WITHDRAW_STATUS
    requestNo = respData["requestNo"]  # 请求流水号
    amount = respData["amount"]  # 提现金额，提现类型为“待确认提现”时为冻结金额
    commission = respData["commission"]  # 平台佣金
    platformUserNo = respData["platformUserNo"]  # 平台用户编号
    createTime = respData["createTime"]  # 交易发起时间
    transactionTime = respData.get("transactionTime", None)  # 交易完成时间
    remitTime = respData.get("remitTime", None)  # 出款时间
    completedTime = respData.get("completedTime", None)  # 到账时间
    bankcardNo = respData["bankcardNo"]  # 提现银行卡号

    if transactionTime:
        transactionTime = datetime.datetime.strptime(transactionTime, "%Y%m%d%H%M%S")
    if remitTime:
        remitTime = datetime.datetime.strptime(remitTime, "%Y%m%d%H%M%S")
    if completedTime:
        completedTime = datetime.datetime.strptime(completedTime, "%Y%m%d%H%M%S")

    mri = Member_reflect_info.query.filter(Member_reflect_info.reflect_id == requestNo).first()
    ma = Member_asset_info.query.filter(Member_asset_info.member_id == platformUserNo).first()

    if mri and mri.type == 2 and ma:
        # 提现成功
        if withdrawStatus in ("SUCCESS", "REMITING"):
            mri.type = 3
            ma.freezeamount -= mri.amount
            db.session.merge(ma)
        else:
            mri.type = 5

        db.session.merge(mri)

    db.session.commit()


# -----------------------------------------------用户预处理(下订单)-----------------------------------------------
# -----------------------------------------------用户预处理(下订单)-----------------------------------------------
# -----------------------------------------------用户预处理(下订单)-----------------------------------------------

# 创建标的
@app.route('/v1/xinwang/establish_project')
@xinwang_register_required
def establish_project():
    serviceName = "ESTABLISH_PROJECT"
    reqData = {
        "platformUserNo": "2de714a1a6c5421e8f15de8c7ff5fcd7",  # 用户ID
        "requestNo": gen_request_no(),  # 请求流水号
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),

        "projectNo": gen_request_no(),
        "projectAmount": 100000,
        "projectName": "标的名称",
        "projectDescription": "标的描述",
        "projectType": "STANDARDPOWDER",
        "projectPeriod": "100",
        "annnualInterestRate": "0.15",
        "repaymentWay": "FIRSEINTREST_LASTPRICIPAL",
    }

    params = base_params(serviceName, reqData)
    resp = requests.post(XW_API_URI, params)
    return resp.text + reqData["projectNo"]


# 用户预处理
@app.route('/v1/xinwang/user_pre_transaction', methods=["GET", "POST"])
@xinwang_register_required
def user_pre_transaction():
    callback = get_callback_url(request)
    serviceName = "USER_PRE_TRANSACTION"

    phone = request.args.get("phone", "")  # 绑卡注册的用户ID
    order_id = request.args.get("order_id", "")  # 订单号
    member = Member.query.filter(Member.phone == phone).first()
    invest_info = Invest_info.query.filter_by(order_id=order_id, member_id=str(member.id).replace('-', '')).first()
    if not invest_info:
        response_data = {}
        response_data["code"] = u"10005"
        response_data["desc"] = u"订单号失效"
        return toolkit.response(response_data, 200, None, True)

    amount = invest_info.money  # 冻结金额

    now = datetime.datetime.now()
    expired = now + datetime.timedelta(hours=1)  # 超过此时间即页面过期
    share = request.args.get("share", None)  # 购买债转份额，业务类型为债权认购时，需要传此参数
    creditsaleRequestNo = request.args.get("creditsaleRequestNo", None)  # 债权出让请求流水号，只有债权认购业务需填此参数

    reqData = {
        "platformUserNo": str(member.id).replace('-', ''),  # 用户ID
        # "requestNo": gen_request_no(),  # 请求流水号
        "requestNo": order_id,  # 请求流水号
        "redirectUrl": callback + '?order_id=%s' % order_id,  # 回调地址
        "timestamp": now.strftime("%Y%m%d%H%M%S"),
        "userRole": "INVESTOR",
        "bizType": 'TENDER',  # 预处理业务类型
        "amount": amount,
        "expired": expired.strftime("%Y%m%d%H%M%S"),
        "remark": "备注内容",
        "projectNo": invest_info.product_id,  # 标的号
    }
    if share:
        reqData["share"] = share
    if creditsaleRequestNo:
        reqData["creditsaleRequestNo"] = creditsaleRequestNo

    pro = Product_info.query.filter_by(id=invest_info.product_id).first()

    if float(invest_info.hongbao) > 0 and pro.product_status == '2':
        reqData["preMarketingAmount"] = float(invest_info.hongbao)  # float(invest_info.yaoqing_money)

    request_data = base_params(serviceName, reqData)
    request_data['xw_url'] = XW_URI_HTML

    return toolkit.response(request_data, 200, None, True)


# 用户预处理回调
def user_pre_transaction_callback():
    response_data = parse_callback(request)
    respData = response_data["respData"]

    requestNo = respData["requestNo"]  # 请求流水号
    code = respData["code"]  # 调用状态(0 为调用成功、1 为失败，返回 1 时请看【调用失败错误码】及错误码 描述)
    status = respData[
        "status"]  # 业务处理状态(处理失败 INIT;处理成功 SUCCESS)，平台可根据非 SUCCESS 状态做相应处理，处理失败时可参考错误码及描述
    errorCode = respData.get("errorCode", "")  # 错误码
    errorMessage = respData.get("errorMessage", "")  # 错误码描述
    bizType = respData["bizType"]  # 预处理业务类型

    invest_info = Invest_info.query.filter_by(order_id=requestNo).first()
    rp = Member_red_pocket.query.filter_by(id=invest_info.hongbao_info_id).first()
    m = Member.query.filter_by(id=invest_info.member_id).first()
    if status == 'SUCCESS':
        if invest_info:  # 成功下订单,并冻结资金
            invest_info.is_effect = 1
            db.session.add(invest_info)
            db.session.commit()
        xw_activity_order(m.phone, requestNo)
        if rp:  # 使用红包
            rp.is_freeze = True
            rp.product_id = invest_info.product_id
            db.session.merge(rp)
            db.session.commit()

    handled = is_handled(requestNo)
    if handled:
        return handled

    callback = CallbackInformation(
        requestNo=requestNo,
        code=code,
        type=CALLBACK_TYPE[response_data["serviceName"]],
        status=status,
        errorCode=errorCode,
        errorMessage=errorMessage,
        phone=m.phone,
    )
    db.session.add(callback)
    db.session.commit()

    return toolkit.response(response_data, 200, None, True)


# -----------------------------------------------授权预处理(充值下订单)-----------------------------------------------
# -----------------------------------------------授权预处理(充值下订单)-----------------------------------------------
# -----------------------------------------------授权预处理(充值下订单)-----------------------------------------------


def user_auto_pre_transaction(order_id, recharge_id):
    serviceName = "USER_AUTO_PRE_TRANSACTION"
    invest_info = Invest_info.query.filter_by(order_id=order_id).first()
    member = Member.query.filter_by(id=invest_info.member_id).first()
    product_id = invest_info.product_id
    red_pocket_val = invest_info.hongbao
    total_fee = invest_info.money
    reqData = {
        "platformUserNo": str(member.id).replace('-', ''),  # 用户ID
        "requestNo": order_id,  # 请求流水号
        "originalRechargeNo": recharge_id,  # 关联充值请求流水号(原充值成功请求流水号)
        "bizType": "TENDER",  # 若传入关联请求流水号,则固定为 TENDER
        "amount": total_fee,  # 冻结金额
        "projectNo": product_id,  # 见【用户授权列表】此处可传一个或多个值，传多个值用“,”英文半角逗号分隔
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }

    if red_pocket_val > 0:
        reqData["preMarketingAmount"] = red_pocket_val  # float(invest_info.yaoqing_money)

    request_data = base_params(serviceName, reqData)
    response_data = eval(http_post(XW_API_URI, request_data))
    print '--------==========快速充值下订单========---------'
    print response_data
    print '--------==========快速充值下订单========---------'

    requestNo = response_data["requestNo"]  # 请求流水号
    code = response_data["code"]  # 调用状态(0 为调用成功、1 为失败，返回 1 时请看【调用失败错误码】及错误码 描述)
    status = response_data[
        "status"]  # 业务处理状态(处理失败 INIT;处理成功 SUCCESS)，平台可根据非 SUCCESS 状态做相应处理，处理失败时可参考错误码及描述
    # errorCode = respData.get("errorCode", "")  # 错误码
    # errorMessage = respData.get("errorMessage", "")  # 错误码描述
    if status == 'SUCCESS':
        # 成功下订单,并冻结资金
        if invest_info:
            invest_info.is_effect = 1
            db.session.merge(invest_info)
            db.session.commit()

        # 活动积分
        xw_activity_order(member.phone, requestNo)

        # 使用红包
        rp = Member_red_pocket.query.filter_by(id=invest_info.hongbao_info_id).first()
        if rp:
            rp.is_freeze = True
            rp.product_id = invest_info.product_id
            db.session.merge(rp)
            db.session.commit()

        handled = is_handled(requestNo)
        if handled:
            return handled

        callback = CallbackInformation(
            requestNo=requestNo,
            code=code,
            type=CALLBACK_TYPE['USER_AUTO_PRE_TRANSACTION'],
            status=status,
            errorCode='',
            errorMessage='',
            phone=member.phone,
        )
        db.session.add(callback)
        db.session.commit()
        order_data = {'order_id': requestNo}
    else:
        order_data = {'order_id': ''}
    return order_data


# -----------------------------------------------用户个人绑卡-----------------------------------------------
# -----------------------------------------------用户个人绑卡-----------------------------------------------
# -----------------------------------------------用户个人绑卡-----------------------------------------------


# 个人绑卡
@app.route('/v1/xinwang/bind_bankcard', methods=["GET", "POST"])
@xinwang_register_required
def xw_bind_bankcard():
    callback = get_callback_url(request)
    serviceName = "PERSONAL_BIND_BANKCARD_EXPAND"
    phone = request.args.get("phone")  # 绑卡注册的用户ID
    member = Member.query.filter(Member.phone == phone).first()
    response_data = {}
    if member.is_pay_bind == 1:
        response_data["code"] = u"10005"
        response_data["desc"] = u"已经绑定银行卡，如果要绑定其他银行卡，请先解绑"
        return toolkit.response(response_data, 200, None, True)
    reqData = {
        "platformUserNo": str(member.id).replace('-', ''),     # 用户ID
        "requestNo": gen_request_no(),          # 请求流水号
        "checkType": "LIMIT",
        "redirectUrl": callback,        # 回调地址
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }
    request_data = base_params(serviceName, reqData)
    request_data['xw_url'] = XW_URI_HTML
    return toolkit.response(request_data, 200, None, True)


# 个人绑卡回调
def xw_bind_bankcard_callback():
    response_data = parse_callback(request)
    respData = response_data["respData"]

    # 根据请求流水号判断是哪次请求
    requestNo = respData["requestNo"]  # 请求流水号
    code = respData["code"]  # 调用状态(0 为调用成功、1 为失败，返回 1 时请看【调用失败错误码】及错误码 描述)
    status = respData[
        "status"]  # 业务处理状态(处理失败 INIT;处理成功 SUCCESS)，平台可根据非 SUCCESS 状态做相应处理，处理失败时可参考错误码及描述
    errorCode = respData.get("errorCode", "")  # 错误码
    errorMessage = respData.get("errorMessage", "")  # 错误码描述
    platformUserNo = respData["platformUserNo"]  # 平台用户编号
    bankcardNo = respData["bankcardNo"]  # 银行卡号
    bank_code = respData["bankcode"]  # 银行编码, BANK_CODE
    mobile = respData["mobile"]  # 银行预留手机号
    accessType = respData["accessType"]  # 见【鉴权通过类型】, ACCESS_TYPE

    handled = is_handled(requestNo)
    if handled:
        return handled

    callback = CallbackInformation(
        requestNo=requestNo,
        code=code,
        type=CALLBACK_TYPE[response_data["serviceName"]],
        status=status,
        phone=mobile,
        errorCode=errorCode,
        errorMessage=errorMessage,
        accessType=accessType
    )
    db.session.add(callback)

    user = Member.query.filter(Member.id == platformUserNo).first()
    if user and status == 'SUCCESS':
        user.is_pay_bind = 1
        db.session.merge(user)
        # 更新用户绑卡信息表
        member_pay_info = Member_pay_info.query.filter(Member_pay_info.member_id==platformUserNo).first()
        bank_logo = Member_bank_logo.query.filter_by(bank_code2=bank_code).first()
        if member_pay_info:
            member_pay_info.pay_bankcard = bankcardNo
            member_pay_info.bank_name = bank_logo.bank
            member_pay_info.bank_code = bank_code
            member_pay_info.phone = mobile
            db.session.merge(member_pay_info)
    db.session.commit()

    return toolkit.response(response_data, 200, None, True)


# -----------------------------------------------银行卡解绑-----------------------------------------------
# -----------------------------------------------银行卡解绑-----------------------------------------------
# -----------------------------------------------银行卡解绑-----------------------------------------------


# 银行卡解绑
@app.route('/v1/xinwang/unbind_bankcard')
@xinwang_register_required
def unbind_bankcard():
    response_data = {}
    # 已经解绑过银行卡
    if request.xinwang_user.is_pay_bind == 0:
        response_data["code"] = u"10004"
        response_data["desc"] = u"未绑定银行卡"
        return toolkit.response(response_data, 200, None, True)

    callback = get_callback_url(request)
    serviceName = "UNBIND_BANKCARD"

    user_id = request.args.get("user_id", "100006")  # 绑卡注册的用户ID

    reqData = {
        "platformUserNo": user_id,  # 用户ID
        "requestNo": gen_request_no(),  # 请求流水号
        "redirectUrl": callback,  # 回调地址
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }
    request_data = base_params(serviceName, reqData)
    return toolkit.response(request_data, 200, None, True)


# 银行卡解绑回调
def unbind_bankcard_callback():
    response_data = parse_callback(request)
    respData = response_data["respData"]

    requestNo = respData["requestNo"]  # 请求流水号
    platformUserNo = respData["platformUserNo"]  # 平台用户编号
    code = respData["code"]  # 见【返回码】
    # 业务处理状态(处理失败 INIT;处理成功 SUCCESS)，平台可根据非 SUCCESS 状态做相应处理，处理失败时可参考错误码及描述
    status = respData["status"]
    errorCode = respData.get("errorCode", "")  # 错误码
    errorMessage = respData.get("errorMessage", "")  # 错误码描述

    handled = is_handled(requestNo)
    if handled:
        return handled

    callback = CallbackInformation(
        requestNo=requestNo,
        code=code,
        type=CALLBACK_TYPE[response_data["serviceName"]],
        status=status,
        errorCode=errorCode,
        errorMessage=errorMessage,
    )
    db.session.add(callback)

    # 银行卡绑定信息标记为未绑定，不需要清除银行卡信息，再次绑定时直接覆盖
    user = Member.query.filter(Member.id == platformUserNo).first()
    if user and user.is_register_xinwang == 1:
        user.is_pay_bind = 0
        db.session.merge(user)

    db.session.commit()

    return toolkit.response(response_data, 200, None, True)


# -----------------------------------------------修改密码-----------------------------------------------
# -----------------------------------------------修改密码-----------------------------------------------
# -----------------------------------------------修改密码-----------------------------------------------


# 修改密码
@app.route('/v1/xinwang/reset_password', methods=["GET", "POST"])
@xinwang_register_required
def reset_password():
    callback = get_callback_url(request)
    serviceName = "RESET_PASSWORD"

    phone = request.args.get("phone", "")  # 绑卡注册的用户ID
    member = Member.query.filter(Member.phone == phone).first()

    reqData = {
        "platformUserNo": str(member.id).replace('-', ''),  # 用户ID
        "requestNo": gen_request_no(),  # 请求流水号
        "redirectUrl": callback,  # 回调地址
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }
    request_data = base_params(serviceName, reqData)
    request_data['xw_url'] = XW_URI_HTML
    return toolkit.response(request_data, 200, None, True)


# 修改密码回调
def reset_password_callback():
    response_data = parse_callback(request)
    respData = response_data["respData"]
    code = respData["code"]  # 调用状态(0 为调用成功、1 为失败，返回 1 时请看【调用失败错误码】及错误码 描述)
    status = respData[
        "status"]  # 业务处理状态(处理失败 INIT;处理成功 SUCCESS)，平台可根据非 SUCCESS 状态做相应处理，处理失败时可参考错误码及描述
    errorCode = respData.get("errorCode", "")  # 错误码
    errorMessage = respData.get("errorMessage", "")  # 错误码描述
    requestNo = respData["requestNo"]  # 请求流水号

    handled = is_handled(requestNo)
    if handled:
        return handled

    callback = CallbackInformation(
        requestNo=requestNo,
        code=code,
        type=CALLBACK_TYPE[response_data["serviceName"]],
        status=status,
        errorCode=errorCode,
        errorMessage=errorMessage,
    )
    db.session.add(callback)
    db.session.commit()

    return toolkitxxx.response(response_data, 200, None, True)


# -----------------------------------------------预留手机号更新-----------------------------------------------
# -----------------------------------------------预留手机号更新-----------------------------------------------
# -----------------------------------------------预留手机号更新-----------------------------------------------


# 预留手机号更新
@app.route('/v1/xinwang/modify_mobile_expand')
@xinwang_register_required
def modify_mobile_expand():
    callback = get_callback_url(request)
    serviceName = "MODIFY_MOBILE_EXPAND"

    user_id = request.args.get("user_id", "100006")  # 绑卡注册的用户ID

    reqData = {
        "platformUserNo": user_id,  # 用户ID
        "requestNo": gen_request_no(),  # 请求流水号
        "redirectUrl": callback,  # 回调地址
        "checkType": "LIMIT",  # 鉴权验证类型，默认填 LIMIT(强制四要素)，即四要素完全通过(姓名、身份证 号、银行卡号，银行预留手机号) 方可更新手机号成功
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }
    request_data = base_params(serviceName, reqData)
    return toolkit.response(request_data, 200, None, True)


# 预留手机号更新回调
def modify_mobile_expand_callback():
    response_data = parse_callback(request)
    respData = response_data["respData"]

    requestNo = respData["requestNo"]  # 请求流水号
    code = respData["code"]  # 调用状态(0 为调用成功、1 为失败，返回 1 时请看【调用失败错误码】及错误码 描述)
    status = respData[
        "status"]  # 业务处理状态(处理失败 INIT;处理成功 SUCCESS)，平台可根据非 SUCCESS 状态做相应处理，处理失败时可参考错误码及描述
    errorCode = respData.get("errorCode", "")  # 错误码
    errorMessage = respData.get("errorMessage", "")  # 错误码描述
    platformUserNo = respData["platformUserNo"]  # 平台用户编号
    bankcardNo = respData["bankcardNo"]  # 银行卡号
    bankcode = respData["bankcode"]  # 银行编码, BANK_CODE
    mobile = respData["mobile"]  # 更新后银行预留手机号

    handled = is_handled(requestNo)
    if handled:
        return handled

    callback = CallbackInformation(
        requestNo=requestNo,
        code=code,
        type=CALLBACK_TYPE[response_data["serviceName"]],
        status=status,
        phone=mobile,
        errorCode=errorCode,
        errorMessage=errorMessage
    )
    db.session.add(callback)
    db.session.commit()

    return toolkit.response(response_data, 200, None, True)


# -----------------------------------------------验证密码-----------------------------------------------
# -----------------------------------------------验证密码-----------------------------------------------
# -----------------------------------------------验证密码-----------------------------------------------


# 验证密码
@app.route('/v1/xinwang/check_password')
@xinwang_register_required
def check_password():
    callback = get_callback_url(request)
    user_id = request.args.get("user_id", "100006")  # 绑卡注册的用户ID
    serviceName = "CHECK_PASSWORD"
    reqData = {
        "platformUserNo": user_id,  # 用户ID
        "requestNo": gen_request_no(),  # 请求流水号
        "redirectUrl": callback,  # 回调地址
        "bizTypeDescription": "验证密码",  # 平台根据自定的业务描述，最多25个字符
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }
    request_data = base_params(serviceName, reqData)
    return toolkit.response(request_data, 200, None, True)


# 验证密码回调
def check_password_callback():
    response_data = parse_callback(request)
    respData = response_data["respData"]

    requestNo = respData["requestNo"]  # 请求流水号
    code = respData["code"]  # 调用状态(0 为调用成功、1 为失败，返回 1 时请看【调用失败错误码】及错误码 描述)
    status = respData[
        "status"]  # 业务处理状态(处理失败 INIT;处理成功 SUCCESS)，平台可根据非 SUCCESS 状态做相应处理，处理失败时可参考错误码及描述
    errorCode = respData.get("errorCode", "")  # 错误码
    errorMessage = respData.get("errorMessage", "")  # 错误码描述
    platformUserNo = respData["platformUserNo"]  # 平台用户编号
    bizTypeDescription = respData["bizTypeDescription"]  # 平台自定义的业务描述

    handled = is_handled(requestNo)
    if handled:
        return handled

    callback = CallbackInformation(
        requestNo=requestNo,
        code=code,
        type=CALLBACK_TYPE[response_data["serviceName"]],
        status=status,
        errorCode=errorCode,
        errorMessage=errorMessage
    )
    db.session.add(callback)
    db.session.commit()

    return toolkit.response(response_data, 200, None, True)


# -----------------------------------------------用户激活-----------------------------------------------
# -----------------------------------------------用户激活-----------------------------------------------
# -----------------------------------------------用户激活-----------------------------------------------


# 用户激活
@app.route('/v1/xinwang/activate_stocked_user', methods=["GET", "POST"])
def activate_stocked_user():
    callback = get_callback_url(request)
    phone = request.args.get("phone", "")
    request_data = {}
    member = Member.query.filter(Member.phone == phone).first()
    if member:
        if member.is_register_xinwang == 2:
            pass
        elif member.is_register_xinwang == 0:
            request_data["code"] = u"10002"
            request_data["desc"] = u"用户未注册"
            return toolkit.response(request_data, 200, None, True)
        elif member.is_register_xinwang == 1:
            request_data["code"] = u"10003"
            request_data["desc"] = u"用户已注册"
            return toolkit.response(request_data, 200, None, True)
        else:
            request_data["code"] = u"10004"
            request_data["desc"] = u"激活异常,请与客服联系"
            return toolkit.response(request_data, 200, None, True)
    else:
        request_data["code"] = u"10001"
        request_data["desc"] = u"用户不存在"
        return toolkit.response(request_data, 200, None, True)

    serviceName = "ACTIVATE_STOCKED_USER"
    reqData = {
        "platformUserNo": str(member.id).replace('-', ''),  # 平台用户编号
        "requestNo": gen_request_no(),  # 请求流水号
        "redirectUrl": callback,  # 页面回跳 URL
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        "authList": "CREDIT_ASSIGNMENT,TENDER",  # 见【用户授权列表】此处可传一个或多个值，传多个值用“,”英文半角逗号分隔
        "checkType": "LIMIT",           # 鉴权验证类型，默认填 LIMIT(强制四要素)，即四要素完全通过(姓名、身份证 号、银行卡号，银行预留手机号) 方可更新手机号成功
    }
    request_data = base_params(serviceName, reqData)
    request_data['xw_url'] = XW_URI_HTML
    request_data["code"] = u'10000'
    return toolkit.response(request_data, 200, None, True)


# 用户激活回调
def activate_stocked_user_callback():
    response_data = parse_callback(request)
    respData = response_data["respData"]

    requestNo = respData["requestNo"]  # 请求流水号
    code = respData["code"]  # 调用状态(0 为调用成功、1 为失败，返回 1 时请看【调用失败错误码】及错误码 描述)
    status = respData[
        "status"]  # 业务处理状态(处理失败 INIT;处理成功 SUCCESS)，平台可根据非 SUCCESS 状态做相应处理，处理失败时可参考错误码及描述
    errorCode = respData.get("errorCode", "")  # 错误码
    errorMessage = respData.get("errorMessage", "")  # 错误码描述
    platformUserNo = respData["platformUserNo"]  # 平台用户编号
    bankcardNo = respData["bankcardNo"]  # 银行卡号或企业对公账户
    bankcode = respData["bankcode"]  # 见【银行编码】
    mobile = respData["mobile"]  # 手机号
    accessType = respData["accessType"]  # 见【鉴权通过类型】
    userRole = respData["userRole"]  # 见【用户角色】
    auditStatus = respData["auditStatus"]  # 见【审核状态】,该接口会发送多次不同审核状态的回调
    # cardNolsChange = respData["cardNolsChange"]  # 主动换卡标识;TRUE 表示用户在页面上修改过已经导入的卡号;FALSE 表示用户 是主动填写或没有在页面上修改过卡号;

    if status == 'SUCCESS':
        member = Member.query.filter(Member.id==platformUserNo).first()
        member.is_register_xinwang = 1
        db.session.merge(member)

    handled = is_handled(requestNo)
    if handled:
        return handled

    callback = CallbackInformation(
        requestNo=requestNo,
        code=code,
        type=CALLBACK_TYPE[response_data["serviceName"]],
        status=status,
        errorCode=errorCode,
        errorMessage=errorMessage
    )
    db.session.add(callback)
    db.session.commit()
    return toolkit.response(response_data, 200, None, True)


# -----------------------------------------------用户授权-----------------------------------------------
# -----------------------------------------------用户授权-----------------------------------------------
# -----------------------------------------------用户授权-----------------------------------------------


# 用户授权
@app.route('/v1/xinwang/user_authorization')
@xinwang_register_required
def user_authorization():
    callback = get_callback_url(request)
    serviceName = "USER_AUTHORIZATION"

    user_id = request.args.get("user_id", "100006")  # 绑卡注册的用户ID

    reqData = {
        "platformUserNo": user_id,  # 用户ID
        "requestNo": gen_request_no(),  # 请求流水号
        "redirectUrl": callback,  # 回调地址
        "authList": choice(AUTH_TYPE.keys()),  # 见【用户授权列表】此处可传一个或多个值，传多个值用“,”英文半角逗号分隔
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }
    request_data = base_params(serviceName, reqData)
    return toolkit.response(request_data, 200, None, True)


# 用户授权回调
@app.route('/v1/xinwang/user_authorization/callback', methods=["POST"])
def user_authorization_callback():
    response_data = parse_callback(request)
    respData = response_data["respData"]

    platformUserNo = respData["platformUserNo"]  # 平台用户编号
    requestNo = respData["requestNo"]  # 请求流水号
    code = respData["code"]  # 调用状态(0 为调用成功、1 为失败，返回 1 时请看【调用失败错误码】及错误码 描述)
    status = respData[
        "status"]  # 业务处理状态(处理失败 INIT;处理成功 SUCCESS)，平台可根据非 SUCCESS 状态做相应处理，处理失败时可参考错误码及描述
    errorCode = respData.get("errorCode", "")  # 错误码
    errorMessage = respData.get("errorMessage", "")  # 错误码描述
    authList = respData["authList"]  # 用户授权列表

    handled = is_handled(requestNo)
    if handled:
        return handled

    callback = CallbackInformation(
        requestNo=requestNo,
        code=code,
        type=CALLBACK_TYPE[response_data["serviceName"]],
        status=status,
        errorCode=errorCode,
        errorMessage=errorMessage
    )
    db.session.add(callback)
    db.session.commit()
    return toolkit.response(response_data, 200, None, True)



@app.route('/v1/xinwang/test_freeze')
def f123():
    result = freeze("100005", "1")
    return json.dumps(result)


# 资金冻结
def freeze(user_id, amount):
    """
    调用资金冻结接口

    :param user_id: 要冻结资金的用户ID
    :param amount: 资金金额，单位：元
    :return:
    """
    requestNo = gen_request_no()  # 请求流水号
    reqData = {
        "requestNo": requestNo,
        "platformUserNo": str(user_id),
        "amount": str(amount),
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }

    serviceName = "FREEZE"
    params = base_params(serviceName, reqData)
    resp = requests.post(XW_API_URI, params)
    if resp.ok:
        respData = resp.json()
        code = respData["code"]
        status = respData["status"]
        if int(code) != 0:
            errorCode = respData.get("errorCode", "")  # 错误码
            errorMessage = respData.get("errorMessage", "")  # 错误码描述

    return resp.json()


@app.route('/v1/xinwang/test_unfreeze')
def f2():
    no = request.args.get("no")
    return json.dumps(unfreeze(no, "1"))


def unfreeze(originalFreezeRequestNo, amount):
    """
    资金解冻

    :param originalFreezeRequestNo: 原冻结的请求流水号
    :param amount: 解冻金额
    :return:
    """
    requestNo = gen_request_no()  # 请求流水号
    reqData = {
        "requestNo": requestNo,
        "originalFreezeRequestNo": originalFreezeRequestNo,
        "amount": str(amount),
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }

    serviceName = "UNFREEZE"
    params = base_params(serviceName, reqData)
    resp = requests.post(XW_API_URI, params)
    if resp.ok:
        respData = resp.json()
        code = respData["code"]
        status = respData["status"]
        if int(code) != 0:
            errorCode = respData.get("errorCode", "")  # 错误码
            errorMessage = respData.get("errorMessage", "")  # 错误码描述

    return resp.json()


def http_post(url, data):
    req = urllib2.Request(url)
    data = urllib.urlencode(data)
    #enable cookie
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
    response = opener.open(req, data)
    return response.read()


def http_get(url, data):
    """
        返回2个参数182.92.237.84
    """
    vpath = urllib.urlencode(data)
    url = url + '&' + vpath
    response = urllib2.urlopen(url)
    return response.read()


@app.route('/v1/xinwang/notify', methods=["POST", 'GET'])
def notify():
    """
    新网异步通知

    :return:
    """
    response_data = parse_callback(request)

    # response_data = {'responseType': u'NOTIFY', 'keySerial': u'1', 'userDevice': None, 'platformNo': u'6000000579', 'sign': u'ROHHJTJge4tEspUFDUmC0AFAoM7ruP3SjqPUEp15WTtbIzEbDc6IhS2sbEyOgSf7jaO254rFd70TXSMHWD/h7N26DfdbKf7bWG4YlE/1/pS1zblRhliGKB2THyefvfahL3fsx9SZ9JeIIOSSOHXedPFl7bMTP7yA/8mjjMQVN9245drSwt9b17j7nI9/kYrYAkzJjkO24+i93StowZ7n6ERgnphIiq23V/qR/QIR6iRGi1mZ/u/tbHTbInCVZWtH/qpdu2bg9GCbes5jlvkpTuODwCQrIFPac81V4ue0liM8nNBWBo4uDB1CvN8h+1c0RoOsq/kuC61Ib4JKT8WsIA==', 'serviceName': u'ENTERPRISE_REGISTER', 'respData': {u'code': u'0', u'status': u'SUCCESS', u'platformUserNo': u'8a2db3e85c669826015c7c1470370065', u'auditStatus': u'AUDIT', u'requestNo': u'20170606142552', u'bankcardNo': u'6224001100001111', u'userRole': u'BORROWERS', u'bankcode': u'CMBC'}}
    serviceName = response_data["serviceName"]
    respData = response_data["respData"]

    if serviceName == "WITHDRAW" and respData['withdrawForm'] == 'CONFIRMED':
        withdrawStatus = respData["withdrawStatus"]
        if withdrawStatus == 'CONFIRMING':  # 已受理
            withdraw_callback()
        else:
            withdraw_notify(respData)
    elif serviceName == "PERSONAL_REGISTER_EXPAND":
        register_callback()
    elif serviceName == "PERSONAL_BIND_BANKCARD_EXPAND":
        xw_bind_bankcard_callback()
    elif serviceName == "UNBIND_BANKCARD":
        unbind_bankcard_callback()
    elif serviceName == "RECHARGE":
        recharge_callback()
    elif serviceName == "RESET_PASSWORD":
        reset_password_callback()
    elif serviceName == "MODIFY_MOBILE_EXPAND":
        modify_mobile_expand_callback()
    elif serviceName == "CHECK_PASSWORD":
        check_password_callback()
    elif serviceName == "USER_AUTHORIZATION":
        user_authorization_callback()
    elif serviceName == "USER_PRE_TRANSACTION":
        user_pre_transaction_callback()  # 用户下订单回调
    elif serviceName == "ACTIVATE_STOCKED_USER":
        activate_stocked_user_callback()  # 用户激活回调
    else:
        # java 那边
        requrl = XW_JAVA_URL + "?%s" % serviceName
        print requrl
        res = http_post(requrl, response_data)
        print '**********java*************'
        print res
        print '**********java*************'
        return res

    return "SUCCESS"
