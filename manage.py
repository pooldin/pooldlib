import os
from cement.core import controller

DIR = os.path.dirname(__file__)
DIR = os.path.abspath(DIR)

from pooldlib import cli


class RootController(cli.RootController):
    class Meta:
        label = 'base'
        description = "Management tools for the Poold.in website."


class App(cli.App):
    class Meta:
        label = 'pooldwww'
        base_controller = RootController
        handlers = (cli.ShellController,)


if __name__ == '__main__':
    App.execute()
