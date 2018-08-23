#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Author: Tony NIU
#   niuwl586@gmail.com
import base64
import datetime
import json
from urllib import unquote

from M2Crypto.RSA import RSAError
from flask import Flask
from flask import render_template
from flask import request
import requests

from xwsdk.sign import sha1withRSA, check_sign

app = Flask(__name__)


PLATFORMNO = 6000000579

XW_API_URI = "http://124.250.37.124:8001/bha-neo-app/lanmaotech/service"


def get_callback_url(request):
    """
    获取回调地址，在当前请求地址后加上_callback

    :return: 回调地址
    :rtype: str
    """
    return request.scheme + "://" + request.host + request.path + "_callback"


def parse_callback(request):
    """
    解析回调结果

    :param request:
    :return:
    """
    params = {}
    for key in (
    "platformNo", "serviceName", "responseType", "keySerial", "respData", "userDevice", "sign"):
        params[key] = request.form.get(key, None)
    respData = params["respData"]
    if isinstance(respData, unicode):
        respData = respData.encode("utf8")
    sign = base64.decodestring(params["sign"])
    try:
        if check_sign(respData, sign) == 0:
            # TODO: 签名未验证通过，可能是伪造请求
            print "签名不正确"
        else:
            print "签名正确"
    except RSAError:
        # TODO: 验证不通过
        print "签名不正确2"
    params["respData"] = json.loads(params["respData"])
    return params


class Gateway(object):
    """
    网关接口
    """
    def get_context(self, ):
        pass

    def get(self):
        raise NotImplementedError()

    def __call__(self, *args, **kwargs):
        self.request = request
        return self.get()


@app.route('/bind', methods=['GET', 'POST'])
def bind():

    callback = get_callback_url(request)
    serviceName = "PERSONAL_REGISTER_EXPAND"
    reqData = {
        "platformUserNo": "100005",
        "requestNo": "100005",
        "idCardType": "PRC_ID",
        "userRole": "BORROWERS",
        "checkType": "LIMIT",
        "redirectUrl": callback,
        "userLimitType": "ID_CARD_NO_UNIQUE",
        "authList": "WITHDRAW,REPAYMENT",
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }
    reqData = json.dumps(reqData)
    params = {
        "serviceName": serviceName,
        "platformNo": PLATFORMNO,
        "reqData": reqData,
        "keySerial": 1,
        "sign": sha1withRSA(reqData)
    }

    return render_template('gateway.html', **params)


def create_project():
    """
    创建标的
    直连接口
    """
    requestNo = "100002"  # 请求流水号
    platformUserNo = "100004"  # 借款方平台用户编号, 用户类型要为 BORROWERS
    projectNo = "100001"  # 标的号
    projectAmount = "100000"  # 标的金额
    projectName = "借钱买车"  # 标的名称
    projectDescription = "借十万元买车，一年还"  # 标的描述
    projectType = "STANDARDPOWDER"  # 标的类型
    projectPeriod = "365"  # 标的期限，单位：天
    annnualInterestRate = 0.15  # 年化利率
    repaymentWay = "ONE_TIME_SERVICING"  # 还款方式，只做记录，不做严格校验
    extend = {"name": "SDF", "name2": "SF"}  # 标的扩展信息
    reqData = {
        "requestNo": requestNo,
        "platformUserNo": platformUserNo,
        "projectNo": projectNo,
        "projectAmount": projectAmount,
        "projectName": projectName,
        "projectDescription": projectDescription,
        "projectType": projectType,
        "projectPeriod": projectPeriod,
        "annnualInterestRate": annnualInterestRate,
        "repaymentWay": repaymentWay,
        "extend": extend,
        "timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }
    reqData = json.dumps(reqData)
    serviceName = "ESTABLISH_PROJECT"
    params = {
        "serviceName": serviceName,
        "platformNo": PLATFORMNO,
        "reqData": reqData,
        "keySerial": 1,
        "sign": sha1withRSA(reqData)
    }
    resp = requests.post(XW_API_URI, params)
    return resp


@app.route("/bind_callback", methods=["POST"])
def bind_callback():
    context = parse_callback(request)
    return render_template("gateway_callback.html", **context)


if __name__ == '__main__':
    app.run(port=8888)
