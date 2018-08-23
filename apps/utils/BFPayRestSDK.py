# -*- coding: UTF-8 -*-

import requests
import json
from random import randint
from datetime import datetime


#BF_PARTNER = '1111411'   ####   member_id
BF_VERSION = '4.0.0.0'
BANK_B2C_CODE=["CMB", "ICBC", "CCB", "BOC", "ABC", "BOCM", "SPDB",
               "CITIC", "CEB", "CIB", "CMBC", "HXB", "PSBC",
               "PAB", "BOHAI", "GDB"]
#BF_TERMINAL_RECHARGE = '32990'    ####  terminal_id
#BF_TERMINAL_DF = '32989'
BF_TEST_TERMINAID = '100000990'   #####  terminal_id
BF_TEST_PARTNER = '100000276'     ####  member_id
TEST_API = 'https://tgw.baofoo.com/cutpayment/api/backTransRequest'
# 公钥证书：bfkey_100000276@@100000990.cer
# 私钥证书：bfkey_100000276@@100000990.pfx
# 商 户 号：100000276
# 终 端 号：100000990
# 证书密码：123456
#
# 测试卡号：6222020111122220000
# 测试姓名：张宝
# 测试证件：320301198502169142
# 测试银行：工商银行
# 测试手机：自行输入，不做校验
# 测试bindid：201604271949318660


def RSA_encode(signdata):

    url = 'http://apitest.boluolc.com:8081/jeecg/baofuController.do?encode'
    ss = requests.session()
    req = ss.post(url,data = signdata,verify = False)
    cont = req.content
    print cont
    Msg = json.loads(cont)
    ChkValue = Msg[u'msg'].encode()
    return ChkValue

def RSA_decode(signdata):

    url = 'http://apitest.boluolc.com:8081/jeecg/baofuController.do?decode'
    poststring = {}
    poststring['postString'] = signdata
    ss = requests.session()
    req = ss.post(url,data = poststring,verify = False)
    cont = req.content
    print cont
    Msg = json.loads(cont)
    result = Msg[u'msg']
    return result

class BFPay(object):
    version = ''
    txn_type = ''
    member_id = ''
    data_type = ''
    biz_type = ""
    id_card_type = ''
    acc_pwd = ''
    valid_date = ''
    valid_no = ''
    additional_info = ''
    req_reserved = ''
    params = {}

    def __init__(self, user_id=None):
        self.user_id = user_id
        self.version = BF_VERSION
        self.txn_type = '0431'
        self.member_id = BF_TEST_PARTNER
        self.data_type = 'json'
        self.biz_type = "0000"
        self.id_card_type = '01'
        self.acc_pwd = ''
        self.valid_date = ''
        self.valid_no = ''
        self.additional_info = '附加字段'
        self.req_reserved = '保留'
        self.params = dict(version=BF_VERSION,terminal_id=BF_TEST_TERMINAID,txn_type = '0431',\
            member_id = BF_TEST_PARTNER,data_type = 'json')

    def bf_post(self,pay_params):
        params = self.params
        data_content = ''
        txn_sub_type = pay_params.get('txn_sub_type',None)
        encryptParams = {}
        encrypt_dict = {}
        if txn_sub_type is not None:
            params['txn_sub_type'] = txn_sub_type
            encryptParams = dict(txn_sub_type=txn_sub_type,biz_type='0000',terminal_id=BF_TEST_TERMINAID,member_id=BF_TEST_PARTNER,trade_date = datetime.strftime(datetime.now(), '%Y%m%d%H%M%S'))
        else:
            return '参数txn_sub_type为空'
        ####预绑卡类交易
        if txn_sub_type == '11':        
            id_holder = pay_params.get('id_holder',None)
            id_card = pay_params.get('id_card',None)
            acc_no = pay_params.get('acc_no',None)
            mobile = pay_params.get('mobile',None)
            pay_code = pay_params.get('pay_code',None)
            encrypt_dict = dict(trans_serial_no=partnerFlowNum(),trans_id = partnerFlowNum(), acc_no=acc_no,\
                id_card = id_card,id_holder = id_holder,mobile = mobile,pay_code = pay_code) 
        ###确认绑卡类交易 
        elif txn_sub_type == '12':   
            sms_code = pay_params.get('sms_code',None)
            encrypt_dict = dict(trans_serial_no=partnerFlowNum(),trans_id = partnerFlowNum(),sms_code = sms_code)
         ####直接绑卡类交易
        elif txn_sub_type == '01':
            id_holder = pay_params.get('id_holder',None)
            id_card = pay_params.get('id_card',None)
            acc_no = pay_params.get('acc_no',None)
            mobile = pay_params.get('mobile',None)
            pay_code = pay_params.get('pay_code',None)
            encrypt_dict = dict(trans_serial_no=partnerFlowNum(),trans_id = partnerFlowNum(), acc_no=acc_no,\
                id_card = id_card,id_holder = id_holder,mobile = mobile,pay_code = pay_code) 
        #解除绑定关系交易   '201604271949318660'
        elif txn_sub_type == '02':  
            bind_id = pay_params.get('id_holder',None)
            encrypt_dict = dict(trans_serial_no=partnerFlowNum(),bind_id=bind_id)
        ### 查询绑定
        elif txn_sub_type == '03':  
            acc_no = pay_params.get('acc_no',None)
            encrypt_dict = dict(trans_serial_no=partnerFlowNum(),acc_no = acc_no)
            
        #####认证支付类预支付交易
        elif txn_sub_type == '15':
            bind_id = pay_params.get('bind_id',None)
            txn_amt = pay_params.get('txn_amt',None)
            risk_content = pay_params.get('risk_content',None)
            encrypt_dict = dict(trans_serial_no=partnerFlowNum(),trans_id = partnerFlowNum(),\
                           bind_id=bind_id,txn_amt = txn_amt,risk_content = risk_content)
           

        #认证支付类支付确认交易
        elif txn_sub_type == '16':
            business_no = pay_params.get('business_no',None)
            encrypt_dict = dict(trans_serial_no=partnerFlowNum(),business_no = business_no)
            
         ##### 交易状态查询类
        elif txn_sub_type == '06':
            orig_trans_id = pay_params.get('orig_trans_id',None)
            encrypt_dict = dict(trans_serial_no=partnerFlowNum(),orig_trans_id = orig_trans_id)
        else:
            return '参数txn_sub_type错误'
        encryptParams.update(encrypt_dict)
        data_content = RSA_encode(encryptParams)
        params['data_content'] = data_content    
        ss = requests.session()
        req = ss.post(TEST_API,data = params,verify = False)
        cont = req.content
        result = RSA_decode(cont)
        return result       

def rand4():
    return str(randint(1000,9999))

#日期
def getCurrentDateTimeStr():
    now_time = datetime.strftime(datetime.now(), '%Y%m%d%H%M%S')
    return now_time

#商户流水号
def partnerFlowNum():
    return getCurrentDateTimeStr() + rand4()


if __name__ == '__main__':

    bf = BFPay()
    import pdb
    pdb.set_trace()
    pay_params = dict(txn_sub_type = '11',id_holder ='张宝' ,id_card ='320301198502169142',acc_no = '6222020111122220000',mobile = '18636747623',pay_code = 'ICBC')
    #pay_params = dict(txn_sub_type = '12',sms_code = '111111')
    # pay_params = dict(txn_sub_type = '01',id_holder ='张宝' ,id_card ='320301198502169142',acc_no = '6222020111122220000',mobile = '18636747623',pay_code = 'ICBC')
    #pay_params = dict(txn_sub_type = '02',id_holder = '201604271949318660')
    result = bf.bf_post(pay_params)
    #bf.relieve_bindCard()
    #bf.query_bindCard('6222020111122220000')
    #bf.prePay()
    #bf.ensure_prePay('123456789')
    #bf.is_pay('15645645')
    print result
