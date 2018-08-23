#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Author: Tony NIU
#   niuwl586@gmail.com
#   Created at 2017/5/4 17:11

import base64
import os
from urllib import unquote
import rsa
import M2Crypto
from config import PLATFORMNO

DIR_PATH = os.path.dirname(os.path.abspath(__file__))


def sha1withRSA(data):
    """
    SHA1withRSA 签名

    :param data: 要签名的数据
    :return: 签名结果16
    """
    md = M2Crypto.EVP.MessageDigest('sha1')
    md.update(data)
    p = md.digest()

    # 自己平台的私钥，用于签名
    path = os.path.join(DIR_PATH, "self.ppk")
    key = M2Crypto.RSA.load_key(path)
    enc = key.sign(p)
    return base64.encodestring(enc)


def sha1withRSA_(data):
    """
    SHA1withRSA 签名

    :param data: 要签名的数据
    :return: 签名结果
    """
    import binascii
    from Crypto.Hash import SHA
    from Crypto.Signature import PKCS1_v1_5 as Signature_pkcs1_v1_5
    from Crypto.PublicKey import RSA
    path = os.path.join(DIR_PATH, "self.ppk")
    with open(path) as f:
        key = f.read()
        print key
        rsakey = RSA.importKey(key)
        signer = Signature_pkcs1_v1_5.new(rsakey)
        digest = SHA.new()
        digest.update(data)
        sign = signer.sign(digest)
        return base64.encodestring(sign)


def check_sign(data, sign):
    """
    检查签名是否正确

    :param data: 待验证数据
    :param sign: 签名
    :return: 是否验证正确
    """
    md = M2Crypto.EVP.MessageDigest('sha1')
    md.update(data)
    p = md.digest()

    # 新网网关的公钥，用于验证签名正确性，如果不正确，可能是伪造的请求
    path = os.path.join(DIR_PATH, "xw_%s.pub" % PLATFORMNO)
    key = M2Crypto.RSA.load_pub_key(path)
    return key.verify(p, sign)


def check_sign_bak(data, sign):
    """
    检查签名是否正确

    :param data: 待验证数据
    :param sign: 签名
    :return: 是否验证正确
    """
    md = M2Crypto.EVP.MessageDigest('sha1')
    md.update(data)
    p = md.digest()
    print p
    # 新网网关的公钥，用于验证签名正确性，如果不正确，可能是伪造的请求
    path = os.path.join(DIR_PATH, "self.pub")
    print path
    key = M2Crypto.RSA.load_pub_key(path)
    print key
    return key.verify(p, sign)


def check_sign_(data, sign):
    """
    检查签名是否正确

    :param data: 待验证数据
    :param sign: 签名
    :return: 是否验证正确
    """
    from Crypto.Hash import SHA
    from Crypto.Signature import PKCS1_v1_5 as Signature_pkcs1_v1_5
    from Crypto.PublicKey import RSA
    path = os.path.join(DIR_PATH, "xw.pub")
    with open(path) as f:
        key = f.read()
        print key
        rsakey = RSA.importKey(key)
        verifier = Signature_pkcs1_v1_5.new(rsakey)
        digest = SHA.new()
        digest.update(data)
        print digest
        return verifier.verify(digest, base64.decodestring(sign))


def parse_callback(body):
    """
    处理回调

    :param body: POST请求消息体
    :return:
    """
    data = unicode(body)


if __name__ == '__main__':
    res = sha1withRSA('123')
    print res
    print check_sign_bak('123', res)

    # print sha1withRSA('123') == sha1withRSA_('123')
    #
    # res = sha1withRSA_('123')
    # print res
    # print check_sign_('123', res)
