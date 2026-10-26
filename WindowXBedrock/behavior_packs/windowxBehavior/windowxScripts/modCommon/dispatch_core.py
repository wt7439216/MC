# -*- coding: utf-8 -*-
"""指令分发核心（服务端逻辑，纯 Python，可在本地单测）。

输入：store（注册表）、family（wx/wxs/wxa）、action、args、actor
输出：{'ok': bool, 'msg': str, 'ops': [...], 'data': {...}}
ops 由 syncBroker 直接下发给客户端；data 供记分板/回显使用。
"""
from __future__ import division

from . import animator_core
from . import layout
from . import modConfig
from . import permissions
from . import window_def

LAYERS = ('normal', 'top', 'solid', 'clickthrough')
CONTENT_KINDS = ('texture', 'frames', 'text')
DISPLAY_MODES = ('fit', 'stretch', 'original', 'tile')


def _ok(msg='', ops=None, data=None):
    return {'ok': True, 'msg': msg, 'ops': ops or [], 'data': data or {}}


def _err(msg, data=None):
    return {'ok': False, 'msg': msg, 'ops': [], 'data': data or {}}


def _f(args, key, default=0.0):
    try:
        return float(args.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def _s(args, key, default=''):
    v = args.get(key, default)
    return default if v is None else str(v)


def _window_op(family, action, args, actor, store):
    """窗口读写类动作的公共入口。"""
    owner = permissions.scope_owner(family, actor)
    wid = _s(args, 'id').strip()
    if not wid:
        return _err('缺少窗口 id')
    win = store.get(owner, wid)
    if win is None:
        return _err('窗口不存在: %s' % wid)
    if not permissions.can_touch(family, win['owner'], actor):
        return _err('无权操作该窗口')
    return win


# ---------------------------------------------------------------------------
# wx* / wxs* 共用动作
# ---------------------------------------------------------------------------
def _act_create(store, args, actor, family, scene=False):
    owner = permissions.scope_owner(family, actor)
    wid = _s(args, 'id').strip()
    if not window_def.valid_id(wid):
        return _err('非法窗口 id（小写字母/数字/下划线，1~16 位）: %s' % wid)
    if store.get(owner, wid) is not None:
        return _err('窗口 id 已存在: %s' % wid)
    w = max(24.0, _f(args, 'w', 120.0))
    h = max(24.0, _f(args, 'h', 80.0))
    cx = layout.resolve_coord(_s(args, 'x', 'p50'), modConfig.VIEW_W * 0.5,
                              modConfig.VIEW_W)
    cy = layout.resolve_coord(_s(args, 'y', 'p50'), modConfig.VIEW_H * 0.5,
                              modConfig.VIEW_H)
    cx, cy, w, h = layout.clamp_window(cx, cy, w, h, modConfig.VIEW_W, modConfig.VIEW_H)
    win = window_def.new_window(wid, owner, w, h, cx, cy, _s(args, 'title', 'Window'))
    ok, msg = store.add(win)
    if not ok:
        return _err(msg)
    return _ok('已创建窗口 %s' % wid,
               [{'op': 'create', 'win': window_def.snapshot(win)}],
               {'id': wid, 'owner': owner, 'scene': scene})


def _act_remove(store, args, actor, family):
    owner = permissions.scope_owner(family, actor)
    wid = _s(args, 'id', 'all').strip()
    ops = []
    if wid == 'all':
        ids = store.remove_all(owner)
        for i in ids:
            ops.append({'op': 'remove', 'id': i})
        return _ok('已删除 %d 个窗口' % len(ids), ops, {'count': len(ids)})
    win = store.get(owner, wid)
    if win is None:
        return _err('窗口不存在: %s' % wid)
    if not permissions.can_touch(family, win['owner'], actor):
        return _err('无权操作该窗口')
    store.remove(owner, wid)
    return _ok('已删除窗口 %s' % wid, [{'op': 'remove', 'id': wid}], {'id': wid})


def _act_move(store, args, actor, family):
    win = _window_op(family, 'move', args, actor, store)
    if isinstance(win, dict) and 'ok' in win:
        return win
    tx = layout.resolve_coord(_s(args, 'x'), win['cx'], modConfig.VIEW_W)
    ty = layout.resolve_coord(_s(args, 'y'), win['cy'], modConfig.VIEW_H)
    tx, ty, w, h = layout.clamp_window(tx, ty, win['w'], win['h'],
                                       modConfig.VIEW_W, modConfig.VIEW_H)
    ease_name = _s(args, 'ease', modConfig.DEFAULT_EASE)
    speed = _f(args, 'speed', 1.0)
    task = animator_core.make_move_task(win, tx, ty, speed, ease_name)
    win['cx'], win['cy'] = tx, ty
    window_def.bump(win)
    return _ok('移动 %s -> (%.0f, %.0f)' % (win['id'], tx, ty),
               [{'op': 'anim', 'task': task}],
               {'id': win['id'], 'x': tx, 'y': ty, 'dur': task['dur']})


def _act_size(store, args, actor, family):
    win = _window_op(family, 'size', args, actor, store)
    if isinstance(win, dict) and 'ok' in win:
        return win
    axis = _s(args, 'axis', 'w').lower()
    if axis not in ('w', 'h'):
        return _err('axis 只能是 w 或 h')
    base = win['w'] if axis == 'w' else win['h']
    total = modConfig.VIEW_W if axis == 'w' else modConfig.VIEW_H
    val = layout.resolve_coord(_s(args, 'value'), base, total, 24.0, total)
    new_w = val if axis == 'w' else win['w']
    new_h = val if axis == 'h' else win['h']
    cx, cy, new_w, new_h = layout.clamp_window(win['cx'], win['cy'], new_w, new_h,
                                               modConfig.VIEW_W, modConfig.VIEW_H)
    task = animator_core.make_zoom_task(win, new_w, new_h, cx, cy,
                                        _f(args, 'speed', 1.0),
                                        _s(args, 'ease', modConfig.DEFAULT_EASE))
    win['w'], win['h'], win['cx'], win['cy'] = new_w, new_h, cx, cy
    window_def.bump(win)
    return _ok('调整尺寸 %s -> %dx%d' % (win['id'], new_w, new_h),
               [{'op': 'anim', 'task': task}],
               {'id': win['id'], 'w': new_w, 'h': new_h, 'dur': task['dur']})


def _act_zoom(store, args, actor, family):
    win = _window_op(family, 'zoom', args, actor, store)
    if isinstance(win, dict) and 'ok' in win:
        return win
    new_w = max(24.0, _f(args, 'w', win['w']))
    new_h = max(24.0, _f(args, 'h', win['h']))
    anchor = _s(args, 'anchor', 'center')
    cx, cy = layout.zoom_keep_anchor(win['cx'], win['cy'], win['w'], win['h'],
                                     new_w, new_h, anchor)
    cx, cy, new_w, new_h = layout.clamp_window(cx, cy, new_w, new_h,
                                               modConfig.VIEW_W, modConfig.VIEW_H)
    task = animator_core.make_zoom_task(win, new_w, new_h, cx, cy,
                                        _f(args, 'speed', 1.0),
                                        _s(args, 'ease', modConfig.DEFAULT_EASE))
    win['w'], win['h'], win['cx'], win['cy'] = new_w, new_h, cx, cy
    window_def.bump(win)
    return _ok('缩放 %s -> %dx%d (anchor=%s)' % (win['id'], new_w, new_h, anchor),
               [{'op': 'anim', 'task': task}],
               {'id': win['id'], 'w': new_w, 'h': new_h, 'anchor': anchor})


def _act_fx(store, args, actor, family, kind):
    win = _window_op(family, kind, args, actor, store)
    if isinstance(win, dict) and 'ok' in win:
        return win
    if kind == 'shake':
        dur = _f(args, 'duration', 0.6)
        params = {'intensity': _f(args, 'intensity', 8.0)}
    elif kind == 'encircle':
        dur = max(0.3, 2.0 / max(0.05, _f(args, 'speed', 1.0)))
        params = {'rx': _f(args, 'rx', 60.0), 'ry': _f(args, 'ry', 40.0),
                  'deg': _f(args, 'deg', 360.0), 'start': 0.0}
    elif kind == 'wobble':
        cycles = int(_f(args, 'cycles', 3))
        dur = max(0.3, float(cycles) / max(0.05, _f(args, 'speed', 1.0)))
        params = {'ix': _f(args, 'ix', 6.0), 'iy': _f(args, 'iy', 6.0),
                  'speed': _f(args, 'speed', 1.0), 'cycles': cycles}
    else:  # breath
        cycles = int(_f(args, 'cycles', 3))
        dur = max(0.3, float(cycles) / max(0.05, _f(args, 'speed', 0.5)))
        params = {'intensity': _f(args, 'intensity', 0.06),
                  'speed': _f(args, 'speed', 0.5), 'cycles': cycles}
    task = animator_core.make_fx_task(win, kind, dur, params)
    return _ok('%s %s (%.2fs)' % (kind, win['id'], dur),
               [{'op': 'fx', 'task': task}], {'id': win['id'], 'dur': dur})


def _act_physics(store, args, actor, family):
    win = _window_op(family, 'physics', args, actor, store)
    if isinstance(win, dict) and 'ok' in win:
        return win
    sx = layout.resolve_coord(_s(args, 'sx', 'p50'), win['cx'], modConfig.VIEW_W)
    sy = layout.resolve_coord(_s(args, 'sy', 'p20'), win['cy'], modConfig.VIEW_H)
    params = {
        'gravity': _f(args, 'gravity', 1200.0),
        'friction': _f(args, 'friction', 0.12),
        'elasticity': _f(args, 'elasticity', 0.45),
        'start': [sx, sy],
        'force': [_f(args, 'fx', 0.0), _f(args, 'fy', 0.0), _f(args, 'fs', 0.0)],
    }
    win['cx'], win['cy'] = sx, sy
    window_def.bump(win)
    return _ok('物理已启动 %s' % win['id'], [{'op': 'physics', 'id': win['id'],
                                            'params': params}], {'id': win['id']})


def _act_follow(store, args, actor, family):
    win = _window_op(family, 'follow', args, actor, store)
    if isinstance(win, dict) and 'ok' in win:
        return win
    target = _s(args, 'target').strip()
    if not target:
        return _err('缺少 target')
    params = {'target': target, 'distance': _f(args, 'distance', 4.0),
              'scale': _f(args, 'scale', 0.0)}
    return _ok('跟随已设置 %s -> %s' % (win['id'], target),
               [{'op': 'follow', 'id': win['id'], 'params': params}],
               {'id': win['id']})


def _act_content(store, args, actor, family):
    win = _window_op(family, 'content', args, actor, store)
    if isinstance(win, dict) and 'ok' in win:
        return win
    kind = _s(args, 'kind', 'text').lower()
    if kind not in CONTENT_KINDS:
        return _err('kind 只能是 %s' % ','.join(CONTENT_KINDS))
    mode = _s(args, 'mode', 'fit').lower()
    if mode not in DISPLAY_MODES:
        return _err('mode 只能是 %s' % ','.join(DISPLAY_MODES))
    win['content'] = {'kind': kind, 'path': _s(args, 'path'), 'mode': mode}
    window_def.bump(win)
    return _ok('内容已更新 %s' % win['id'],
               [{'op': 'set', 'id': win['id'], 'fields': {'content': win['content']}}],
               {'id': win['id'], 'content': win['content']})


def _act_layer(store, args, actor, family):
    win = _window_op(family, 'layer', args, actor, store)
    if isinstance(win, dict) and 'ok' in win:
        return win
    layer = _s(args, 'layer', 'normal').lower()
    if layer not in LAYERS:
        return _err('layer 只能是 %s' % ','.join(LAYERS))
    win['layer'] = layer
    window_def.bump(win)
    return _ok('层级 %s -> %s' % (win['id'], layer),
               [{'op': 'set', 'id': win['id'], 'fields': {'layer': layer}}],
               {'id': win['id'], 'layer': layer})


def _act_title(store, args, actor, family):
    win = _window_op(family, 'title', args, actor, store)
    if isinstance(win, dict) and 'ok' in win:
        return win
    action = _s(args, 'action', 'set').lower()
    text = '' if action == 'reset' else _s(args, 'text')[0:modConfig.MAX_TITLE_LEN]
    win['title'] = text
    window_def.bump(win)
    return _ok('标题已更新 %s' % win['id'],
               [{'op': 'set', 'id': win['id'], 'fields': {'title': text}}],
               {'id': win['id'], 'title': text})


def _act_show_hide(store, args, actor, family, visible):
    win = _window_op(family, 'show', args, actor, store)
    if isinstance(win, dict) and 'ok' in win:
        return win
    win['visible'] = bool(visible)
    window_def.bump(win)
    return _ok('%s %s' % ('显示' if visible else '隐藏', win['id']),
               [{'op': 'set', 'id': win['id'], 'fields': {'visible': bool(visible)}}],
               {'id': win['id'], 'visible': bool(visible)})


def _act_stop(store, args, actor, family):
    owner = permissions.scope_owner(family, actor)
    wid = _s(args, 'id', 'all').strip()
    if wid == 'all':
        return _ok('停止全部动画', [{'op': 'stop', 'id': 'all'}], {'count': store.count(owner)})
    win = store.get(owner, wid)
    if win is None:
        return _err('窗口不存在: %s' % wid)
    if not permissions.can_touch(family, win['owner'], actor):
        return _err('无权操作该窗口')
    return _ok('停止 %s 的动画' % wid, [{'op': 'stop', 'id': wid}], {'id': wid})


def _act_get(store, args, actor, family):
    win = _window_op(family, 'get', args, actor, store)
    if isinstance(win, dict) and 'ok' in win:
        return win
    prop = _s(args, 'prop', 'x').lower()
    if prop not in ('x', 'y', 'w', 'h', 'visible'):
        return _err('prop 只能是 x/y/w/h/visible')
    val = win[{'x': 'cx', 'y': 'cy'}.get(prop, prop)]
    return _ok('%s.%s = %s' % (win['id'], prop, val), [], {'id': win['id'],
                                                          'prop': prop, 'value': val})


def _act_score(store, args, actor, family):
    win = _window_op(family, 'score', args, actor, store)
    if isinstance(win, dict) and 'ok' in win:
        return win
    objective = _s(args, 'objective').strip()
    if not objective:
        return _err('缺少 objective')
    data = {'objective': objective, 'id': win['id'],
            'x': win['cx'], 'y': win['cy'], 'w': win['w'], 'h': win['h'],
            'visible': 1 if win['visible'] else 0}
    return _ok('已写入记分板 %s' % objective, [], data)


# ---------------------------------------------------------------------------
# 管理族
# ---------------------------------------------------------------------------
def _act_admin_stop(store, args, actor):
    who = _s(args, 'player', 'all').strip()
    owners = store.owners() if who == 'all' else [who]
    ops = [{'op': 'stop', 'id': 'all', 'owner': o} for o in owners if store.count(o)]
    return _ok('已停止 %d 个命名空间的动画' % len(ops), ops, {'count': len(ops)})


def _act_admin_list(store, args, actor):
    who = _s(args, 'player', 'all').strip()
    owners = store.owners() if who == 'all' else [who]
    data = {'owners': [{'owner': o, 'count': store.count(o),
                        'ids': [w['id'] for w in store.list(o)]} for o in owners]}
    total = sum(item['count'] for item in data['owners'])
    return _ok('共 %d 个窗口' % total, [], data)


def _act_admin_kill(store, args, actor):
    who = _s(args, 'player').strip()
    if not who:
        return _err('缺少 player')
    ids = store.remove_all(who)
    ops = [{'op': 'remove', 'id': i, 'owner': who} for i in ids]
    return _ok('已清空 %s 的 %d 个窗口' % (who, len(ids)), ops, {'count': len(ids)})


def _act_admin_quota(store, args, actor):
    who = _s(args, 'player').strip()
    limit = int(_f(args, 'limit', 8))
    if not who:
        return _err('缺少 player')
    if limit < 1 or limit > 64:
        return _err('limit 需在 1~64')
    store.set_quota(who, limit)
    return _ok('%s 的配额已设为 %d' % (who, limit), [], {'owner': who, 'limit': limit})


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def handle(store, family, action, args, actor):
    args = args or {}
    if not permissions.can_run(family, actor):
        return _err('当前身份无权使用该指令（%s）' % family)

    act = str(action or '').lower()
    if family == modConfig.FAMILY_PLAYER:
        if act == 'create':
            return _act_create(store, args, actor, family)
        if act == 'remove':
            return _act_remove(store, args, actor, family)
        if act == 'move':
            return _act_move(store, args, actor, family)
        if act == 'size':
            return _act_size(store, args, actor, family)
        if act == 'zoom':
            return _act_zoom(store, args, actor, family)
        if act in ('shake', 'encircle', 'wobble', 'breath'):
            return _act_fx(store, args, actor, family, act)
        if act == 'physics':
            return _act_physics(store, args, actor, family)
        if act == 'follow':
            return _act_follow(store, args, actor, family)
        if act == 'content':
            return _act_content(store, args, actor, family)
        if act == 'layer':
            return _act_layer(store, args, actor, family)
        if act == 'title':
            return _act_title(store, args, actor, family)
        if act == 'stop':
            return _act_stop(store, args, actor, family)
        if act == 'get':
            return _act_get(store, args, actor, family)
        if act == 'score':
            return _act_score(store, args, actor, family)

    elif family == modConfig.FAMILY_SHOW:
        if act == 'create':
            return _act_create(store, args, actor, family, scene=True)
        if act == 'move':
            return _act_move(store, args, actor, family)
        if act == 'size':
            return _act_size(store, args, actor, family)
        if act == 'show':
            return _act_show_hide(store, args, actor, family, True)
        if act == 'hide':
            return _act_show_hide(store, args, actor, family, False)
        if act == 'stop':
            return _act_stop(store, args, actor, family)
        if act == 'anim':
            kind = _s(args, 'kind', 'shake').lower()
            if kind not in ('shake', 'wobble', 'breath', 'encircle'):
                return _err('kind 只能是 shake/wobble/breath/encircle')
            # 通用参数 a/b/c/d -> 具体特效参数
            mapped = {
                'shake': {'intensity': _f(args, 'a', 8.0), 'duration': _f(args, 'c', 0.6)},
                'wobble': {'ix': _f(args, 'a', 6.0), 'iy': _f(args, 'a', 6.0),
                           'speed': _f(args, 'b', 1.0), 'cycles': int(_f(args, 'd', 3))},
                'breath': {'intensity': _f(args, 'a', 0.06), 'speed': _f(args, 'b', 0.5),
                           'cycles': int(_f(args, 'd', 3))},
                'encircle': {'rx': _f(args, 'a', 60.0), 'ry': _f(args, 'c', 40.0),
                             'speed': _f(args, 'b', 1.0), 'deg': 360.0, 'duration': None},
            }[kind]
            if kind == 'encircle':
                dur = max(0.3, 2.0 / max(0.05, mapped['speed']))
                mapped.pop('duration', None)
            elif kind == 'shake':
                dur = mapped.get('duration', 0.6)
            else:
                dur = max(0.3, float(mapped['cycles']) / max(0.05, mapped['speed']))
            win = _window_op(family, 'anim', {'id': _s(args, 'id')}, actor, store)
            if isinstance(win, dict) and 'ok' in win:
                return win
            task = animator_core.make_fx_task(win, kind, dur, mapped)
            return _ok('%s %s' % (kind, win['id']), [{'op': 'fx', 'task': task}],
                       {'id': win['id'], 'dur': dur})

    elif family == modConfig.FAMILY_ADMIN:
        if act == 'stop':
            return _act_admin_stop(store, args, actor)
        if act == 'list':
            return _act_admin_list(store, args, actor)
        if act == 'kill':
            return _act_admin_kill(store, args, actor)
        if act == 'quota':
            return _act_admin_quota(store, args, actor)

    return _err('未知动作: %s' % act)
