import os
import sys
import cdecimal
sys.modules["decimal"] = cdecimal


path = os.path.abspath(__name__)
