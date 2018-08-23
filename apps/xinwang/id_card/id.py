#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   Author: Tony NIU
#   niuwl586@gmail.com
#   Created at 2017/5/15 17:48

import json
import os


DIR_PATH = os.path.dirname(os.path.abspath(__file__))

def id_card_verify(id_card_no):
    """
    身份证号验证，简单检查身份证号是否通过校验
    通过检查前17位求出最后一位校验位，是否与身份证号校验位一致

    :param id_card_no:
    :return:
    """
    weight = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    verify_code = ('1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2')

    _sum = 0
    for i, c in enumerate(id_card_no[:-1]):
        _sum += int(c) * weight[i]
    return verify_code[_sum % 11] == id_card_no[-1]



area_dict = json.loads(file(os.path.join(DIR_PATH, "id_area.txt")).read())


def get_address(id_card_no):
    """
    根据身份证好查询地址

    :param id_card_no:
    :return:
    """
    district = area_dict.get(id_card_no[:6], "未知")
    city = area_dict.get(id_card_no[:4] + "00", "未知")
    province = area_dict.get(id_card_no[:2] + "0000", "未知")
    return province, city, district
