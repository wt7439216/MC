# -*- coding: utf-8 -*-
"""摄像机状态守卫（P0.5b）。

不变量：
  1. **快照失败 → 绝不修改摄像机**（不 depart，不 set），直接返回 False；
  2. depart 失败 → 视为"状态未知"，立即尝试按快照恢复，并返回 False；
  3. exit() 一定尝试全部恢复步骤，且如实返回 ok/failed。

用法：
    ok = guard.enter()
    if not ok: 不要做任何相机操作
    report = guard.exit()   # 必须检查 report['ok']
"""
from __future__ import division

from mod_log import logger


class CameraGuard(object):
    def __init__(self, adapter):
        self.adapter = adapter
        self.snap = None
        self.active = False
        self.enter_failed = None
        self.last_report = None

    def enter(self):
        if self.active:
            return True
        self.enter_failed = None
        try:
            snap = self.adapter.snapshot()
        except Exception as exc:
            logger.error('[WX] camera snapshot exception: %r' % (exc,))
            snap = {'ok': False, 'fov': None, 'offset': None,
                    'perspective': None}
        self.snap = snap

        if not snap.get('ok'):
            # 关键：快照不可用时不 depart，保证"失败不改状态"
            self.enter_failed = 'snapshot'
            logger.error('[WX] camera snapshot failed; camera left untouched')
            return False

        try:
            departed = self.adapter.depart()
        except Exception as exc:
            logger.error('[WX] camera depart exception: %r' % (exc,))
            departed = False
        if not departed:
            self.enter_failed = 'depart'
            logger.error('[WX] camera depart failed; restoring snapshot')
            try:
                self.adapter.restore(snap)
            except Exception as exc:
                logger.error('[WX] camera rollback exception: %r' % (exc,))
            return False

        self.active = True
        return True

    def exit(self):
        if not self.active:
            if self.enter_failed:
                report = {'ok': False, 'attempted': [],
                          'failed': [self.enter_failed]}
                self.enter_failed = None
                self.snap = None
                self.last_report = report
                return report
            return {'ok': True, 'attempted': [], 'failed': []}

        report = {'ok': False, 'attempted': [], 'failed': ['restore-not-run']}
        snapshot_ok = bool((self.snap or {}).get('ok'))
        try:
            report = self.adapter.restore(self.snap)
            if not snapshot_ok:
                report = {'ok': False,
                          'attempted': report.get('attempted', []),
                          'failed': list(report.get('failed') or []) + ['snapshot']}
        except Exception as exc:
            logger.error('[WX] camera restore exception: %r' % (exc,))
            for name in ('UnDepartCamera', 'ResetCameraPos', 'UnLockCamera'):
                try:
                    self.adapter._call(self.adapter._components()[0], name)
                except Exception:
                    pass
        finally:
            self.snap = None
            self.active = False
            self.last_report = report
        return report

    def soft_exit(self):
        if not self.active:
            return {'ok': True, 'attempted': [], 'failed': []}
        try:
            return self.adapter.restore(self.snap)
        finally:
            self.active = False
