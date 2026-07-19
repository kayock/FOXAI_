FOXAI ENGINEERING WORKSHOP V1

This package extends the existing Departments\Engineering folder. It does not
modify the original uploaded ZIP.

1. Extract this package to a temporary folder.
2. Preview the installation:
     INSTALL_ENGINEERING_WORKSHOP_V1.bat
3. Install after reviewing the target and file list:
     INSTALL_ENGINEERING_WORKSHOP_V1.bat --approve

The installer:
- targets Z:\FOXAI\Departments\Engineering by default;
- creates one exact backup under Z:\FOXAI\System\EngineeringWorkshop\InstallBackups;
- adds/replaces only the listed Engineering Workshop files;
- deletes nothing;
- installs no packages and uses no network;
- runs the harmless Workshop test suite;
- restores the backup automatically when tests fail;
- writes a real JSON install receipt.

The package builds the controlled backend worker and CLI. Connecting the current
read-only Engineer WebUI screen to this worker still requires the live Mission
Director/WebUI controller source files, which were not included in Engineering.zip.
