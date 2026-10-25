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

CRawViewThumbnailProvider::CRawViewThumbnailProvider() : m_cRef(1) {
    InterlockedIncrement(&g_cDllRef);
}

CRawViewThumbnailProvider::~CRawViewThumbnailProvider() {
    InterlockedDecrement(&g_cDllRef);
}

IFACEMETHODIMP CRawViewThumbnailProvider::QueryInterface(REFIID riid, void **ppv) {
    static const QITAB qit[] = {
        QITABENT(CRawViewThumbnailProvider, IInitializeWithFile),
        QITABENT(CRawViewThumbnailProvider, IThumbnailProvider),
        { 0 },
    };
    return QISearch(this, qit, riid, ppv);
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

    std::wstringstream ss;
    ss << localAppData << L"\\RawView\\cache\\thumbs";
    std::wstring thumbDir = ss.str();
    CreateDirectoryW(thumbDir.c_str(), NULL);

    std::wstringstream fileName;
    fileName << thumbDir << L"\\thumb_" << std::hex << pathHash << L"_" << mtime << L"_" << cx << L".bmp";
    return fileName.str();
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
        return false;
    }

    // Set pipe to message mode
    DWORD dwMode = PIPE_READMODE_MESSAGE;
    SetNamedPipeHandleState(hPipe, &dwMode, NULL, NULL);

    // Prepare request
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

    // Read response header
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

    // Allocate buffer for pixel data
    std::vector<uint8_t> buffer(resp.dataSize);
    DWORD totalRead = 0;
    while (totalRead < resp.dataSize) {
        DWORD chunkRead = 0;
        if (!ReadFile(hPipe, buffer.data() + totalRead, resp.dataSize - totalRead, &chunkRead, NULL) || chunkRead == 0) {
            break;
        }
        totalRead += chunkRead;
    }
    CloseHandle(hPipe);

    if (totalRead != resp.dataSize) {
        return false;
    }

    // Construct 32-bit ARGB DIBSection
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
        return false;
    }

    memcpy(pBits, buffer.data(), resp.dataSize);

    *phbmp = hbmp;
    *pdwAlpha = WTSAT_ARGB;
    return true;
}

bool CRawViewThumbnailProvider::FetchFromHeadlessWorker(UINT cx, HBITMAP *phbmp, WTS_ALPHATYPE *pdwAlpha) {
    // Locate RawView.exe in same directory as this DLL or standard install dir
    wchar_t dllPath[MAX_PATH];
    if (!GetModuleFileNameW(g_hInst, dllPath, MAX_PATH)) return false;
    PathRemoveFileSpecW(dllPath);

    std::wstring exePath = std::wstring(dllPath) + L"\\RawView.exe";
    if (GetFileAttributesW(exePath.c_str()) == INVALID_FILE_ATTRIBUTES) {
        exePath = L"C:\\Program Files\\RawView\\RawView.exe";
        if (GetFileAttributesW(exePath.c_str()) == INVALID_FILE_ATTRIBUTES) {
            return false;
        }
    }

    std::wstring cachePath = GetCacheFilePath(cx);

    std::wstringstream cmd;
    cmd << L"\"" << exePath << L"\" --headless-thumb \"" << m_filePath << L"\" " << cx << L" \"" << cachePath << L"\"";

    STARTUPINFOW si = { sizeof(si) };
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    PROCESS_INFORMATION pi = { 0 };

    std::vector<wchar_t> cmdBuf(cmd.str().begin(), cmd.str().end());
    cmdBuf.push_back(0);

    if (CreateProcessW(NULL, cmdBuf.data(), NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        WaitForSingleObject(pi.hProcess, 1500); // Wait max 1.5 seconds
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);

        return FetchFromDiskCache(cx, phbmp, pdwAlpha);
    }

    return false;
}

IFACEMETHODIMP CRawViewThumbnailProvider::GetThumbnail(UINT cx, HBITMAP *phbmp, WTS_ALPHATYPE *pdwAlpha) {
    if (!phbmp || !pdwAlpha) return E_POINTER;
    *phbmp = NULL;
    *pdwAlpha = WTSAT_UNKNOWN;

    if (m_filePath.empty()) return E_FAIL;

    // Tier 1: Check ultra-fast disk cache (<1ms)
    if (FetchFromDiskCache(cx, phbmp, pdwAlpha)) {
        return S_OK;
    }

    // Tier 2: Check live background service via Named Pipe (<10ms)
    if (FetchFromPipe(cx, phbmp, pdwAlpha)) {
        return S_OK;
    }

    // Tier 3: If background service is closed or restarting, launch headless worker
    if (FetchFromHeadlessWorker(cx, phbmp, pdwAlpha)) {
        return S_OK;
    }

    return E_FAIL;
}
