import os
import sys
import cdecimal
sys.modules["decimal"] = cdecimal


DIR = os.path.dirname(__file__)
DIR = os.path.abspath(__file__)
