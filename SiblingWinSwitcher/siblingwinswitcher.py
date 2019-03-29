# Keypirinha launcher (keypirinha.com)

import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpnet
import time
import ctypes
import threading
from .lib.alttab import AltTab
from .lib.processutil import ProcessUtil

USER32 = ctypes.windll.USER32
KERNEL32 = ctypes.windll.KERNEL32

# WH_KEYBOARD_LL = 13
# WM_KEYDOWN = 0x0100
# WM_KEYUP = 0x0101
# WM_SYSKEYDOWN = 0x0104
# WM_SYSKEYUP = 0x0105
WM_HOTKEY = 0x0312

VK_LEFTALT = 164
VK_RIGHTALT = 165
VK_ALT = 18
VK_OEM_3 = 192

MOD_ALT = 1
MOD_CONTROL = 2
MOD_SHIFT = 4
MOD_WIN = 8

IS_REPEAT = False

def get_sibling_windows():
    sibling_wins = []    
    for i in range(5):
        foreground_win = USER32.GetForegroundWindow()
        if foreground_win:
            break
        else:
            time.sleep(0.1)

    if not foreground_win:
        return sibling_wins

    wins = AltTab.list_alttab_windows()
    processes = ProcessUtil.get_all_processes()

    ul_process_id = ctypes.c_ulong()
    USER32.GetWindowThreadProcessId(foreground_win, ctypes.byref(ul_process_id))
    process_id = ul_process_id.value
    process_name = processes.get(process_id)

    # Foreground window is not must to be the first one in z-order
    sibling_wins.append(foreground_win)
    for win in wins:
        if win != foreground_win:
            USER32.GetWindowThreadProcessId(win, ctypes.byref(ul_process_id))
            if process_id == ul_process_id.value:
                sibling_wins.append(win)
            else:
                if process_name and processes.get(ul_process_id.value) == process_name:
                    sibling_wins.append(win)

    return sibling_wins

def switch_window(sibling_wins):
    try:
        sibling_wins.append(sibling_wins.pop(0))
    except ValueError:
        return

    AltTab.switch_to_window(sibling_wins[0])

    return

def hotkey_handler(p):
    global IS_REPEAT

    def hotkey_triggered():
        global IS_REPEAT

        while True:
            if IS_REPEAT:
                if USER32.GetAsyncKeyState(VK_ALT) & 0xff00 == 0:
                    # Alt key is up
                    IS_REPEAT = False

            time.sleep(0.01)
        return

    hotkey_id = 98
    if not USER32.RegisterHotKey(None, hotkey_id, MOD_ALT, VK_OEM_3):
        p.info("Register hotKey failed ")
        return

    try:
        thread = None
        sibling_wins = []
        msg = ctypes.wintypes.MSG()
        while True:
            if USER32.GetMessageA(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == WM_HOTKEY and msg.wParam == hotkey_id:
                    if not thread:
                        thread = threading.Thread(target=hotkey_triggered)
                        thread.setDaemon(True)
                        thread.start()

                    if not IS_REPEAT:
                        sibling_wins = get_sibling_windows()
                        if sibling_wins:
                            IS_REPEAT = True

                    switch_window(sibling_wins)

                USER32.TranslateMessage(ctypes.byref(msg))  
                USER32.DispatchMessageA(ctypes.byref(msg))
    finally:
        USER32.UnregisterHotKey(None, 98)


class SiblingWinSwitcher(kp.Plugin):
    """
    One-line description of your plugin.

    This block is a longer and more detailed description of your plugin that may
    span on several lines, albeit not being required by the application.

    You may have several plugins defined in this module. It can be useful to
    logically separate the features of your package. All your plugin classes
    will be instantiated by Keypirinha as long as they are derived directly or
    indirectly from :py:class:`keypirinha.Plugin` (aliased ``kp.Plugin`` here).

    In case you want to have a base class for your plugins, you must prefix its
    name with an underscore (``_``) to indicate Keypirinha it is not meant to be
    instantiated directly.

    In rare cases, you may need an even more powerful way of telling Keypirinha
    what classes to instantiate: the ``__keypirinha_plugins__`` global variable
    may be declared in this module. It can be either an iterable of class
    objects derived from :py:class:`keypirinha.Plugin`; or, even more dynamic,
    it can be a callable that returns an iterable of class objects. Check out
    the ``StressTest`` example from the SDK for an example.

    Up to 100 plugins are supported per module.

    More detailed documentation at: http://keypirinha.com/api/plugin.html
    """
    def __init__(self):
        super().__init__()
        # self._debug = True

    def on_start(self):
        t = threading.Thread(target=hotkey_handler, args=(self,))
        t.setDaemon(True)
        t.start()

    def on_catalog(self):
        pass

    def on_suggest(self, user_input, items_chain):
        pass

    def on_execute(self, item, action):
        pass

    def on_activated(self):
        pass

    def on_deactivated(self):
        pass

    def on_events(self, flags):
        pass
