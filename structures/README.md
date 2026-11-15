# Published crystal structures for clay XRD

65 published crystal structures, as CIF files: the clay minerals and the
minerals that accompany them in clay X-ray diffraction. They were selected on
2026-11-15 and are separate from MudLab's built-in model components.

| In this folder | |
|---|---|
| `Clays/` | 18 layer silicates: kaolin and serpentine minerals, micas and illites, smectites, vermiculite and chlorites |
| `Non-clays/` | 47 other minerals: silica and feldspars, carbonates, sulfates, oxides, zeolites, and the fibrous clays sepiolite and palygorskite |
| `CREDITS.md` | the article to cite for every structure |
| `manifest.csv` | one row per file: mineral, group, formula, citation, database id, notes, and a checksum |

## Using a structure in MudLab

- **A clay, as a component of a clay phase.** Open *Edit Phases*, select the
  phase, and in its component editor choose **Import CIF…**. The file dialog
  opens in `Clays`. MudLab projects the structure along c\* and shows the result
  for review before it replaces anything.
- **A non-clay phase.** In *Edit Phases*, choose **Import Non-Clay**, then open
  a file. The dialog opens in `Non-clays`. The pattern is computed for the
  wavelength of your instrument.
- **Any file works either way.** A clay can also be imported as a non-clay
  phase, which gives its fixed powder pattern instead of a stacking model.
- **Help → Structure Collection…** opens this folder.

Three files are two-layer polytypes that the importer does not fold to one
layer by itself: **nacrite**, **muscovite-2M1** and **paragonite-2M1**. In the
import review, set *Layers stacked in the published cell* to 2. The `hint`
column of `manifest.csv` gives the numbers.

Fibrous clays (sepiolite, palygorskite) are channel structures, not stacks of
layers, so they are in `Non-clays`. Import them with Import Non-Clay.

The files are ordinary CIFs, so other crystallographic programs can read them
too.

## Citing and terms of use

**Cite the original article whenever you use a structure.** `CREDITS.md` lists
the article for each file.

- Structures from the **Crystallography Open Database (COD)** are in the public
  domain.
- Structures from the **American Mineralogist Crystal Structure Database
  (AMCSD)** may be used *"so long as proper attribution is given to the journal
  article from which the data were obtained"*.
- Some files reached MudLab through atomipy, which bundles the Avogadro 2 crystal
  library. They are COD or AMCSD structures and carry those terms.

MudLab's own licence covers the program, not these data.

## Leave the files unchanged

Each file is the published CIF, byte for byte; only its name is new. The
`sha256` column of `manifest.csv` records the published bytes, so the citation
provably describes the file. To modify a structure, save a copy somewhere else
first.

## How they were chosen

One structure per mineral, chosen by these rules: measured, not computed;
ambient conditions; natural or near-end-member composition; a modern refinement
where one exists; a DOI where available; and coherent sets preferred
(Gualtieri 2000 quantitative-XRD standards, Effenberger 1981 carbonates,
Howard 1991 TiO₂). The `note` column says where an entry is one of a series,
for example a heating or high-pressure study.

## Not included

- **Beidellite** and **saponite**: no published single-crystal structure.
  MudLab's model components cover them.
- **Halloysite**: only Mehmel 1935, which is not a usable refinement.
- **Glauconite**: left out for now. Every COD glauconite (Drits et al. 2010) is
  an idealised model with an all-Al octahedral site. Glauconite is Fe-rich, so
  the model would give illite-like intensities.
