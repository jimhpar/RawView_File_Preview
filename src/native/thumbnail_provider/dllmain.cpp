#include "RawViewThumbnailProvider.h"
#include <shlwapi.h>

#pragma comment(lib, "shlwapi.lib")
#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "shell32.lib")

// {78FDF5BA-0E57-4B06-8230-1340EE5EA83B}
const CLSID CLSID_RawViewThumbnailProvider = 
    { 0x78fdf5ba, 0x0e57, 0x4b06, { 0x82, 0x30, 0x13, 0x40, 0xee, 0x5e, 0xa8, 0x3b } };

const wchar_t* SZ_CLSID_RAWVIEW_THUMB = L"{78FDF5BA-0E57-4B06-8230-1340EE5EA83B}";
const wchar_t* SZ_IID_ITHUMBNAILPROVIDER = L"{e357fccd-a995-4576-b01f-234630154e96}";

HINSTANCE g_hInst = NULL;
long g_cDllRef = 0;

// List of supported extensions for permanent Windows Explorer thumbnails
static const wchar_t* SUPPORTED_EXTENSIONS[] = {
    // Adobe Design
    L".psd", L".psb", L".ai", L".eps",
    // Documents & Office
    L".pdf", L".docx", L".doc", L".rtf",
    L".pptx", L".ppt", L".xlsx", L".xls",
    // Camera RAW
    L".cr2", L".cr3", L".crw",
    L".nef", L".nrw",
    L".arw", L".srf", L".sr2",
    L".raf", L".orf", L".rw2", L".pef", L".ptx",
    L".3fr", L".fff", L".iiq", L".raw", L".x3f", L".dng",
    // Vectors
    L".svg", L".svgz",
    // Archives & Compressed Packages
    L".zip", L".rar", L".7z", L".tar", L".gz", L".tgz", L".bz2"
};

class CRawViewClassFactory : public IClassFactory {
public:
    CRawViewClassFactory() : m_cRef(1) { InterlockedIncrement(&g_cDllRef); }
    virtual ~CRawViewClassFactory() { InterlockedDecrement(&g_cDllRef); }

    // IUnknown
    IFACEMETHODIMP QueryInterface(REFIID riid, void **ppv) {
        static const QITAB qit[] = {
            QITABENT(CRawViewClassFactory, IClassFactory),
            { 0 },
        };
        return QISearch(this, qit, riid, ppv);
    }
    IFACEMETHODIMP_(ULONG) AddRef() { return InterlockedIncrement(&m_cRef); }
    IFACEMETHODIMP_(ULONG) Release() {
        ULONG cRef = InterlockedDecrement(&m_cRef);
        if (cRef == 0) delete this;
        return cRef;
    }

    // IClassFactory
    IFACEMETHODIMP CreateInstance(IUnknown *pUnkOuter, REFIID riid, void **ppv) {
        if (pUnkOuter != NULL) return CLASS_E_NOAGGREGATION;
        CRawViewThumbnailProvider *pProvider = new (std::nothrow) CRawViewThumbnailProvider();
        if (!pProvider) return E_OUTOFMEMORY;
        HRESULT hr = pProvider->QueryInterface(riid, ppv);
        pProvider->Release();
        return hr;
    }

    IFACEMETHODIMP LockServer(BOOL fLock) {
        if (fLock) InterlockedIncrement(&g_cDllRef);
        else InterlockedDecrement(&g_cDllRef);
        return S_OK;
    }

private:
    long m_cRef;
};

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
    if (ul_reason_for_call == DLL_PROCESS_ATTACH) {
        g_hInst = hModule;
        DisableThreadLibraryCalls(hModule);
    }
    return TRUE;
}

STDAPI DllCanUnloadNow(void) {
    return (g_cDllRef == 0) ? S_OK : S_FALSE;
}

STDAPI DllGetClassObject(REFCLSID rclsid, REFIID riid, LPVOID *ppv) {
    if (!ppv) return E_POINTER;
    *ppv = NULL;

    if (IsEqualCLSID(rclsid, CLSID_RawViewThumbnailProvider)) {
        CRawViewClassFactory *pFactory = new (std::nothrow) CRawViewClassFactory();
        if (!pFactory) return E_OUTOFMEMORY;
        HRESULT hr = pFactory->QueryInterface(riid, ppv);
        pFactory->Release();
        return hr;
    }
    return CLASS_E_CLASSNOTAVAILABLE;
}

static HRESULT SetRegistryValue(HKEY hRoot, const std::wstring& subKey, const std::wstring& valueName, const std::wstring& data) {
    HKEY hKey;
    LONG lRes = RegCreateKeyExW(hRoot, subKey.c_str(), 0, NULL, REG_OPTION_NON_VOLATILE, KEY_SET_VALUE, NULL, &hKey, NULL);
    if (lRes != ERROR_SUCCESS) return HRESULT_FROM_WIN32(lRes);

    lRes = RegSetValueExW(hKey, valueName.empty() ? NULL : valueName.c_str(), 0, REG_SZ, 
                          (const BYTE*)data.c_str(), (DWORD)((data.size() + 1) * sizeof(wchar_t)));
    RegCloseKey(hKey);
    return HRESULT_FROM_WIN32(lRes);
}

static HRESULT SetRegistryDword(HKEY hRoot, const std::wstring& subKey, const std::wstring& valueName, DWORD data) {
    HKEY hKey;
    LONG lRes = RegCreateKeyExW(hRoot, subKey.c_str(), 0, NULL, REG_OPTION_NON_VOLATILE, KEY_SET_VALUE, NULL, &hKey, NULL);
    if (lRes != ERROR_SUCCESS) return HRESULT_FROM_WIN32(lRes);

    lRes = RegSetValueExW(hKey, valueName.c_str(), 0, REG_DWORD, (const BYTE*)&data, sizeof(DWORD));
    RegCloseKey(hKey);
    return HRESULT_FROM_WIN32(lRes);
}

static void CleanCorruptedUserRegistry() {
    // 1. Remove all fake ProgID keys from HKCU that were mistakenly created without DefaultIcon
    const wchar_t* ADOBE_PROGIDS[] = {
        L"Photoshop.Image.20", L"Photoshop.Image.21", L"Photoshop.Image.22",
        L"Photoshop.Image.23", L"Photoshop.Image.24", L"Photoshop.Image.25",
        L"Photoshop.Image.26", L"Photoshop.Image.27", L"Photoshop.Image.28",
        L"Photoshop.Image.29", L"Photoshop.Image.30",
        L"Photoshop.PSBFile.24", L"Photoshop.PSBFile.25", L"Photoshop.PSBFile.26",
        L"Photoshop.PSBFile.27", L"Photoshop.PSBFile.28",
        L"Adobe.Illustrator.24", L"Adobe.Illustrator.25", L"Adobe.Illustrator.26",
        L"Adobe.Illustrator.27", L"Adobe.Illustrator.28", L"Adobe.Illustrator.29",
        L"Adobe.Illustrator.30", L"Adobe.Illustrator.EPS"
    };

    for (const wchar_t* pId : ADOBE_PROGIDS) {
        std::wstring baseKey = std::wstring(L"Software\\Classes\\") + pId;
        HKEY hKey;
        if (RegOpenKeyExW(HKEY_CURRENT_USER, baseKey.c_str(), 0, KEY_READ, &hKey) == ERROR_SUCCESS) {
            HKEY hIconKey;
            bool hasIcon = (RegOpenKeyExW(hKey, L"DefaultIcon", 0, KEY_READ, &hIconKey) == ERROR_SUCCESS);
            if (hasIcon) RegCloseKey(hIconKey);

            HKEY hCmdKey;
            bool hasCommand = (RegOpenKeyExW(hKey, L"shell\\open\\command", 0, KEY_READ, &hCmdKey) == ERROR_SUCCESS);
            if (hasCommand) RegCloseKey(hCmdKey);

            RegCloseKey(hKey);

            // If it has no icon and no open command, it was an empty key created by the installer. Delete it!
            if (!hasIcon && !hasCommand) {
                RegDeleteTreeW(HKEY_CURRENT_USER, baseKey.c_str());
            } else {
                RegDeleteTreeW(HKEY_CURRENT_USER, (baseKey + L"\\ShellEx").c_str());
            }
        }
    }

    // 2. Clean up HKCU file extension keys that shadow HKLM and broke default icons
    for (const wchar_t* ext : SUPPORTED_EXTENSIONS) {
        std::wstring hkcuExt = std::wstring(L"Software\\Classes\\") + ext;
        std::wstring hkcuShellex = hkcuExt + L"\\ShellEx\\" + SZ_IID_ITHUMBNAILPROVIDER;
        RegDeleteKeyW(HKEY_CURRENT_USER, hkcuShellex.c_str());
        RegDeleteKeyW(HKEY_CURRENT_USER, (hkcuExt + L"\\ShellEx").c_str());

        std::wstring hkcuSfa = std::wstring(L"Software\\Classes\\SystemFileAssociations\\") + ext + L"\\ShellEx\\" + SZ_IID_ITHUMBNAILPROVIDER;
        RegDeleteKeyW(HKEY_CURRENT_USER, hkcuSfa.c_str());

        // Check if HKCU\<ext> has default value or other subkeys left
        HKEY hKey;
        if (RegOpenKeyExW(HKEY_CURRENT_USER, hkcuExt.c_str(), 0, KEY_READ, &hKey) == ERROR_SUCCESS) {
            DWORD subKeys = 0;
            DWORD values = 0;
            wchar_t defVal[256] = {0};
            DWORD defSize = sizeof(defVal);
            LONG qRes = RegQueryValueExW(hKey, NULL, NULL, NULL, (LPBYTE)defVal, &defSize);
            RegQueryInfoKeyW(hKey, NULL, NULL, NULL, &subKeys, NULL, NULL, &values, NULL, NULL, NULL, NULL);
            RegCloseKey(hKey);

            // If default value is not set or empty, and no subkeys, remove the key so HKLM associations shine through
            if ((qRes != ERROR_SUCCESS || defVal[0] == 0) && subKeys == 0) {
                RegDeleteKeyW(HKEY_CURRENT_USER, hkcuExt.c_str());
            }
        }
    }

    // 3. Delete CLSID from HKCU
    std::wstring hkcuClsid = L"Software\\Classes\\CLSID\\" + std::wstring(SZ_CLSID_RAWVIEW_THUMB);
    RegDeleteTreeW(HKEY_CURRENT_USER, hkcuClsid.c_str());
}

STDAPI DllRegisterServer(void) {
    wchar_t szDllPath[MAX_PATH];
    if (!GetModuleFileNameW(g_hInst, szDllPath, MAX_PATH)) {
        return HRESULT_FROM_WIN32(GetLastError());
    }

    // 1. Clean up any shadowing or corrupted keys in HKCU
    CleanCorruptedUserRegistry();

    // 2. Register CLSID in HKEY_LOCAL_MACHINE
    std::wstring clsidSubKey = L"Software\\Classes\\CLSID\\" + std::wstring(SZ_CLSID_RAWVIEW_THUMB);
    SetRegistryValue(HKEY_LOCAL_MACHINE, clsidSubKey, L"", L"RawView Thumbnail Provider");
    SetRegistryValue(HKEY_LOCAL_MACHINE, clsidSubKey + L"\\InprocServer32", L"", szDllPath);
    SetRegistryValue(HKEY_LOCAL_MACHINE, clsidSubKey + L"\\InprocServer32", L"ThreadingModel", L"Apartment");
    SetRegistryDword(HKEY_LOCAL_MACHINE, clsidSubKey, L"DisableProcessIsolation", 1);

    // 3. Register thumbnail provider under SystemFileAssociations and extension in HKLM
    for (const wchar_t* ext : SUPPORTED_EXTENSIONS) {
        std::wstring sfaKey = std::wstring(L"Software\\Classes\\SystemFileAssociations\\") + ext + L"\\ShellEx\\" + SZ_IID_ITHUMBNAILPROVIDER;
        SetRegistryValue(HKEY_LOCAL_MACHINE, sfaKey, L"", SZ_CLSID_RAWVIEW_THUMB);

        std::wstring shellexKey = std::wstring(L"Software\\Classes\\") + ext + L"\\ShellEx\\" + SZ_IID_ITHUMBNAILPROVIDER;
        SetRegistryValue(HKEY_LOCAL_MACHINE, shellexKey, L"", SZ_CLSID_RAWVIEW_THUMB);

        // Check if there is an associated ProgID under HKCR\<ext> and register ShellEx under HKLM\<ProgID>
        HKEY hExtKey;
        if (RegOpenKeyExW(HKEY_CLASSES_ROOT, ext, 0, KEY_READ, &hExtKey) == ERROR_SUCCESS) {
            wchar_t progIdBuf[256] = {0};
            DWORD dwBufSize = sizeof(progIdBuf);
            if (RegQueryValueExW(hExtKey, NULL, NULL, NULL, (LPBYTE)progIdBuf, &dwBufSize) == ERROR_SUCCESS && progIdBuf[0]) {
                // Only register if the ProgID actually exists in HKLM
                HKEY hProgCheck;
                std::wstring progKeyPath = std::wstring(L"Software\\Classes\\") + progIdBuf;
                if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, progKeyPath.c_str(), 0, KEY_READ, &hProgCheck) == ERROR_SUCCESS) {
                    RegCloseKey(hProgCheck);
                    std::wstring progShellex = progKeyPath + L"\\ShellEx\\" + SZ_IID_ITHUMBNAILPROVIDER;
                    SetRegistryValue(HKEY_LOCAL_MACHINE, progShellex, L"", SZ_CLSID_RAWVIEW_THUMB);
                }
            }
            RegCloseKey(hExtKey);
        }
    }

    // 4. Register explicit known Adobe Photoshop and Illustrator ProgIDs IF they are installed in HKLM
    const wchar_t* ADOBE_PROGIDS[] = {
        L"Photoshop.Image.20", L"Photoshop.Image.21", L"Photoshop.Image.22",
        L"Photoshop.Image.23", L"Photoshop.Image.24", L"Photoshop.Image.25",
        L"Photoshop.Image.26", L"Photoshop.Image.27", L"Photoshop.Image.28",
        L"Photoshop.Image.29", L"Photoshop.Image.30",
        L"Photoshop.PSBFile.24", L"Photoshop.PSBFile.25", L"Photoshop.PSBFile.26",
        L"Photoshop.PSBFile.27", L"Photoshop.PSBFile.28",
        L"Adobe.Illustrator.24", L"Adobe.Illustrator.25", L"Adobe.Illustrator.26",
        L"Adobe.Illustrator.27", L"Adobe.Illustrator.28", L"Adobe.Illustrator.29",
        L"Adobe.Illustrator.30", L"Adobe.Illustrator.EPS"
    };

    for (const wchar_t* pId : ADOBE_PROGIDS) {
        HKEY hProgKey;
        std::wstring progKeyPath = std::wstring(L"Software\\Classes\\") + pId;
        // ONLY register if this ProgID actually exists in HKLM!
        if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, progKeyPath.c_str(), 0, KEY_READ, &hProgKey) == ERROR_SUCCESS) {
            RegCloseKey(hProgKey);
            std::wstring progShellex = progKeyPath + L"\\ShellEx\\" + SZ_IID_ITHUMBNAILPROVIDER;
            SetRegistryValue(HKEY_LOCAL_MACHINE, progShellex, L"", SZ_CLSID_RAWVIEW_THUMB);
        }
    }

    // 5. Ensure "Display file icon on thumbnails" (App Badges: Ps, Ai) is enabled in Windows Explorer
    SetRegistryDword(HKEY_CURRENT_USER, L"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced", L"ShowTypeOverlay", 1);

    // 6. Register "Refresh Thumbnail" in Explorer Context Menus
    wchar_t appExePath[MAX_PATH];
    wcscpy_s(appExePath, szDllPath);
    PathRemoveFileSpecW(appExePath);
    std::wstring appDir = appExePath;
    std::wstring exePath = appDir + L"\\RawView.exe";
    std::wstring iconPath = appDir + L"\\assets\\app_icon.ico";

    // A. Single file context menu for all supported extensions under SystemFileAssociations
    for (const wchar_t* ext : SUPPORTED_EXTENSIONS) {
        std::wstring sfaMenu = std::wstring(L"Software\\Classes\\SystemFileAssociations\\") + ext + L"\\shell\\RawViewRefreshThumb";
        SetRegistryValue(HKEY_LOCAL_MACHINE, sfaMenu, L"", L"Refresh Thumbnail");
        SetRegistryValue(HKEY_LOCAL_MACHINE, sfaMenu, L"Icon", L"\"" + iconPath + L"\"");
        std::wstring sfaCmd = sfaMenu + L"\\command";
        SetRegistryValue(HKEY_LOCAL_MACHINE, sfaCmd, L"", L"\"" + exePath + L"\" --refresh-thumb \"%1\"");
    }

    // B. Folder empty space context menu (Directory Background)
    std::wstring dirBgMenu = L"Software\\Classes\\Directory\\Background\\shell\\RawViewRefreshFolderThumbs";
    SetRegistryValue(HKEY_LOCAL_MACHINE, dirBgMenu, L"", L"Refresh Thumbnails");
    SetRegistryValue(HKEY_LOCAL_MACHINE, dirBgMenu, L"Icon", L"\"" + iconPath + L"\"");
    std::wstring dirBgCmd = dirBgMenu + L"\\command";
    SetRegistryValue(HKEY_LOCAL_MACHINE, dirBgCmd, L"", L"\"" + exePath + L"\" --refresh-folder \"%V\"");

    // C. Folder item context menu (Directory)
    std::wstring dirMenu = L"Software\\Classes\\Directory\\shell\\RawViewRefreshFolderThumbs";
    SetRegistryValue(HKEY_LOCAL_MACHINE, dirMenu, L"", L"Refresh Thumbnails");
    SetRegistryValue(HKEY_LOCAL_MACHINE, dirMenu, L"Icon", L"\"" + iconPath + L"\"");
    std::wstring dirCmd = dirMenu + L"\\command";
    SetRegistryValue(HKEY_LOCAL_MACHINE, dirCmd, L"", L"\"" + exePath + L"\" --refresh-folder \"%1\"");

    // 7. Notify Windows Shell to refresh caches
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);
    return S_OK;
}

STDAPI DllUnregisterServer(void) {
    std::wstring clsidSubKey = L"Software\\Classes\\CLSID\\" + std::wstring(SZ_CLSID_RAWVIEW_THUMB);
    RegDeleteTreeW(HKEY_LOCAL_MACHINE, clsidSubKey.c_str());

    for (const wchar_t* ext : SUPPORTED_EXTENSIONS) {
        std::wstring shellexKey = std::wstring(L"Software\\Classes\\") + ext + L"\\ShellEx\\" + SZ_IID_ITHUMBNAILPROVIDER;
        RegDeleteKeyW(HKEY_LOCAL_MACHINE, shellexKey.c_str());

        std::wstring sfaKey = std::wstring(L"Software\\Classes\\SystemFileAssociations\\") + ext + L"\\ShellEx\\" + SZ_IID_ITHUMBNAILPROVIDER;
        RegDeleteKeyW(HKEY_LOCAL_MACHINE, sfaKey.c_str());

        // Delete context menu keys
        std::wstring sfaCmd = std::wstring(L"Software\\Classes\\SystemFileAssociations\\") + ext + L"\\shell\\RawViewRefreshThumb\\command";
        RegDeleteKeyW(HKEY_LOCAL_MACHINE, sfaCmd.c_str());
        std::wstring sfaMenu = std::wstring(L"Software\\Classes\\SystemFileAssociations\\") + ext + L"\\shell\\RawViewRefreshThumb";
        RegDeleteKeyW(HKEY_LOCAL_MACHINE, sfaMenu.c_str());
    }

    RegDeleteTreeW(HKEY_LOCAL_MACHINE, L"Software\\Classes\\Directory\\Background\\shell\\RawViewRefreshFolderThumbs");
    RegDeleteTreeW(HKEY_LOCAL_MACHINE, L"Software\\Classes\\Directory\\shell\\RawViewRefreshFolderThumbs");

    const wchar_t* ADOBE_PROGIDS[] = {
        L"Photoshop.Image.20", L"Photoshop.Image.21", L"Photoshop.Image.22",
        L"Photoshop.Image.23", L"Photoshop.Image.24", L"Photoshop.Image.25",
        L"Photoshop.Image.26", L"Photoshop.Image.27", L"Photoshop.Image.28",
        L"Photoshop.Image.29", L"Photoshop.Image.30",
        L"Photoshop.PSBFile.24", L"Photoshop.PSBFile.25", L"Photoshop.PSBFile.26",
        L"Photoshop.PSBFile.27", L"Photoshop.PSBFile.28",
        L"Adobe.Illustrator.24", L"Adobe.Illustrator.25", L"Adobe.Illustrator.26",
        L"Adobe.Illustrator.27", L"Adobe.Illustrator.28", L"Adobe.Illustrator.29",
        L"Adobe.Illustrator.30", L"Adobe.Illustrator.EPS"
    };

    for (const wchar_t* pId : ADOBE_PROGIDS) {
        std::wstring shellexKey = std::wstring(L"Software\\Classes\\") + pId + L"\\ShellEx\\" + SZ_IID_ITHUMBNAILPROVIDER;
        RegDeleteKeyW(HKEY_LOCAL_MACHINE, shellexKey.c_str());
    }

    // Clean up any remaining HKCU keys
    CleanCorruptedUserRegistry();

    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);
    return S_OK;
}
