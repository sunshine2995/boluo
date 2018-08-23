from apps.dbinstance import db


class Message_info(db.Model):

    __tablename__ = "tjtyy_message"

    id = db.Column(db.Integer, primary_key= True)
    ip = db.Column(db.String(50))
    phone = db.Column(db.String(36))
    template_id = db.Column(db.String(36))
    verify_code = db.Column(db.String(36))
    send_time = db.Column(db.DateTime)
    is_verify = db.Column(db.Boolean)


class Error_log(db.Model):

    __tablename__ = "tjtyy_error_log"

    id = db.Column(db.Integer, primary_key=True)
    creat_time = db.Column(db.DateTime)
    description = db.Column(db.String(255))
    type = db.Column(db.String(64))
    phone = db.Column(db.String(64))



class Push_info(db.Model):

    __tablename__ = "tjtyy_push_info_log"

    id = db.Column(db.String(36), primary_key=True)
    user_type = db.Column(db.String(50))
    theme = db.Column(db.String(200))
    content = db.Column(db.String(500))
    create_date = db.Column(db.DateTime)
    push_date = db.Column(db.DateTime)
    state = db.Column(db.Integer)