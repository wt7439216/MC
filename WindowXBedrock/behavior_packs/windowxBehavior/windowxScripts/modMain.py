# -*- coding: utf-8 -*-
"""WindowX Bedrock 入口（P0 骨架）。

注意：脚本路径必须与 pack 内目录一致；如 MCStudio 生成的项目使用
其他根目录名（例如 behavior_pack_xxx/xxxScripts），请同步修改
modConfig.SERVER_SYSTEM_CLS / CLIENT_SYSTEM_CLS 与 import 前缀。
"""
from __future__ import absolute_import

import mod.client.extraClientApi as clientApi
import mod.server.extraServerApi as serverApi
from mod.common.mod import Mod

from windowxScripts.modCommon import modConfig


@Mod.Binding(name='windowx', version='0.1.0')
class WindowXBedrock(object):
    def __init__(self):
        pass

    @Mod.InitServer()
    def wx_init_server(self):
        serverApi.RegisterSystem(modConfig.MOD_NAME, modConfig.SERVER_SYSTEM,
                                 modConfig.SERVER_SYSTEM_CLS)

    @Mod.DestroyServer()
    def wx_destroy_server(self):
        pass

    @Mod.InitClient()
    def wx_init_client(self):
        clientApi.RegisterSystem(modConfig.MOD_NAME, modConfig.CLIENT_SYSTEM,
                                 modConfig.CLIENT_SYSTEM_CLS)

    @Mod.DestroyClient()
    def wx_destroy_client(self):
        pass
