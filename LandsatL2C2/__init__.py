from os.path import join, abspath, dirname

from .LandsatL2C2 import *
from .backends import LandsatBackend, M2MBackend, S3Backend, create_backend

with open(join(abspath(dirname(__file__)), "version.txt")) as f:
    version = f.read()

__version__ = version
__author__ = "Gregory H. Halverson"
