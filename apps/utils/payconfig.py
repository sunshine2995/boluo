#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from Crypto.PublicKey import RSA
from config import BOLUO_URL


YT_PUB_KEY = RSA.importKey(open('./apps/utils/rsa_public_key.pem','r').read())
TRADER_PRI_KEY = RSA.importKey(open('./apps/utils/pkcs8_rsa_private_key.pem','r').read())
#YT_PUB_KEY = RSA.importKey(open('./apps/utils/test_rsa_public_key.pem','r').read())
#TRADER_PRI_KEY = RSA.importKey(open('./apps/utils/test_rsa_private_key.pem','r').read())
MD5_KEY = "201510281000562502_boluolc_20151028"
NOTIFY_URL = BOLUO_URL + "/v1/asset/%s/%s/llrecharge/result"
OID_PARTNER = "201510281000562502"
#OID_PARTNER = "201408071000001539"
SIGN_TYPE = "RSA"
#SIGN_TYPE = "MD5"
VERSION = "1.0"
#BUSI_PARTNER = "108001"
BUSI_PARTNER = "101001"
PAY_TYPE = "D"
ID_TYPE = "0"
CHARSET_NAME = "utf-8"
BANK_CODE = ['01020000','01040000','01030000','03080000', '03030000', '03100000']