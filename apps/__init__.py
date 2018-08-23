from flask import Flask

app = Flask("boluolc-api")

def create_app(config_filename):
    app.config.from_object(config_filename)

    from apps.dbinstance import db
    from apps.dbinstance import redis
    from apps.member.models import Member, Member_log
    from apps.news.models import News,Sort
    from apps.product.models import Product_info,Organ_info,\
                                    Borrower_info,Feature_info,\
                                    Invest_info,Product_image

    from apps.message.models import Message_info
    from apps.asset.models import Member_asset_info,\
                                    Member_recharge_info,\
                                    Member_reflect_info
    db.init_app(app)
    redis.init_app(app)

    # will use blue_print
    import member.views
    import news.views
    import product.views
    import message.views
    import asset.views
    import activity.views
    import html5.views
    import pc.views
    return app

