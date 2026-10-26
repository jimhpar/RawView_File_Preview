#pragma once

#include <windows.h>
#include <thumbcache.h>
#include <propsys.h>
#include <shlobj.h>
#include <string>
#include <vector>

// CLSID: {78FDF5BA-0E57-4B06-8230-1340EE5EA83B}
extern const CLSID CLSID_RawViewThumbnailProvider;

// RVTP Protocol Constants
#define RVTP_MAGIC 0x52565450 // 'RVTP'
#define RVTP_STATUS_OK 1
#define RVTP_STATUS_FAIL 0
#define RVTP_FORMAT_BGRA32 1

#pragma pack(push, 1)
struct ThumbnailRequest {
    uint32_t magic;
    uint32_t cx;
    uint32_t pathCharCount; // count of wchar_t
};

struct ThumbnailResponseHeader {
    uint32_t magic;
    uint32_t status;
    uint32_t width;
    uint32_t height;
    uint32_t format;
    uint32_t dataSize; // raw byte count
};
#pragma pack(pop)

class CRawViewThumbnailProvider : public IInitializeWithFile,
                                   public IThumbnailProvider
{
public:
    CRawViewThumbnailProvider();
    virtual ~CRawViewThumbnailProvider();

    // IUnknown
    IFACEMETHODIMP QueryInterface(REFIID riid, void **ppv);
    IFACEMETHODIMP_(ULONG) AddRef();
    IFACEMETHODIMP_(ULONG) Release();

    // IInitializeWithFile
    IFACEMETHODIMP Initialize(LPCWSTR pszFilePath, DWORD grfMode);

    // IThumbnailProvider
    IFACEMETHODIMP GetThumbnail(UINT cx, HBITMAP *phbmp, WTS_ALPHATYPE *pdwAlpha);

private:
    long m_cRef;
    std::wstring m_filePath;

    bool FetchFromPipe(UINT cx, HBITMAP *phbmp, WTS_ALPHATYPE *pdwAlpha);
    bool FetchFromDiskCache(UINT cx, HBITMAP *phbmp, WTS_ALPHATYPE *pdwAlpha);
    std::wstring GetCacheFilePath(UINT cx);
};
