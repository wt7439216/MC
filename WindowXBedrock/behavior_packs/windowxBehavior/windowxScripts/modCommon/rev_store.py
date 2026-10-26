# -*- coding: utf-8 -*-
"""按 owner 维护的版本号，用于增量补丁的连续性校验。纯逻辑。"""


class RevStore(object):
    def __init__(self):
        self.revs = {}

    def current(self, owner):
        return int(self.revs.get(owner, 0))

    def next(self, owner):
        rev = self.current(owner) + 1
        self.revs[owner] = rev
        return rev

    def set(self, owner, rev):
        self.revs[owner] = int(rev)

    def reset(self, owner):
        self.revs.pop(owner, None)

    def needs_full(self, owner, client_rev):
        """客户端版本落后（或超前）太多时，服务端应重发全量。"""
        return int(client_rev) != self.current(owner)
