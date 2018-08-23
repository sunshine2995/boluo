#!/use/bin/env python
# -*- coding: UTF-8 -*-

import hashlib
import base64
import datetime
import urllib2
import json
from xmltojson import xmltojson
from xml.dom import minidom
import requests


SERVICE = "reapal.trust.realNameAuth"
PARTNER = "100000000008910"
SIGNTYPE = "md5"
SIGNKEY = "cd96cagf706694826eb189647g24ge35e0d1cd50a1cgg481f0a575da0cg6e113"

BANK_B2C_CODE=["CMB", "ICBC", "CCB", "BOC", "ABC", "BOCM", "SPDB", "CGB",
               "CITIC", "CEB", "CIB", "SDB", "CMBC", "HXB", "PSBC", "BCCB",
               "SHBANK", "BOHAI", "SHNS"]

BANK_B2B_CODE=["ICBC_B2B", "CCB_B2B", "BOC_B2B", "ABC_B2B", "BOCM_B2B", "SPDB_B2B",
               "CEB_B2B", "SDB_B2B", "CMBC_B2B"]


def md5util(content, key):
    md = hashlib.md5()
    md.update(content)
    md.update(key)
    return  md.hexdigest()

class RealRest(object):

    signkey=SIGNKEY
    signType=SIGNTYPE
    version=""
    service=SERVICE
    partner=PARTNER

    def __init__(self, version):

        self.version = version

    def sign_content(self, content, signkey):

        return  md5util(content, signkey)

    # real_info verify include bankcard and id.
    def request_real_info_auth(self, content, api_url):

        sign = self.sign_content(content, self.signkey)

        params = {"sign": sign, "signType": self.signType, "version": self.version,
                  "service":self.service, "partner":self.partner, "reqData":content}

        respone_data = {}
        try:
            r = requests.get(api_url, params=params, verify = False)
            respone_data["code"] = r.status
            respone_data["content"]=r.text
            return respone_data
        except:
            respone_data["code"]="172001"
            respone_data["content"]="网络错误"
            return respone_data

    #设置包头
    def setHttpHeader(self,req):
        if self.BodyType == 'json':
            req.add_header("Accept", "application/json")
            req.add_header("Content-Type", "application/json;charset=utf-8")
        else:
            req.add_header("Accept", "application/xml")
            req.add_header("Content-Type", "application/xml;charset=utf-8")

class PayRest(object):


    signkey=SIGNKEY
    signType=SIGNTYPE
    service=""
    merchant_ID=PARTNER
    charset=""
    paymethod=""
    payment_type=""
    pay_cus_no=""
    defaultbank=""
    seller_email="13810354654@163.com"
    buyer_email=""
    service_fee=""


    def __init__(self, service, charset):

        self.service = service
        self.charset = charset

    def sign_content(self, content, signkey):

        return  md5util(content, signkey)

    # 银行间间接支付
    def post_bank_pay_info(self, content, api_url, notify_url, return_url):

        title = content.get("title", None)
        body = content.get("body", None)
        order_no = content.get("order_no", None)
        total_fee = content.get("total_fee", None)

        self.payment_type = "1"
        self.paymethod = "paybank"

        respone_data = {}

        if title is None or body is None or order_no is None or total_fee is None\
           or title == "" or body == "" or order_no == "" or total_fee == "":
            respone_data["code"] = u"1"
            respone_data["content"] = u"参数不能为空"

        all_content = "{\"service\":%s, \"merchant_ID\":%s, \"notify_url\":%s, \"return_url\":%s," \
                      "\"charset\":%s, \"title\":%s, \"body\":%s, \"order_no\":%s, \"total_fee\":%s," \
                      "\"payment_type\":%s, \"paymethod\":%s, \"seller_email\":%s}" \
                      % (self.service, self.merchant_ID, notify_url, return_url, self.charset, title, body,
                         order_no, total_fee, self.payment_type, self.paymethod, self.seller_email)

        sign = self.sign_content(all_content, self.signkey)
        params = {"service":self.service, "merchant_ID":self.merchant_ID, "notify_url":notify_url, "return_url":return_url,
                  "charset":self.charset, "title":title, "body":body, "order_no":order_no, "total_fee":total_fee,
                  "payment_type":self.payment_type, "paymethod":self.paymethod, "seller_email":self.seller_email,
                  "sign": sign, "signType": self.signType}

        try:
            r = requests.get(api_url, params=params, verify = False)
            return r
        except:
            respone_data["code"]=u"172001"
            respone_data["content"]=u"网络错误"
            return respone_data


    def post_direct_pay_info(self, content, api_url, return_url, notify_url):

        title = content.get("title", None)
        body = content.get("body", None)
        order_no = content.get("order_no", None)
        total_fee = content.get("total_fee", None)
        bank_code = content.get("bank_code", None)
        bank_type = content.get("bank_type", None)

        self.paymethod = "directPay"

        response_data = {}
        if title is None or body is None or order_no is None or total_fee is None or bank_code is None or bank_type is None\
           or title == "" or body == "" or order_no == "" or total_fee == "" or bank_type == "" or bank_code == "":
            response_data["code"] = u"1"
            response_data["content"] = u"参数不能为空"
            return response_data

        self.defaultbank = bank_code

        all_content = None

        if bank_code in BANK_B2C_CODE:
            if bank_type == "1":
                self.payment_type = "1"
            elif bank_type == "2":
                self.payment_type = "2"

            all_content = "{\"body\":\"%s\", \"charset\":\"%s\", \"defaultbank\":\"%s\", \"merchant_ID\":\"%s\"," \
                      "\"notify_url\":\"%s\", \"order_no\":\"%s\", \"payment_type\":\"%s\", \"paymethod\":\"%s\", \"return_url\":\"%s\"," \
                      "\"seller_email\":\"%s\", \"service\":\"%s\", \"title\":\"%s\", \"total_fee\":\"%s\"}" \
                      % (body, self.charset, self.defaultbank, self.merchant_ID, notify_url, order_no, self.payment_type,
                         self.paymethod, return_url, self.seller_email, self.service, title, total_fee)
        elif bank_code in BANK_B2B_CODE:
            self.payment_type = "1"
            if bank_code == "BOCM_B2B" or bank_code == "CMBC_B2B" or bank_code == "SPDB_B2B":
                self.pay_cus_no == content.get("pay_cus_no", None)
                if self.pay_cus_no is None or self.pay_cus_no =="":
                    response_data["code"] = u"2"
                    response_data["content"] = u"需要银行账户或者客户号"
                    return response_data

                all_content = "{\"body\":\"%s\", \"charset\":\"%s\", \"defaultbank\":\"%s\", \"merchant_ID\":\"%s\"," \
                      "\"notify_url\":\"%s\", \"order_no\":\"%s\", \"pay_cus_no\":\"%s\" \"payment_type\":\"%s\", \"paymethod\":\"%s\", " \
                      "\"return_url\":\"%s\",\"seller_email\":\"%s\", \"service\":\"%s\", \"title\":\"%s\", \"total_fee\":\"%s\"}" \
                      % (body, self.charset, self.defaultbank, self.merchant_ID, notify_url, order_no, self.pay_cus_no, self.payment_type,
                         self.paymethod, return_url, self.seller_email, self.service, title, total_fee)

            else:
                all_content = "{\"body\":\"%s\", \"charset\":\"%s\", \"defaultbank\":\"%s\", \"merchant_ID\":\"%s\"," \
                      "\"notify_url\":\"%s\", \"order_no\":\"%s\", \"payment_type\":\"%s\", \"paymethod\":\"%s\", \"return_url\":\"%s\"," \
                      "\"seller_email\":\"%s\", \"service\":\"%s\", \"title\":\"%s\", \"total_fee\":\"%s\"}" \
                      % (body, self.charset, self.defaultbank, self.merchant_ID, notify_url, order_no, self.payment_type,
                         self.paymethod, return_url, self.seller_email, self.service, title, total_fee)

        else:
            response_data["code"] = u"2"
            response_data["content"] = u"银行支付类型错误"
            return  response_data

        if all_content == None:
            response_data["code"] = u"3"
            response_data["content"] = u"银行参数错误"
            return  response_data

        params_str = ""
        params = json.loads(all_content)
        for k in sorted(params.keys()):
            params_str += k.encode("utf-8") + "=" + params[k].encode("utf-8")+ "&"

        sign = self.sign_content(params_str.rstrip("&"), self.signkey)
        params["sign"] = sign
        params["sign_type"] = self.signType
        
        try:
            r = requests.get(api_url, params=params, verify = False)
            response_data["code"] = r.status_code
            response_data["content"] = r.text
            return response_data
        except:
            response_data["code"]=u"172001"
            response_data["content"]=u"网络错误"
            return response_data


    def setHttpHeader(self,req):
        if self.BodyType == 'json':
            req.add_header("Accept", "application/json")
            req.add_header("Content-Type", "application/json;charset=utf-8")

        else:
            req.add_header("Accept", "application/xml")
            req.add_header("Content-Type", "application/xml;charset=utf-8")


