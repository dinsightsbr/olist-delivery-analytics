# Power BI project — how to open, refresh and iterate

The dashboard is generated as a **Power BI Project (PBIP)** by [build_pbip.py](build_pbip.py):
a TMDL semantic model that imports `OLIST.MARTS` from Snowflake, ~45 DAX measures and a
PBIR report with five pages. Nothing here is hand-clicked; the storyboard lives in
[../docs/roteiro-apresentacao.md](../docs/roteiro-apresentacao.md) and the measure dictionary
in [measures.md](measures.md).

## 1. Open in Power BI Desktop

1. Power BI Desktop (Microsoft Store build 2.159 or newer is installed). If Desktop complains
   about the project format: **File → Options and settings → Options → Preview features**, tick
   *Power BI Project (.pbip) save option* and *Store reports using enhanced metadata format (PBIR)*,
   restart Desktop.
2. **File → Open report → Browse** and pick
   `case-dataart/powerbi/Olist Delivery Experience/Olist Delivery Experience.pbip`.
3. The report opens with empty visuals (no data cached yet). Click **Refresh**.
4. Credentials prompt (first time only). The Snowflake account was created with Google sign-in,
   so there is no password; Power BI uses a **service user with key pair auth** instead
   (created by the last block of `sql/00_setup.sql`):
   - In the dialog pick **Key Pair** on the left.
   - **User name:** `PBI_SERVICE`
   - **Private key:** browse to `~/.snowflake/pbi_service_rsa_key.p8`
     (local file, not in the repo; regenerate with the openssl lines in `00_setup.sql` if lost and
     update the public key in Snowflake).
   - **Passphrase:** leave empty (the key was generated unencrypted for the trial).
   - Privacy level, if asked: Organizational.
   - If the dialog has no *Key Pair* option, update Power BI Desktop (connector 2.0, July 2025+).
5. Refresh takes well under a minute (~99k orders, ~113k items, 6 dimensions + themes).

## 2. First things to check after refresh

- Page 1 cards: GMV ≈ R$ 13.5M, Orders 99,092, On-time 93.2%, Avg review 4.09, Repeat 3.1%.
- Page 2 first chart: On time 4.29 vs Late 8+ days ≈ 1.6–1.8; title shows the 2.27 vs 4.29 sentence.
- Page 3 bar chart: AL at the top (78.5%), SP/PR/RO/AM at the bottom (95%+); RJ at 87.8%.
- Page 4: move the *Late deliveries cut by (%)* slicer and watch the three scenario cards change.
- Page 5 table: matches `OLIST.MARTS.V_KPI_MONTHLY` for Jan 2017 to Aug 2018.

If a visual shows an error icon, hover it: the message names the measure or field. Report it
back; the generator is fixed and re-run, not the PBIX.

## 3. Save and version

- **File → Save** writes back into the same PBIP folders (Desktop may add `.pbi/` caches and
  `diagramLayout.json`; the caches are git-ignored).
- Commit the folder. Desktop reformats the TMDL/JSON on save; that is expected.
- From this point you can edit in Desktop (move visuals, tweak colours, add bookmarks) and keep
  saving. Re-running `build_pbip.py` **overwrites** the definition folders; do it only if you want
  to regenerate from the script, after porting your manual changes into it.

## 4. Suggested manual polish in Desktop (15–20 min)

1. Page 1: resize the combo chart's secondary axis to 85%–100% so the on-time line is readable.
2. Page 2: confirm the delivery-bucket bars are coloured blue / orange / red / grey (field value
   colour); if not, Format → Columns → Colour → fx → Field value → `Color | Delivery Bucket`.
3. Page 3: set the scatter's X axis start at 10% and Y at 0%; turn on category labels.
4. Page 4: if the slicer renders as a range, switch it to *Single value* in Format → Slicer settings.
5. Add bookmarks in story order (View → Bookmarks) and tidy the filter pane.
6. File → Export → PDF as the fallback copy for presentations.

## 5. Branding and canvas

Pages are 1600 × 900 with a branded background (`branding/bg_1600x900.png`: fictitious brand
"ROTA · Marketplace Analytics", dataset tag, footer). The generator lays visuals out on a 1280 × 720
grid and scales them onto the canvas, leaving the top 64 px for the band. Taller variants
(`bg_1600x1200.png`, `bg_1600x2000.png`) exist for scrolling pages; to use one, set
`PAGE_H`, `BACKGROUND` and the layout in `build_pbip.py`. Logos: `logo_rota.png` (light text) and
`logo_rota_dark.png` (dark text) for README and slides. Regenerate the images with
`python branding/make_backgrounds.py` (Pillow).

## 6. Regenerate

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" case-dataart\powerbi\build_pbip.py
```
