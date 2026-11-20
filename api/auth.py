# -*- coding: utf-8 -*-
"""
Vercel Serverless Function for /api/auth
"""
import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import MinhAnApiHandler

class handler(MinhAnApiHandler):
    def get_route_path(self):
        url = self.path
        if 'login' in url:
            return '/api/auth/login'
        elif 'register' in url:
            return '/api/auth/register'
        return '/api/auth/me'
