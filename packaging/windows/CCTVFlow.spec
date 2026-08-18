from pathlib import Path

from PyInstaller.utils.hooks import collect_all


project_root = Path(SPECPATH).parents[1]
playwright_data, playwright_binaries, playwright_hidden = collect_all(
    "playwright"
)

application_data = [
    (str(project_root / "cctvflow" / "resources"), "cctvflow/resources"),
    (str(project_root / "cctvflow" / "ui" / "assets"), "cctvflow/ui/assets"),
    *playwright_data,
]

analysis = Analysis(
    [str(project_root / "cctvflow_gui.py")],
    pathex=[str(project_root)],
    binaries=playwright_binaries,
    datas=application_data,
    hiddenimports=playwright_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
python_archive = PYZ(analysis.pure)

executable = EXE(
    python_archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="CCTVFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

bundle = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CCTVFlow",
)
