#!/usr/bin/env python
# -*- coding: utf-8 -*-

# only needed if not using gunicorn gevent
if __name__ == '__main__':
    import gevent.monkey
    gevent.monkey.patch_all()

from run import app  # noqa

if __name__ == '__main__':
    app.run(host=app.config['HOST'],
            port=app.config['PORT'],
            debug=app.config['INFO'])

