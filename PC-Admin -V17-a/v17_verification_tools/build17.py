import zipfile, os, hashlib, sys
R="/home/claude/v17/"
OUT="/mnt/user-data/outputs/"
DT=(2026,10,21,0,0,0)
ORDER={"WebService":["app.py","templates/index.html","pcadmintool_service.py","requirements.txt","check_port.bat","install_service.bat","run_console_testmode.bat","uninstall_service.bat","install_and_run.sh","pcadmintool.service.template","README.txt","logs/"],
       "PythonGUI":["PCAdminTool.pyw","requirements.txt","install_and_run.bat","README.txt"],
       "PowerShell":["PCAdminTool.ps1","Run-AdminTool.bat","README.txt"]}
built=[]
for e,files in ORDER.items():
    d=f"{R}PC_Admin_Tool_{e}_Edition/"
    # no stray files
    actual=set()
    for root,dirs,fs in os.walk(d):
        dirs[:]=[x for x in dirs if x!="__pycache__"]
        for f in fs: actual.add(os.path.relpath(os.path.join(root,f),d).replace(os.sep,"/"))
    expected={f for f in files if not f.endswith("/")}
    assert actual==expected,(e,actual^expected)
    zp=f"{R}PC_Admin_Tool_{e}_Edition.zip"
    with zipfile.ZipFile(zp,"w",zipfile.ZIP_DEFLATED) as z:
        for f in files:
            zi=zipfile.ZipInfo(f,DT)
            if f.endswith("/"):
                zi.external_attr=(0o40755<<16)|0x10; zi.compress_type=zipfile.ZIP_STORED; z.writestr(zi,b"")
            else:
                data=open(d+f,"rb").read()
                zi.external_attr=((0o100755 if f.endswith(".sh") else 0o100644)<<16); zi.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(zi,data)
    built.append(zp)
outer=OUT+"Multi-edition_PC_cleanup_tool-v17.zip"
with zipfile.ZipFile(outer,"w",zipfile.ZIP_DEFLATED) as z:
    for zp in built:
        zi=zipfile.ZipInfo(os.path.basename(zp),DT); zi.external_attr=0o100644<<16; zi.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(zi,open(zp,"rb").read())
for zp in built+[outer]:
    print(os.path.getsize(zp), os.path.basename(zp))
