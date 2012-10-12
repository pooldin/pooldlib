import os
import signal
from cement.core import controller, exc


class ServerController(controller.CementBaseController):

    class Meta:
        label = 'runserver'
        description = "Run the flask development server"

    @controller.expose(hide=True, help='Run the flask development server')
    def default(self):
        app = getattr(self, 'flask_app')
        self.run(app)

    def run(self, app, **kw):
        kw['debug'] = True
        kw.setdefault('host', os.environ.get('HOST', '0.0.0.0'))
        kw.setdefault('port', int(os.environ.get('PORT', 5000)))

        while True:
            try:
                app.run(**kw)
            except exc.CaughtSignal, e:
                if e.signum != signal.SIGHUP:
                    return
