# -*- coding: utf-8 -*-
"""窗口注册表（服务端权威内存态）。纯 Python，可单测。"""
from __future__ import division

from . import modConfig


class Store(object):
    def __init__(self, player_quota=None, scene_quota=None):
        self.player_quota = player_quota or modConfig.MAX_WINDOWS_PER_PLAYER
        self.scene_quota = scene_quota or modConfig.MAX_WINDOWS_PER_SCENE
        self.by_owner = {}
        self.quota_overrides = {}

    # ---- 查询 ----
    def quota_of(self, owner):
        if owner in self.quota_overrides:
            return self.quota_overrides[owner]
        return self.scene_quota if owner == modConfig.SCENE_OWNER else self.player_quota

    def set_quota(self, owner, limit):
        self.quota_overrides[owner] = int(limit)

    def count(self, owner):
        return len(self.by_owner.get(owner) or {})

    def total(self):
        n = 0
        for owner in self.by_owner:
            n += len(self.by_owner[owner])
        return n

    def get(self, owner, wid):
        return (self.by_owner.get(owner) or {}).get(wid)

    def list(self, owner):
        buckets = self.by_owner.get(owner) or {}
        return [buckets[k] for k in sorted(buckets.keys())]

    def owners(self):
        return sorted(self.by_owner.keys())

    # ---- 变更 ----
    def add(self, win):
        owner = win['owner']
        buckets = self.by_owner.setdefault(owner, {})
        if win['id'] in buckets:
            return False, '窗口 id 已存在: %s' % win['id']
        if len(buckets) >= self.quota_of(owner):
            return False, '窗口数量已达配额 %d' % self.quota_of(owner)
        buckets[win['id']] = win
        return True, ''

    def remove(self, owner, wid):
        buckets = self.by_owner.get(owner) or {}
        if wid not in buckets:
            return False, '窗口不存在: %s' % wid
        del buckets[wid]
        if not buckets:
            self.by_owner.pop(owner, None)
        return True, ''

    def remove_all(self, owner):
        removed = sorted((self.by_owner.get(owner) or {}).keys())
        self.by_owner.pop(owner, None)
        return removed
