# -*- coding: UTF-8 -*-
from time import time
from random import randint


def gen_order_id():
    order_id = '%s%s' % (int(time()), randint(1000000000, 10000000000))
    return order_id