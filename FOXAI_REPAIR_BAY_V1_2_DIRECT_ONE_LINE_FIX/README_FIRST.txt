FOXAI REPAIR BAY V1.2 DIRECT ONE-LINE FIX

CONFIRMED LIVE FILE

The uploaded current live WebUI has SHA-256:

3d50f594191a130d7c816d7a8fc4defa434dba467cf79f8384ceadb6988f284b

It still contains the original Repair Bay V1 browser startup bug:

};renderRepairGuidedStatus(s)

That call sits outside refresh(), so the browser throws `s is not defined`
before grouped navigation initializes.

THIS PATCH

- Requires the exact confirmed broken SHA-256
- Replaces only that one sequence
- Produces the reviewed fixed SHA-256:

5601b36cd49d213d367954b9ff5e1456fb3c41b5eabe0b7e1ba56364e8ecec65

- Compiles the resulting Python file
- Creates a timestamped verified backup
- Uses atomic replacement
- Writes a receipt
- Does not alter projects, repairs, models, PDFs, runtimes, or settings

INSTALL

1. Close FOXAI WebUI.
2. Extract this entire folder directly inside Z:\FOXAI.
3. Run:

   Z:\FOXAI\FOXAI_REPAIR_BAY_V1_2_DIRECT_ONE_LINE_FIX\APPLY_REPAIR_BAY_V1_2_DIRECT_FIX.bat

4. Press Y.
5. Confirm the window prints:

   REPAIR BAY V1.2 DIRECT FIX INSTALLED
   After SHA-256: 5601b36cd49d213d367954b9ff5e1456fb3c41b5eabe0b7e1ba56364e8ecec65

6. Restart FOXAI WebUI.

EXPECTED RESULT

- Grouped department sidebar returns
- Search, Favorites, and Recents return
- Guided Repair Bay remains installed
