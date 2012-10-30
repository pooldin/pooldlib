import os
import sys
import cdecimal
sys.modules["decimal"] = cdecimal

from .config import Config as Config
config = Config()

DIR = os.path.abspath(__file__)
DIR = os.path.dirname(DIR)
