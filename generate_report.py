"""
Main Report Generator — Assembles all modules into a single .docx file.
Run: python generate_report.py
Output: Capstone_Report.docx
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from report_helpers import create_doc, OUT_PATH
from report_front_matter import write_front_matter
from report_chapters_1_3 import write_chapter1, write_chapter2, write_chapter3
from report_chapter4 import write_chapter4
from report_chapters_5_6 import write_chapter5, write_chapter6, write_references, write_appendices


def main():
    print("=" * 60)
    print("  Capstone Report Generator")
    print("  Pro-Active Driver Monitoring System Using EEG")
    print("=" * 60)

    print("\n[1/8] Creating document with formatting...")
    doc = create_doc()

    print("[2/8] Writing front matter (title, declaration, abstract, etc.)...")
    write_front_matter(doc)

    print("[3/8] Writing Chapter 1: Introduction...")
    write_chapter1(doc)

    print("[4/8] Writing Chapter 2: Review of Literature...")
    write_chapter2(doc)

    print("[5/8] Writing Chapter 3: Problem Definition and Objectives...")
    write_chapter3(doc)

    print("[6/8] Writing Chapter 4: Methodology...")
    write_chapter4(doc)

    print("[7/8] Writing Chapter 5: Results and Discussion...")
    write_chapter5(doc)

    print("[7/8] Writing Chapter 6: Conclusion...")
    write_chapter6(doc)

    print("[8/8] Writing References, Appendices, Publications...")
    write_references(doc)
    write_appendices(doc)

    print(f"\nSaving to: {OUT_PATH}")
    doc.save(OUT_PATH)
    print(f"\n{'=' * 60}")
    print(f"  SUCCESS! Report saved to:")
    print(f"  {OUT_PATH}")
    print(f"{'=' * 60}")
    print(f"\nNext steps:")
    print(f"  1. Open Capstone_Report.docx in Microsoft Word")
    print(f"  2. Generate TOC: References -> Table of Contents")
    print(f"  3. Generate LOF: References -> Insert Table of Figures")
    print(f"  4. Replace screenshot placeholders with actual screenshots")
    print(f"  5. Transfer content into the official VIT template")


if __name__ == "__main__":
    main()
