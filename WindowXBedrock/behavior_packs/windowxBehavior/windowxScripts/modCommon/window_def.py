# -*- coding: utf-8 -*-
"""窗口数据模型（服务端权威状态的唯一定义）。

纯 dict，方便直接 JSON 序列化跨端传输；无 SDK 依赖。
"""
from __future__ import division

import re

from . import modConfig

ID_RE = re.compile(modConfig.WINDOW_ID_PATTERN)

DEFAULT_CONTENT = {'kind': 'text', 'path': '', 'mode': 'fit'}


def valid_id(wid):
    return bool(ID_RE.match(str(wid or '')))


def new_window(wid, owner, w, h, cx, cy, title='Window'):
    return {
        'id': wid,
        'owner': owner,
        'title': str(title)[:modConfig.MAX_TITLE_LEN],
        'cx': float(cx),
        'cy': float(cy),
        'w': float(w),
        'h': float(h),
        'color': 'black',
        'layer': 'normal',
        'visible': True,
        'content': dict(DEFAULT_CONTENT),
        'rev': 1,
    }


def snapshot(win):
    """深拷贝（content 是唯一嵌套层）。"""
    out = dict(win)
    out['content'] = dict(win.get('content') or DEFAULT_CONTENT)
    return out


def diff(old, new):
    """仅返回变化字段，用于增量补丁。content 单独比较。"""
    patch = {}
    for k, v in new.items():
        if k == 'content':
            if (old.get('content') or {}) != (v or {}):
                patch['content'] = dict(v or {})
            continue
        if old.get(k) != v:
            patch[k] = v
    return patch


def bump(win):
    win['rev'] = int(win.get('rev', 1)) + 1
    return win['rev']
