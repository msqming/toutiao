#! /usr/bin/env python
# -*- coding:utf-8 -*-
# Author:Ypp

import os

path = '{0}'.format(os.getcwd()+'/images')
pa = os.path.exists(path)
print(pa)