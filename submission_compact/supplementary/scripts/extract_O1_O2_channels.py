"""
EEG Channel Extractor: O1/O2 Only
Extracts occipital channels (O1, O2) from DROZY EDF files for GitHub repository

Author: Muhammad
Date: March 5, 2026
Purpose: Reduce repository size by keeping only headrest-relevant channels
"""

import mne
import os
from pathlib import Path

def extract_o1_o2_channels(input_file, output_dir):
    """
    Extract only O1 and O2 channels from EDF file.
    
    Parameters:
    -----------
    input_file : str
        Path to input EDF file (full DROZY dataset)
    output_dir : str
        Directory to save extracted O1/O2 EDF file
    
    Returns:
    --------
    str : Path to output file
    """
    
    # Read original EDF file
    print(f"Reading: {os.path.basename(input_file)}")
    raw = mne.io.read_raw_edf(input_file, preload=True, verbose=False)
    
    # Get available channels
    available_channels = raw.ch_names
    print(f"  Available channels: {available_channels}")
    
    # Define channels to keep (O1-Ref, O2-Ref occipital sensors - DROZY naming)
    channels_to_keep = ['O1-Ref', 'O2-Ref']
    
    # Check if O1-Ref and O2-Ref exist
    missing = [ch for ch in channels_to_keep if ch not in available_channels]
    if missing:
        print(f"  ⚠️ Warning: Missing channels {missing}, skipping file")
        return None
    
    # Pick only O1 and O2 channels
    raw_o1_o2 = raw.pick_channels(channels_to_keep, ordered=True)
    
    # Fix physical min/max to fit EDF format constraints (8 character limit)
    # Clamp values to reasonable EEG range (-3200 to 3200 µV)
    for ch in raw_o1_o2.info['chs']:
        ch['cal'] = 1.0  # Reset calibration
        # Set physical min/max within format limits
        if 'range' in ch:
            ch['range'] = 6400.0  # Total range
    
    # Create output filename
    input_name = Path(input_file).stem  # e.g., "01M_1"
    output_name = f"{input_name}_O1_O2.edf"
    output_path = os.path.join(output_dir, output_name)
    
    # Export to new EDF file with physical_range constraint
    raw_o1_o2.export(output_path, overwrite=True, physical_range=(-3200, 3200))
    
    # Get file sizes
    input_size = os.path.getsize(input_file) / (1024 * 1024)  # MB
    output_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
    reduction = (1 - output_size/input_size) * 100
    
    print(f"  ✓ Saved: {output_name}")
    print(f"    Original: {input_size:.2f} MB → Extracted: {output_size:.2f} MB ({reduction:.1f}% reduction)")
    
    return output_path


def process_drozy_dataset(drozy_dir, output_dir):
    """
    Process all DROZY EDF files and extract O1/O2 channels.
    
    Parameters:
    -----------
    drozy_dir : str
        Path to DROZY directory containing original EDF files
    output_dir : str
        Directory to save extracted files
    """
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all EDF files (exclude annotation files)
    edf_files = [f for f in Path(drozy_dir).glob("*.edf") 
                 if not "annotations" in f.name]
    
    print(f"\n{'='*60}")
    print(f"DROZY O1/O2 Channel Extraction")
    print(f"{'='*60}\n")
    print(f"Found {len(edf_files)} EDF files in {drozy_dir}")
    print(f"Output directory: {output_dir}\n")
    
    successful = 0
    failed = 0
    total_input_size = 0
    total_output_size = 0
    
    # Process each file
    for i, edf_file in enumerate(sorted(edf_files), 1):
        print(f"\n[{i}/{len(edf_files)}] Processing: {edf_file.name}")
        
        try:
            # Extract O1/O2 channels
            output_path = extract_o1_o2_channels(str(edf_file), output_dir)
            
            if output_path:
                successful += 1
                total_input_size += os.path.getsize(str(edf_file))
                total_output_size += os.path.getsize(output_path)
            else:
                failed += 1
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"✓ Successful: {successful} files")
    print(f"✗ Failed: {failed} files")
    print(f"\nStorage reduction:")
    print(f"  Original:  {total_input_size / (1024*1024):.2f} MB")
    print(f"  Extracted: {total_output_size / (1024*1024):.2f} MB")
    print(f"  Saved:     {(total_input_size - total_output_size) / (1024*1024):.2f} MB")
    if total_input_size > 0:
        print(f"  Reduction: {(1 - total_output_size/total_input_size)*100:.1f}%")
    print(f"\n✓ All files saved to: {output_dir}")
    print(f"✓ Ready for GitHub upload!\n")


def main():
    """Main execution function"""
    
    # Directory paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    drozy_input_dir = os.path.join(base_dir, "DROZY")
    drozy_output_dir = os.path.join(base_dir, "DROZY_O1_O2")
    
    # Check if DROZY directory exists
    if not os.path.exists(drozy_input_dir):
        print(f"✗ Error: DROZY directory not found at {drozy_input_dir}")
        print(f"  Please ensure DROZY dataset is in the correct location.")
        return
    
    # Process the dataset
    process_drozy_dataset(drozy_input_dir, drozy_output_dir)
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. Review extracted files in DROZY_O1_O2/ directory")
    print("2. Update notebook to use DROZY_O1_O2/*.edf files")
    print("3. Add DROZY_O1_O2/ to git:")
    print("   git add DROZY_O1_O2/")
    print("4. Commit and push to GitHub")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
