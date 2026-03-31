# -*- mode: python ; coding: utf-8 -*-


def _normalized_dest(entry):
    if not isinstance(entry, (list, tuple)) or not entry:
        return ""
    return str(entry[0]).replace("\\", "/").lower()


def _is_excluded_qt_artifact(entry):
    dest = _normalized_dest(entry)
    if not dest.startswith("pyqt6/qt6/"):
        return False

    if dest.startswith("pyqt6/qt6/translations/"):
        return True

    excluded_exact = {
        "pyqt6/qt6/bin/libcrypto-3.dll",
        "pyqt6/qt6/bin/qt6network.dll",
        "pyqt6/qt6/bin/opengl32sw.dll",
        "pyqt6/qt6/bin/qt6pdf.dll",
        "pyqt6/qt6/bin/qt6svg.dll",
        "pyqt6/qt6/plugins/generic/qtuiotouchplugin.dll",
        "pyqt6/qt6/plugins/iconengines/qsvgicon.dll",
        "pyqt6/qt6/plugins/imageformats/qgif.dll",
        "pyqt6/qt6/plugins/imageformats/qicns.dll",
        "pyqt6/qt6/plugins/imageformats/qpdf.dll",
        "pyqt6/qt6/plugins/imageformats/qsvg.dll",
        "pyqt6/qt6/plugins/imageformats/qtga.dll",
        "pyqt6/qt6/plugins/imageformats/qtiff.dll",
        "pyqt6/qt6/plugins/imageformats/qwbmp.dll",
        "pyqt6/qt6/plugins/imageformats/qwebp.dll",
        "pyqt6/qt6/plugins/platforms/qminimal.dll",
        "pyqt6/qt6/plugins/platforms/qoffscreen.dll",
        "pyqt6/qt6/plugins/styles/qmodernwindowsstyle.dll",
    }
    return dest in excluded_exact


def _is_excluded_common_binary(entry):
    dest = _normalized_dest(entry)
    excluded_exact = {
        "_hashlib.pyd",
        "libcrypto-3.dll",
    }
    return dest in excluded_exact


def _is_excluded_artifact(entry):
    return _is_excluded_qt_artifact(entry) or _is_excluded_common_binary(entry)


a = Analysis(
    ['standup_timer.13.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)
a.binaries = [entry for entry in a.binaries if not _is_excluded_artifact(entry)]
a.datas = [entry for entry in a.datas if not _is_excluded_artifact(entry)]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='StandUpTimer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['ikon.ico'],
)
