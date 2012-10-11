from cement.core import CementBaseController, expose


class RootController(CementBaseController):
    class Meta:
        label = 'root'

    @expose(hide=True)
    def default(self):
        self.app.args.print_help()
