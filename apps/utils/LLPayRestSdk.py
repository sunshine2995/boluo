#!/use/bin/env python
# -*- coding: UTF-8 -*-

import hashlib
import base64
from datetime import datetime
import urllib2
import json
from xmltojson import xmltojson
from xml.dom import minidom
import requests
import struct
from Crypto import Random
from Crypto.Cipher import PKCS1_v1_5
from Crypto.Hash import SHA, MD5
from hashlib import sha1
from rsa import key, common, encrypt
from Crypto.PublicKey import RSA
import time
import json
from Crypto.Signature import PKCS1_v1_5 as pk

from payconfig import BUSI_PARTNER, OID_PARTNER, TRADER_PRI_KEY, CHARSET_NAME, MD5_KEY,\
                       NOTIFY_URL, VERSION, YT_PUB_KEY, SIGN_TYPE, PAY_TYPE, ID_TYPE



def md5util(content):
    md = hashlib.md5()
    kkey = "&key=%s" % MD5_KEY
    content += kkey
    md.update(content)
    #md.update(MD5_KEY)
    return  md.hexdigest()

def RSASign(signdata):

    h=MD5.new(signdata)
    signer = pk.new(TRADER_PRI_KEY)
    signn=signer.sign(h)
    signn=base64.b64encode(signn)
    return signn

def checkRSASign(rdata):

    signn=base64.b64decode(rdata.pop('sign'))
    signdata=getSort(rdata)
    verifier = pk.new(YT_PUB_KEY)
    if verifier.verify(MD5.new(signdata), signn):
        print "The signature is authentic."
    else:
        print "The signature is not authentic."

def getSort(params):
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')
    keys=params.keys()
    keys.sort()
    message = ""
    for key in keys:
        if key != "risk_item":
            message += key + "=" + params[key]+ "&"
        else:
            message += key + "=" + str(json.dumps(params[key], ensure_ascii=False)).replace(" ", "").replace("\"", "'") + "&"
    # print message
    return message.rstrip('&')

def getMobileSort(params):
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')
    keys=params.keys()
    keys.sort()
    nsign = ["platform", "user_id", "force_bank", "id_type", "id_no", "acct_name", "card_no", "no_agree", "shareing_data"]
    message = ""
    for key in keys:
        if key not in nsign:
            message += key + "=" + params[key]+ "&"
    # print message
    return message.rstrip('&')

def getCurrentDateTimeStr():
    now_time = datetime.strftime(datetime.now(), '%Y%m%d%H%M%S')
    return now_time

class LLPayRest(object):

    version = ""
    charset_name = ""
    oid_partner = ""
    timestamp = ""
    sign_type = ""
    user_id = ""

    pay_params = {}
    order_dict = {}
    risk_item_dict = {}
    base_dict = {}

    def __init__(self, user_id=None):

        self.version = VERSION
        self.charset_name = CHARSET_NAME
        self.oid_partner = OID_PARTNER
        self.sign_type = SIGN_TYPE
        self.timestamp = getCurrentDateTimeStr()
        self.user_id = user_id

        self.pay_params= dict(oid_partner=self.oid_partner, sign_type=self.sign_type, user_id=self.user_id)

    def setUserId(self, user_id):
        self.user_id = user_id
        self.pay_params["user_id"] = user_id

    def setPayBaseParams(self):
        self.base_dict = dict(id_type=ID_TYPE, busi_partner=BUSI_PARTNER)

    def setOrderParam(self, no_order, dt_order, name_goods, info_order, *args, **kwargs):
        self.order_dict = dict(no_order=no_order, dt_order=dt_order, name_goods=name_goods, info_order=info_order, **kwargs)

    def setRiskItem(self, frms_ware_category, user_info_mercht_userno, user_info_dt_register,user_info_full_name, user_info_id_no, *args, **kwargs):

        risk_dict = dict(frms_ware_category=frms_ware_category, user_info_mercht_userno=user_info_mercht_userno, \
                         user_info_dt_register=user_info_dt_register,user_info_full_name=user_info_full_name, \
                         user_info_id_no=user_info_id_no, **kwargs)
        
        self.risk_item_dict["risk_item"] = str(json.dumps(risk_dict, ensure_ascii=False)).replace(" ", "").replace("\"", "\"")


    def user_bank_card(self, card_no):
        # construct params
        offset = "0"
        pay_type = "D"
        params =dict(oid_partner=self.oid_partner, sign_type=self.sign_type, card_no=str(card_no), \
                     pay_type=pay_type, user_id=self.user_id, offset=offset)
        sign_str = getSort(params)
        #sign = md5util(sign_str)
        sign = RSASign(sign_str)
        params["sign"] = sign
        user_bank_card_API = "https://traderapi.lianlianpay.com/userbankcard.htm"
        
        response_data = {}
        headers = {"Accept":"text/plain", "Content-type":"application/json;charset=utf-8"}
        r = requests.post(user_bank_card_API, data=json.dumps(params), headers=headers, verify = False)
        if r.status_code == 200 or r.status_code ==201:
            response_data["code"]=u"0"
            response_data["content"] = json.loads(r.text)
            return response_data
        else:
            response_data["code"]=u"1"
            response_data["content"] = u"Network is unreachable"
            return response_data 

    def bank_card_auth_bin(self, card_no):
        pay_type = "D"
        flag_amt_limit = "1"
        api_version = "1.1" 
        params =dict(api_version=api_version, oid_partner=self.oid_partner, sign_type=self.sign_type, \
                     card_no=str(card_no), pay_type=pay_type, flag_amt_limit=flag_amt_limit)
        sign_str = getSort(params)
        #sign = md5util(sign_str)
        sign = RSASign(sign_str)
        params["sign"] = sign

        bank_card_bin_API = "https://traderapi.lianlianpay.com/bankcardquery.htm"
        response_data = {}
        headers = {"Accept":"text/plain", "Content-type":"application/json;charset=utf-8"}
        r = requests.post(bank_card_bin_API, data=json.dumps(params), headers=headers, verify = False)
        if r.status_code == 200 or r.status_code ==201:
            response_data["code"]=u"0"
            response_data["content"] = json.loads(r.text)
            return response_data
        else:
            response_data["code"]=u"1"
            response_data["content"] = u"Network is unreachable"
            return response_data

    def authPay(self, acct_name, id_no, card_no, money_order, bank_code, *args, **kwargs):

        pay_type = "D"
        auth_pay_API = "https://cashier.lianlianpay.com/payment/authpay.htm"
        pay_params = {}
        notify_url=(NOTIFY_URL) % (self.user_id, card_no)
        params=dict(notify_url=notify_url, acct_name=acct_name, id_no=id_no, card_no=card_no, \
                    money_order=money_order, bank_code=bank_code, pay_type=pay_type, **kwargs)
        self.pay_params.update(params)
        self.pay_params.update(self.base_dict)
        self.pay_params.update(self.order_dict)
        self.pay_params.update(self.risk_item_dict)
        params_str = getSort(self.pay_params)
        sign = RSASign(params_str)
        self.pay_params["sign"]=sign
        response_data = {}
        # print self.pay_params
        html = "<form id=\"llpaysubmit\" name=\"llpaysubmit\" action=\"%s\" method=\"post\">" % auth_pay_API
        for key, value in self.pay_params.items():
            if key != "risk_item":
                html+="<input type=\"hidden\" name=\"%s\" value=\"%s\"/>" % (key, value)
            else:
                html+="<input type=\"hidden\" name=\"%s\" value=\"%s\"/>" % (key, \
                      json.dumps(value, ensure_ascii=False).replace(" ", "").replace("\"","'"))
        html += "</form>"
        html += "<script>document.forms[\"llpaysubmit\"].submit();</script>"
        response_data["code"] = u"0"
        response_data["content"] = html
        return response_data


    def mobilePay(self, acct_name, id_no, card_no, money_order, *args, **kwargs):
       
        notify_url=(NOTIFY_URL) % (self.user_id, card_no) 
        params=dict(notify_url=notify_url, acct_name=acct_name, id_no=id_no, card_no=card_no, money_order=money_order, **kwargs)
        self.pay_params.update(params)
        self.pay_params.update(self.base_dict)
        self.pay_params.update(self.order_dict)
        self.pay_params.update(self.risk_item_dict)
        params_str = getMobileSort(self.pay_params)
        sign = RSASign(params_str)
        self.pay_params["sign"]=sign
        return self.pay_params
        

    def CNAPSCodeQuery(self, bank_code, brabank_name, city_code):
        
        params = dict(oid_partner=self.oid_partner, sign_type=self.sign_type, bank_code=bank_code, brabank_name=brabank_name, city_code=city_code) 
        sign_str = getSort(params)
        sign = RSASign(sign_str)
        #sign = md5util(sign_str)
        params["sign"] = sign

        CNAPS_API = "https://traderapi.lianlianpay.com/CNAPSCodeQuery.htm"
        response_data = {}
        headers = {"Accept":"text/plain", "Content-type":"application/json;charset=utf-8"}
        r = requests.post(CNAPS_API, data=json.dumps(params), headers=headers, verify = False)
        if r.status_code == 200 or r.status_code ==201:
            response_data["code"]=u"10000"
            response_data["content"] = json.loads(r.text)
            return response_data
        else:
            response_data["code"]=u"10001"
            response_data["content"] = u"Network is unreachable"
            return response_data

    def setHttpHeader(self,req):
        if self.BodyType == 'json':
            req.add_header("Accept", "application/json")
            req.add_header("Content-Type", "application/json;charset=utf-8")

        else:
            req.add_header("Accept", "application/xml")
            req.add_header("Content-Type", "application/xml;charset=utf-8")
