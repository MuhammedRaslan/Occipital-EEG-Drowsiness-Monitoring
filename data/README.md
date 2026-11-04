# Data

No EEG data are included in this repository. Both datasets are third-party releases with their own terms; obtain them from their publishers and place them here, or point the scripts elsewhere with the environment variables below.

## DD-Database (Drivers Drowsiness Database)

Orosco et al., Dryad, 2023, [doi:10.5061/dryad.5tb2rbp9c](https://doi.org/10.5061/dryad.5tb2rbp9c). License: CC0.

Download the 20 signal EDF files and the 20 annotation EDF files (`01M_1.edf`, `01M_1_annotations.edf`, ...) into

```
data/DD-Database/
```

or set `DD_DIR` to the folder that holds them. The scripts read the original EDF files and convert them to microvolts from each file's header.

## SEED-VIG

Zheng and Lu, *J. Neural Eng.*, 14(2), 026017, 2017, [doi:10.1088/1741-2552/aa5a98](https://doi.org/10.1088/1741-2552/aa5a98). Available from the BCMI laboratory, Shanghai Jiao Tong University, under a license agreement.

Place the distributed `Raw_Data/` and `perclos_labels/` folders in one folder and set `SEED_VIG_DIR` to it. Step 00 (`analysis/00_seed_extract.py`) then builds

```
data/features_seed_vig_cache.npz
```

which holds the ten features of every epoch with PERCLOS below 0.35 or above 0.70. If the cache already exists, put it at that path or set `SEED_CACHE` to it.

Step 00 repeats the extraction that built the cache behind the article. It gave identical values on a synthetic recording in the same layout, but it has not itself been run on the raw files, which were not held on the machine that ran these analyses.

## Locations

| Variable | Default |
|---|---|
| `DATA_DIR` | `data/` |
| `DD_DIR` | `data/DD-Database/` |
| `SEED_CACHE` | `data/features_seed_vig_cache.npz` |
| `SEED_VIG_DIR` | none (needed only to rebuild the SEED-VIG cache) |
