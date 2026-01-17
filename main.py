#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 - Present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam (谭淞)
# @Email  : sepinetam@gmail.com
# @File   : main.py

"""
Mini-Duolingo 启动脚本
运行此脚本启动Flask服务器
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app import app, init_csv_files

if __name__ == '__main__':
    # 初始化CSV文件
    init_csv_files()

    # 启动Flask应用
    print("=" * 50)
    print("Mini-Duolingo 正在启动...")
    print("访问地址: http://127.0.0.1:3000")
    print("=" * 50)

    app.run(debug=True, port=3000)
