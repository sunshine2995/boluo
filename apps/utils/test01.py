#!/use/bin/env python
# -*- coding: UTF-8 -*-
from apps.asset.models import Member_recharge_info, Member_reflect_info, Member_red_pocket, Member_red_pocket_type, Member_asset_info, Province_city
from apps.product.models import Invest_info, Product_info

from models import Member, Member_real_info, Member_pay_info, Member_email_info, Member_invite, Member_invite_info, Member_bussnes, Member_invite_profit, Member_loan
from apps.dbinstance import db
from apps import app
from apps.utils import toolkit


@app.route('/v1/test/abcd', methods=['GET', 'POST'])
def test():
    response_data = {}
    return toolkit.response(response_data, 200, None, True)