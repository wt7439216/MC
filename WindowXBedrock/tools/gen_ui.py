# -*- coding: utf-8 -*-
"""生成 windowx_hud.json（N 个伪窗口槽位）+ _ui_defs.json。

为什么用生成器：L1/L2/L3/L4 性能验证需要不同控件规模（3/10/20/30 窗口），
而 UI 是静态 JSON，必须在打包前按目标规模生成。

控件路径与 modClient/hudScreen.py 约定一致：
    /win<i>            根 panel（anchor=center，offset/size 用百分比）
    /win<i>/bg         九宫格背景 image
    /win<i>/title      标题 label
    /win<i>/content    内容 image
    /win<i>/bar_drag   标题栏拖拽 button

注意：结构参照官方样例（data/apollo/.../neteaseNpcRes/ui/npcSure.json）。
若 MCStudio 的 UI 校验报字段错误，按报错微调；不要改动控件命名，
否则 hudBackend 的路径会失配。
"""
from __future__ import print_function

import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
UI_DIR = os.path.join(PROJECT, 'resource_packs', 'windowxResource', 'ui')

sys.path.insert(0, os.path.join(PROJECT, 'behavior_packs', 'windowxBehavior'))
from windowxScripts.modCommon import modConfig  # noqa: E402

NS = 'windowx_hud'


def pct(v):
    return '%.4f%%' % v


def build(windows):
    defs = {
        'namespace': NS,
        'main@common.base_screen': {
            'type': 'screen',
            'absorbs_input': False,
            'always_accepts_input': False,
            'is_showing_menu': False,
            'render_game_behind': True,
            'render_only_when_topmost': False,
            'should_steal_mouse': False,
            'controls': [],
        },
        # ---- 共享模板 ----
        'bg': {
            'type': 'image',
            'texture': 'textures/ui/windowx/bg',
            'is_new_nine_slice': True,
            'nine_slice_left': 4, 'nine_slice_right': 4,
            'nine_slice_top': 4, 'nine_slice_buttom': 4,
            'size': ['100%', '100%'],
            'layer': 0,
            'anchor_from': 'center',
            'anchor_to': 'center',
        },
        'shadow': {
            'type': 'image',
            'texture': 'textures/ui/windowx/shadow',
            'is_new_nine_slice': True,
            'nine_slice_left': 4, 'nine_slice_right': 4,
            'nine_slice_top': 4, 'nine_slice_buttom': 4,
            'size': ['104%', '108%'],
            'offset': [0, '2%'],
            'layer': -1,
            'anchor_from': 'center',
            'anchor_to': 'center',
        },
        'title': {
            'type': 'label',
            'text': 'Window',
            'color': [1.0, 1.0, 1.0],
            'font_size': 'normal',
            'font_type': 'smooth',
            'text_alignment': 'left',
            'size': ['88%', '12%'],
            'offset': ['-4%', '-40%'],
            'layer': 4,
            'anchor_from': 'center',
            'anchor_to': 'center',
        },
        'content': {
            'type': 'image',
            'texture': 'textures/ui/windowx/content',
            'size': ['94%', '76%'],
            'offset': [0, '4%'],
            'layer': 1,
            'anchor_from': 'center',
            'anchor_to': 'center',
        },
        'btn_img': {
            'type': 'image',
            'texture': 'textures/ui/windowx/titlebar',
            'is_new_nine_slice': True,
            'nine_slice_left': 4, 'nine_slice_right': 4,
            'nine_slice_top': 4, 'nine_slice_buttom': 4,
            'size': ['100%', '100%'],
        },
        'bar_drag': {
            'type': 'button',
            'size': ['100%', '16%'],
            'offset': [0, '-41%'],
            'layer': 3,
            'anchor_from': 'center',
            'anchor_to': 'center',
            'default_control': 'default',
            'hover_control': 'hover',
            'pressed_control': 'pressed',
            'is_handle_button_move_event': True,
            'button_mappings': [],
            'controls': [
                {'default@windowx_hud.btn_img': {}},
                {'hover@windowx_hud.btn_img': {}},
                {'pressed@windowx_hud.btn_img': {}},
            ],
        },
    }

    for i in range(windows):
        defs['win%d' % i] = {
            'type': 'panel',
            'size': [pct(6.25), pct(7.41)],   # 120x80 @1920x1080
            'offset': [pct(0.0), pct(-30.0)],
            'layer': 10,
            'visible': False,
            'anchor_from': 'center',
            'anchor_to': 'center',
            'controls': [
                {'shadow@windowx_hud.shadow': {}},
                {'bg@windowx_hud.bg': {}},
                {'content@windowx_hud.content': {}},
                {'title@windowx_hud.title': {}},
                {'bar_drag@windowx_hud.bar_drag': {}},
            ],
        }
        defs['main@common.base_screen']['controls'].append(
            {'win%d@windowx_hud.win%d' % (i, i): {}})

    return defs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--windows', type=int, default=None,
                    help='窗口槽位数（默认取 modConfig.HUD_SLOTS；L1=3 L2=10 L3=20 L4=30）')
    ns = ap.parse_args()

    target = int(ns.windows if ns.windows is not None else modConfig.HUD_SLOTS)
    if target < 1 or target > int(modConfig.HUD_SLOT_PROBE_LIMIT):
        print('[FAIL] windows 必须在 1..%d' % modConfig.HUD_SLOT_PROBE_LIMIT)
        return 2
    if target != int(modConfig.HUD_SLOTS):
        print('[WARN] 生成 %d 个槽位，与 modConfig.HUD_SLOTS=%d 不同；'
              '运行时按 UI 实际控件探测（hudScreen._detect_slots），仅用于性能分级测试。'
              % (target, modConfig.HUD_SLOTS))

    if not os.path.isdir(UI_DIR):
        os.makedirs(UI_DIR)

    defs = build(target)
    path = os.path.join(UI_DIR, 'windowx_hud.json')
    with io.open(path, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(defs, ensure_ascii=False, indent=2))
        fh.write(u'\n')

    ui_defs = {'ui_defs': ['ui/windowx_hud.json']}
    with io.open(os.path.join(UI_DIR, '_ui_defs.json'), 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(ui_defs, ensure_ascii=False, indent=2))
        fh.write(u'\n')

    print('[OK] windows=%d -> %s' % (target, path))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
