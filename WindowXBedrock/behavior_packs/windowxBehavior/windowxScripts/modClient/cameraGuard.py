# -*- coding: utf-8 -*-
"""摄像机状态守卫（P0.5：异常路径也必须尝试复原，且如实报告失败）。

用法：
    guard.enter()   -> bool（快照是否成功；失败也仍会 depart）
    guard.exit()    -> {'ok','failed','attempted'}（必须检查）
"""
from __future__ import division

from mod_log import logger


class CameraGuard(object):
    def __init__(self, adapter):
        self.adapter = adapter
        self.snap = None
        self.active = False
        self.last_report = None

    def enter(self):
        if self.active:
            return True
        try:
            self.snap = self.adapter.snapshot()
        except Exception as exc:
            logger.error('[WX] camera snapshot exception: %r' % (exc,))
            self.snap = {'ok': False, 'fov': None, 'offset': None,
                         'perspective': None}
        try:
            departed = self.adapter.depart()
        except Exception as exc:
            logger.error('[WX] camera depart exception: %r' % (exc,))
            departed = False
        self.active = True
        ok = bool(self.snap.get('ok')) and departed
        if not ok:
            logger.warn('[WX] camera enter degraded (snapshot=%r depart=%r)'
                        % (self.snap.get('ok'), departed))
        return ok

    def exit(self):
        """无论如何都走完整恢复流程；返回真实结果。"""
        if not self.active:
            return {'ok': True, 'attempted': [], 'failed': []}
        report = {'ok': False, 'attempted': [], 'failed': ['restore-not-run']}
        snapshot_ok = bool((self.snap or {}).get('ok'))
        try:
            report = self.adapter.restore(self.snap)
            if not snapshot_ok:
                # 快照失败意味着"原状态未知"，恢复不能宣称成功
                report = {'ok': False,
                          'attempted': report.get('attempted', []),
                          'failed': list(report.get('failed') or []) + ['snapshot']}
        except Exception as exc:
            logger.error('[WX] camera restore exception: %r' % (exc,))
            # 再兜底一次最小恢复
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
        """切换机位时只复原视角，不丢状态。"""
        if not self.active:
            return {'ok': True, 'attempted': [], 'failed': []}
        try:
            return self.adapter.restore(self.snap)
        finally:
            self.active = False
