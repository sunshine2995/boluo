#!/use/bin/env python
# -*- coding: UTF-8 -*-

from apps import create_app
from apps.dbinstance import db

app = create_app('config')
db.init_app(app)


if __name__ == '__main__':
    app.run(host=app.config['HOST'],
            port=app.config['PORT'],
            debug=app.config['DEBUG'])
