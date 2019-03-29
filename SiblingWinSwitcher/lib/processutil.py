import ctypes
import ctypes.wintypes

KERNEL32 = ctypes.windll.kernel32

_TH32CS_SNAPPROCESS = 0x00000002
class _PROCESSENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", ctypes.wintypes.DWORD),
                ("cntUsage", ctypes.wintypes.DWORD),
                ("th32ProcessID", ctypes.wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_size_t),
                ("th32ModuleID", ctypes.wintypes.DWORD),
                ("cntThreads", ctypes.wintypes.DWORD),
                ("th32ParentProcessID", ctypes.wintypes.DWORD),
                ("pcPriClassBase", ctypes.wintypes.LONG),
                ("dwFlags", ctypes.wintypes.DWORD),
                ("szExeFile", ctypes.c_char * 260)]


class ProcessUtil:

    @staticmethod
    def get_all_processes():
        processes = {}
        hProcessSnap = KERNEL32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
        try:
            pe32 = _PROCESSENTRY32()
            pe32.dwSize = ctypes.sizeof(_PROCESSENTRY32)
            if not KERNEL32.Process32First(hProcessSnap, ctypes.byref(pe32)):
                return processes

            while True:
                processes[pe32.th32ProcessID] = pe32.szExeFile.decode("utf-8")
                if not KERNEL32.Process32Next(hProcessSnap, ctypes.byref(pe32)):
                    break
        finally:
            KERNEL32.CloseHandle(hProcessSnap)
        return processes
        
if __name__ == '__main__':
    print(ProcessUtil.get_all_processes()[4])

