import mne
import numpy as np

raw = mne.io.read_raw_edf("DROZY_O1_O2/01M_1_O1_O2.edf", preload=True, verbose=False)
d = raw.get_data()
print(f"Raw range: {d.min():.6f} to {d.max():.6f} V")
print(f"In uV: {d.min()*1e6:.1f} to {d.max()*1e6:.1f} uV")
print(f"Channels: {raw.ch_names}")

raw.filter(1, 40, verbose=False)
d2 = raw.get_data()
print(f"Filtered range: {d2.min()*1e6:.1f} to {d2.max()*1e6:.1f} uV")
print(f"Filtered abs max: {np.max(np.abs(d2))*1e6:.1f} uV")
