import os
import ctypes

'''Prevent OS sleep/hibernate in windows; code from:
https://github.com/h3llrais3r/Deluge-PreventSuspendPlus/blob/master/preventsuspendplus/core.py
API documentation:
https://msdn.microsoft.com/en-us/library/windows/desktop/aa373208(v=vs.85).aspx'''


# class WindowsInhibitor:
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


def prevent_sleep():
    if os.name != 'nt':
        return
    print("Preventing Windows from going to sleep")
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS |
        ES_DISPLAY_REQUIRED)


def authorize_sleep():
    if os.name != 'nt':
        return
    print("Allowing Windows to go to sleep")
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS)

# # in Windows, prevent the OS from sleeping while we run
# import os
# if os.name == 'nt':
#     osSleep = WindowsInhibitor()
# osSleep.inhibit()
# osSleep.uninhibit()
