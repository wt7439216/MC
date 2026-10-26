# -*- coding: utf-8 -*-
"""服务端<->客户端 协议（增量补丁 + 操作指令）。纯逻辑。"""
from __future__ import division

from . import modConfig

PROTO_VERSION = 1
MAX_OPS_PER_PACKET = 24
MAX_TITLE_LEN = modConfig.MAX_TITLE_LEN

VALID_OPS = ('create', 'remove', 'anim', 'fx', 'physics', 'follow', 'set', 'stop')


def make_patch(owner, rev, ops):
    """生成一个补丁包；ops 会被截断到上限，防单包过大。"""
    return {
        'v': PROTO_VERSION,
        'owner': owner,
        'rev': int(rev),
        'ops': list(ops)[:MAX_OPS_PER_PACKET],
        'truncated': len(ops) > MAX_OPS_PER_PACKET,
    }


def make_full(owner, rev, windows):
    return {
        'v': PROTO_VERSION,
        'owner': owner,
        'rev': int(rev),
        'windows': [dict(w) for w in windows],
    }


def validate_patch(pkt):
    if not isinstance(pkt, dict):
        return False, 'packet not a dict'
    if pkt.get('v') != PROTO_VERSION:
        return False, 'version mismatch'
    if not isinstance(pkt.get('ops'), (list, tuple)):
        return False, 'ops missing'
    for op in pkt['ops']:
        if not isinstance(op, dict) or op.get('op') not in VALID_OPS:
            return False, 'bad op: %r' % (op,)
    return True, ''
