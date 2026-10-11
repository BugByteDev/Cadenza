from pathlib import Path
root = Path(SPECPATH).parent
# Preserve the directory layout used by local inference and sampled instruments.
data = [(str(root/'dist'), 'dist'), (str(root/'sounds'), 'sounds'),
        (str(root/'build/runtime'), 'runtime'), (str(root/'build/notices'),'notices')]
for name in ['desktop_engine.mjs','render_soundfont.mjs','README.md','LICENSE','MODEL_CARD.md','MODEL_LICENSE.md','THIRD_PARTY_DESKTOP.md','DEPENDENCIES.txt']:
    data.append((str(root/name),'.'))
a = Analysis([str(root/'desktop.py')], pathex=[str(root)], binaries=[], datas=data, hiddenimports=['startup','pygame','render_portable','render_sampled_piano','playback','packaged_smoke'])
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='Cadenza',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=True,icon=str(root/'dist/assets/icon.ico') if __import__('sys').platform=='win32' else None)
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='Cadenza')
