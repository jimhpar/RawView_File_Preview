#include "RawViewThumbnailProvider.h"
#include <shlwapi.h>
#include <sstream>
#include <iomanip>

#pragma comment(lib, "shlwapi.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "shell32.lib")

extern HINSTANCE g_hInst;
extern long g_cDllRef;

// 64-bit FNV-1a Hash for ultra-fast, deterministic cache key generation
static uint64_t Fnv1aHash(const std::wstring& str) {
    uint64_t hash = 14695981039346656037ULL;
    for (wchar_t wc : str) {
        hash ^= (uint64_t)(wc & 0xFFFF);
        hash *= 1099511628211ULL;
    }
    return hash;
}

// Explicit GUID definitions to guarantee zero external symbol resolution issues in MinGW/Clang
static const IID s_IID_IUnknown = { 0x00000000, 0x0000, 0x0000, { 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46 } };
static const IID s_IID_IInitializeWithFile = { 0xb7d14566, 0x0509, 0x4cce, { 0xa7, 0x1f, 0x0a, 0x55, 0x42, 0x33, 0xbd, 0x9b } };
static const IID s_IID_IInitializeWithItem = { 0x7f73be3f, 0xfb79, 0x493c, { 0xa6, 0xc7, 0x7e, 0xe1, 0x4e, 0x24, 0x58, 0x41 } };
static const IID s_IID_IThumbnailProvider = { 0xe357fccd, 0xa995, 0x4576, { 0xb0, 0x1f, 0x23, 0x46, 0x30, 0x15, 0x4e, 0x96 } };

CRawViewThumbnailProvider::CRawViewThumbnailProvider() : m_cRef(1) {
    InterlockedIncrement(&g_cDllRef);
}

CRawViewThumbnailProvider::~CRawViewThumbnailProvider() {
    InterlockedDecrement(&g_cDllRef);
}

IFACEMETHODIMP CRawViewThumbnailProvider::QueryInterface(REFIID riid, void **ppv) {
    if (!ppv) return E_POINTER;
    *ppv = NULL;

    if (IsEqualIID(riid, s_IID_IUnknown)) {
        *ppv = static_cast<IThumbnailProvider*>(this);
    }
    else if (IsEqualIID(riid, s_IID_IInitializeWithFile)) {
        *ppv = static_cast<IInitializeWithFile*>(this);
    }
    else if (IsEqualIID(riid, s_IID_IInitializeWithItem)) {
        *ppv = static_cast<IInitializeWithItem*>(this);
    }
    else if (IsEqualIID(riid, s_IID_IThumbnailProvider)) {
        *ppv = static_cast<IThumbnailProvider*>(this);
    }
    else {
        return E_NOINTERFACE;
    }

    reinterpret_cast<IUnknown*>(*ppv)->AddRef();
    return S_OK;
}

IFACEMETHODIMP_(ULONG) CRawViewThumbnailProvider::AddRef() {
    return InterlockedIncrement(&m_cRef);
}

IFACEMETHODIMP_(ULONG) CRawViewThumbnailProvider::Release() {
    ULONG cRef = InterlockedDecrement(&m_cRef);
    if (cRef == 0) {
        delete this;
    }
    return cRef;
}

IFACEMETHODIMP CRawViewThumbnailProvider::Initialize(LPCWSTR pszFilePath, DWORD grfMode) {
    if (!pszFilePath) return E_INVALIDARG;
    m_filePath = pszFilePath;
    return S_OK;
}

IFACEMETHODIMP CRawViewThumbnailProvider::Initialize(IShellItem *psi, DWORD grfMode) {
    if (!psi) return E_POINTER;
    LPWSTR pszName = NULL;
    HRESULT hr = psi->GetDisplayName(SIGDN_FILESYSPATH, &pszName);
    if (SUCCEEDED(hr) && pszName) {
        m_filePath = pszName;
        CoTaskMemFree(pszName);
        return S_OK;
    }
    return hr;
}

std::wstring CRawViewThumbnailProvider::GetCacheFilePath(UINT cx) {
    if (m_filePath.empty()) return L"";

    // Obtain last write time to invalidate stale cache
    WIN32_FILE_ATTRIBUTE_DATA attrData;
    uint64_t mtime = 0;
    if (GetFileAttributesExW(m_filePath.c_str(), GetFileExInfoStandard, &attrData)) {
        mtime = ((uint64_t)attrData.ftLastWriteTime.dwHighDateTime << 32) | attrData.ftLastWriteTime.dwLowDateTime;
    }

    uint64_t pathHash = Fnv1aHash(m_filePath);
    
    // Cache folder: %LOCALAPPDATA%\RawView\cache\thumbs
    wchar_t localAppData[MAX_PATH];
    if (FAILED(SHGetFolderPathW(NULL, CSIDL_LOCAL_APPDATA, NULL, SHGFP_TYPE_CURRENT, localAppData))) {
        return L"";
    }

    wchar_t thumbDir[MAX_PATH + 64];
    swprintf_s(thumbDir, L"%s\\RawView\\cache\\thumbs", localAppData);
    CreateDirectoryW(thumbDir, NULL);

    wchar_t fileName[MAX_PATH + 128];
    swprintf_s(fileName, L"%s\\thumb_%llx_%llx_%u.bmp", thumbDir, (unsigned long long)pathHash, (unsigned long long)mtime, cx);
    return std::wstring(fileName);
}

bool CRawViewThumbnailProvider::FetchFromDiskCache(UINT cx, HBITMAP *phbmp, WTS_ALPHATYPE *pdwAlpha) {
    std::wstring cachePath = GetCacheFilePath(cx);
    if (cachePath.empty()) return false;

    DWORD attr = GetFileAttributesW(cachePath.c_str());
    if (attr == INVALID_FILE_ATTRIBUTES || (attr & FILE_ATTRIBUTE_DIRECTORY)) {
        return false;
    }

    HBITMAP hbmp = (HBITMAP)LoadImageW(
        NULL,
        cachePath.c_str(),
        IMAGE_BITMAP,
        0,
        0,
        LR_LOADFROMFILE | LR_CREATEDIBSECTION
    );

    if (hbmp) {
        *phbmp = hbmp;
        *pdwAlpha = WTSAT_ARGB;
        return true;
    }
    return false;
}

bool CRawViewThumbnailProvider::FetchFromPipe(UINT cx, HBITMAP *phbmp, WTS_ALPHATYPE *pdwAlpha) {
    HANDLE hPipe = CreateFileW(
        L"\\\\.\\pipe\\RawViewThumbnailPipe",
        GENERIC_READ | GENERIC_WRITE,
        0,
        NULL,
        OPEN_EXISTING,
        0,
        NULL
    );

    if (hPipe == INVALID_HANDLE_VALUE) {
        if (GetLastError() == ERROR_PIPE_BUSY) {
            if (WaitNamedPipeW(L"\\\\.\\pipe\\RawViewThumbnailPipe", 250)) {
                hPipe = CreateFileW(
                    L"\\\\.\\pipe\\RawViewThumbnailPipe",
                    GENERIC_READ | GENERIC_WRITE,
                    0,
                    NULL,
                    OPEN_EXISTING,
                    0,
                    NULL
                );
            }
        }
        if (hPipe == INVALID_HANDLE_VALUE) {
            return false;
        }
    }

    DWORD dwMode = PIPE_READMODE_MESSAGE;
    SetNamedPipeHandleState(hPipe, &dwMode, NULL, NULL);

    ThumbnailRequest req;
    req.magic = RVTP_MAGIC;
    req.cx = cx;
    req.pathCharCount = (uint32_t)m_filePath.size();

    DWORD bytesWritten = 0;
    if (!WriteFile(hPipe, &req, sizeof(req), &bytesWritten, NULL)) {
        CloseHandle(hPipe);
        return false;
    }

    if (!m_filePath.empty()) {
        DWORD pathBytes = (DWORD)(m_filePath.size() * sizeof(wchar_t));
        if (!WriteFile(hPipe, m_filePath.c_str(), pathBytes, &bytesWritten, NULL)) {
            CloseHandle(hPipe);
            return false;
        }
    }

    ThumbnailResponseHeader resp;
    DWORD bytesRead = 0;
    if (!ReadFile(hPipe, &resp, sizeof(resp), &bytesRead, NULL) || bytesRead < sizeof(resp)) {
        CloseHandle(hPipe);
        return false;
    }

    if (resp.magic != RVTP_MAGIC || resp.status != RVTP_STATUS_OK || resp.dataSize == 0) {
        CloseHandle(hPipe);
        return false;
    }

    DWORD expectedBytes = resp.width * resp.height * 4;
    if (resp.width == 0 || resp.height == 0 || resp.dataSize != expectedBytes || resp.dataSize > 32 * 1024 * 1024) {
        CloseHandle(hPipe);
        return false;
    }

    BYTE* buffer = (BYTE*)HeapAlloc(GetProcessHeap(), 0, resp.dataSize);
    if (!buffer) {
        CloseHandle(hPipe);
        return false;
    }

    DWORD totalRead = 0;
    while (totalRead < resp.dataSize) {
        DWORD chunkRead = 0;
        if (!ReadFile(hPipe, buffer + totalRead, resp.dataSize - totalRead, &chunkRead, NULL) || chunkRead == 0) {
            break;
        }
        totalRead += chunkRead;
    }
    CloseHandle(hPipe);

    if (totalRead != resp.dataSize) {
        HeapFree(GetProcessHeap(), 0, buffer);
        return false;
    }

    BITMAPINFO bmi = {0};
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth = (LONG)resp.width;
    bmi.bmiHeader.biHeight = -(LONG)resp.height; // top-down
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 32;
    bmi.bmiHeader.biCompression = BI_RGB;

    void* pBits = nullptr;
    HBITMAP hbmp = CreateDIBSection(NULL, &bmi, DIB_RGB_COLORS, &pBits, NULL, 0);
    if (!hbmp || !pBits) {
        HeapFree(GetProcessHeap(), 0, buffer);
        return false;
    }

    memcpy(pBits, buffer, resp.dataSize);
    HeapFree(GetProcessHeap(), 0, buffer);

    *phbmp = hbmp;
    *pdwAlpha = WTSAT_ARGB;
    return true;
}

static void EnsureBackgroundDaemonRunning() {
    static ULONGLONG s_lastLaunchTick = 0;
    ULONGLONG now = GetTickCount64();
    if (now - s_lastLaunchTick < 30000) {
        return;
    }
    s_lastLaunchTick = now;

    // Check if RawView single instance mutex is active
    HANDLE hMutex1 = OpenMutexW(SYNCHRONIZE, FALSE, L"RawView_SingleInstance_Mutex_v4.1.2");
    if (hMutex1) {
        CloseHandle(hMutex1);
        return;
    }
    HANDLE hMutex2 = OpenMutexW(SYNCHRONIZE, FALSE, L"Global\\RawView_SingleInstance_Mutex_v4.1.2");
    if (hMutex2) {
        CloseHandle(hMutex2);
        return;
    }

    // Locate RawView.exe in same directory as this DLL or standard install dir
    wchar_t dllPath[MAX_PATH];
    if (!GetModuleFileNameW(g_hInst, dllPath, MAX_PATH)) return;
    PathRemoveFileSpecW(dllPath);

    wchar_t exePath[MAX_PATH];
    swprintf_s(exePath, L"%s\\RawView.exe", dllPath);
    if (GetFileAttributesW(exePath) == INVALID_FILE_ATTRIBUTES) {
        wcscpy_s(exePath, L"C:\\Program Files\\RawView\\RawView.exe");
        if (GetFileAttributesW(exePath) == INVALID_FILE_ATTRIBUTES) {
            return;
        }
    }

    wchar_t cmd[MAX_PATH + 64];
    swprintf_s(cmd, L"\"%s\" --minimized", exePath);

    STARTUPINFOW si = { sizeof(si) };
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    PROCESS_INFORMATION pi = { 0 };

    if (CreateProcessW(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW | DETACHED_PROCESS, NULL, NULL, &si, &pi)) {
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
}

IFACEMETHODIMP CRawViewThumbnailProvider::GetThumbnail(UINT cx, HBITMAP *phbmp, WTS_ALPHATYPE *pdwAlpha) {
    if (!phbmp || !pdwAlpha) return E_POINTER;
    *phbmp = NULL;
    *pdwAlpha = WTSAT_UNKNOWN;

    if (m_filePath.empty()) return E_FAIL;

    try {
        // Tier 1: Check ultra-fast disk cache (<1ms)
        if (FetchFromDiskCache(cx, phbmp, pdwAlpha)) {
            return S_OK;
        }

        // Tier 2: Check live background service via Named Pipe (<10ms)
        if (FetchFromPipe(cx, phbmp, pdwAlpha)) {
            return S_OK;
        }

        // Gently trigger background service startup if not already running
        EnsureBackgroundDaemonRunning();
    }
    catch (...) {
        return E_FAIL;
    }

    return E_FAIL;
}
