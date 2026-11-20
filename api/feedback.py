# -*- coding: utf-8 -*-
"""
Vercel Serverless Function for /api/feedback
"""
import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import MinhAnApiHandler

class handler(MinhAnApiHandler):
    def get_route_path(self):
        return '/api/feedback'

