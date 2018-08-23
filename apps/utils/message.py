#!/use/bin/env python
# -*- coding: UTF-8 -*-

from apps.utils.CCPRestSDK import REST
from config import ACCOUNT_SID, ACCOUNT_TOKEN,\
                   APP_ID, SERVER_IP, SERVER_PORT, SOFT_VERSION

def send_message(to_phone, datas, template_id):

    rest = REST(SERVER_IP,SERVER_PORT,SOFT_VERSION)
    rest.setAccount(ACCOUNT_SID,ACCOUNT_TOKEN)
    rest.setAppId(APP_ID)
    rest.sendTemplateSMS(to_phone,datas,int(template_id))
