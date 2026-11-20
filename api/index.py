# -*- coding: utf-8 -*-
"""
Vercel Serverless Function entry point for Minh An AI Agent.
"""
import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import MinhAnApiHandler

class handler(MinhAnApiHandler):
    pass
