"""
Front matter: title page, declaration, certificate, abstract, acknowledgement, TOC, nomenclature, acronyms.
"""
from report_helpers import *


def write_front_matter(doc):
    # ── TITLE PAGE ────────────────────────────────────────────────────────────
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("PRO-ACTIVE DRIVER MONITORING SYSTEM USING EEG —\nPREDICTING DROWSINESS 5–10 MINUTES IN ADVANCE\nUSING MINIMAL OCCIPITAL SENSORS")
    run.bold = True; run.font.size = Pt(16); run.font.name = 'Times New Roman'

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("A Capstone Project Report\nSubmitted in partial fulfilment of the requirements for the degree of\nBachelor of Technology")
    run.font.size = Pt(12); run.font.name = 'Times New Roman'

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("by")
    run.font.size = Pt(12)
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("MUHAMMED RASLAN THALASSERY — 22BMH1046\nSULAIMAN SHIYAS ALI — 22BME1021")
    run.bold = True; run.font.size = Pt(13); run.font.name = 'Times New Roman'

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Under the guidance of\nDr. Abhishek Rudra Pal")
    run.font.size = Pt(12); run.font.name = 'Times New Roman'

    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("SCHOOL OF MECHANICAL ENGINEERING\nVELLORE INSTITUTE OF TECHNOLOGY, CHENNAI\nApril 2026")
    run.bold = True; run.font.size = Pt(12); run.font.name = 'Times New Roman'

    # ── DECLARATION ───────────────────────────────────────────────────────────
    page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run("DECLARATION")
    run.bold = True; run.font.size = Pt(14); run.font.name = 'Times New Roman'

    add_para(doc, 'We, Muhammed Raslan Thalassery (22BMH1046) and Sulaiman Shiyas Ali (22BME1021), hereby declare that the Capstone Project Report entitled "Pro-Active Driver Monitoring System Using EEG — Predicting Drowsiness 5–10 Minutes in Advance Using Minimal Occipital Sensors" submitted to the School of Mechanical Engineering, Vellore Institute of Technology, Chennai, in partial fulfilment of the requirements for the award of the degree of Bachelor of Technology, is a bona fide record of work carried out by us under the guidance of Dr. Abhishek Rudra Pal.')
    add_para(doc, "The results embodied in this report have not been submitted to any other university or institution for the award of any degree or diploma.")
    doc.add_paragraph()
    doc.add_paragraph()

    p = doc.add_paragraph()
    run = p.add_run("Place: Chennai\nDate: April 2026")
    run.font.size = Pt(12); run.font.name = 'Times New Roman'
    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run("Muhammed Raslan Thalassery (22BMH1046)")
    run.font.size = Pt(12); run.font.name = 'Times New Roman'
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run("Sulaiman Shiyas Ali (22BME1021)")
    run.font.size = Pt(12); run.font.name = 'Times New Roman'

    # ── CERTIFICATE ───────────────────────────────────────────────────────────
    page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run("CERTIFICATE")
    run.bold = True; run.font.size = Pt(14); run.font.name = 'Times New Roman'

    add_para(doc, 'This is to certify that the Capstone Project Report entitled "Pro-Active Driver Monitoring System Using EEG — Predicting Drowsiness 5–10 Minutes in Advance Using Minimal Occipital Sensors" submitted by Muhammed Raslan Thalassery (22BMH1046) and Sulaiman Shiyas Ali (22BME1021) to the School of Mechanical Engineering, Vellore Institute of Technology, Chennai, in partial fulfilment of the requirements for the award of the degree of Bachelor of Technology, is a bona fide record of work carried out under my guidance and supervision.')
    add_para(doc, "The contents of this report have not been submitted to any other university or institution for the award of any degree or diploma.")
    doc.add_paragraph()
    doc.add_paragraph()
    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run("Dr. Abhishek Rudra Pal\nProject Guide\nSchool of Mechanical Engineering\nVIT Chennai")
    run.font.size = Pt(12); run.font.name = 'Times New Roman'

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run("Internal Examiner\t\t\tExternal Examiner")
    run.font.size = Pt(12); run.font.name = 'Times New Roman'

    # ── ABSTRACT ──────────────────────────────────────────────────────────────
    page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run("ABSTRACT")
    run.bold = True; run.font.size = Pt(14); run.font.name = 'Times New Roman'

    add_para(doc, "Driver drowsiness is a leading contributor to road traffic fatalities worldwide, accounting for approximately 20% of fatal accidents. Existing driver monitoring systems operate reactively, detecting drowsiness only after behavioural symptoms have manifested, thereby offering insufficient time for preventive intervention. This project presents a proactive driver monitoring system that predicts drowsiness onset 5–10 minutes in advance using electroencephalographic (EEG) signals acquired from only two occipital electrodes (O1 and O2) embedded in a standard vehicle headrest.")
    add_para(doc, "The system employs a 4th-order Butterworth bandpass filter (0.5–40 Hz) for signal preprocessing, followed by Welch's power spectral density estimation to extract theta (4–8 Hz) and alpha (8–13 Hz) band power within 60-second sliding windows. A Random Forest classifier trained on the DROZY clinical dataset (10 subjects, ~30 hours of EEG) achieved 89.54% classification accuracy with the 2-channel headrest configuration — only 1.95% below the 4-channel baseline (91.32%). The core innovation is a temporal trend extrapolation algorithm that applies linear regression to a rolling 5-minute history of the theta/alpha ratio, predicting when the drowsiness biomarker will breach a personalised threshold. Validation on DROZY Subject 07F demonstrated 27/27 critical drowsiness events detected with 0% critical false alarms and an average advance warning of 7–9 minutes. Cross-dataset exploration on SEED-VIG was also conducted. The graduated alert system (Yellow, Red, Critical) ensures timely driver intervention at an estimated hardware cost of $100–500, making it the first system to combine proactive temporal prediction with a headrest-embedded, minimal-sensor EEG configuration suitable for mass-market automotive deployment.")
    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run("Keywords: ")
    run.bold = True; run.font.name = 'Times New Roman'; run.font.size = Pt(12)
    run2 = p.add_run("EEG, Drowsiness Detection, Driver Monitoring, Theta/Alpha Ratio, Random Forest, Proactive Prediction, Occipital Sensors, Vehicle Headrest")
    run2.font.name = 'Times New Roman'; run2.font.size = Pt(12)

    # ── ACKNOWLEDGEMENT ───────────────────────────────────────────────────────
    page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run("ACKNOWLEDGEMENT")
    run.bold = True; run.font.size = Pt(14); run.font.name = 'Times New Roman'

    add_para(doc, "We would like to express our sincere gratitude to our project guide, Dr. Abhishek Rudra Pal, School of Mechanical Engineering, VIT Chennai, for his invaluable guidance, encouragement, and constant support throughout this project. His expertise and constructive feedback were instrumental in shaping this work.")
    add_para(doc, "We extend our heartfelt thanks to the Head of the Department, School of Mechanical Engineering, VIT Chennai, for providing the necessary infrastructure and facilities to carry out this project.")
    add_para(doc, "We are grateful to the researchers at the University of Liège, Belgium, for making the DROZY dataset publicly available, and to the Shanghai Jiao Tong University for the SEED-VIG dataset, both of which were essential for the validation of this system.")
    add_para(doc, "We also thank the developers of the open-source tools and libraries — MNE-Python, scikit-learn, SciPy, and Streamlit — that made the signal processing and machine learning aspects of this project possible.")
    add_para(doc, "Finally, we wish to thank our families and friends for their unwavering support and encouragement throughout our academic journey.")
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run("Muhammed Raslan Thalassery\nSulaiman Shiyas Ali")
    run.font.name = 'Times New Roman'; run.font.size = Pt(12)

    # ── TABLE OF CONTENTS (placeholder) ───────────────────────────────────────
    page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run("TABLE OF CONTENTS")
    run.bold = True; run.font.size = Pt(14); run.font.name = 'Times New Roman'
    add_para(doc, "[Generate Table of Contents in Microsoft Word: References → Table of Contents → Automatic Table]")

    # ── LIST OF FIGURES (placeholder) ─────────────────────────────────────────
    page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run("LIST OF FIGURES")
    run.bold = True; run.font.size = Pt(14); run.font.name = 'Times New Roman'
    add_para(doc, "[Generate List of Figures in Microsoft Word: References → Insert Table of Figures → Select 'Figure' label]")

    # ── LIST OF TABLES (placeholder) ──────────────────────────────────────────
    page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run("LIST OF TABLES")
    run.bold = True; run.font.size = Pt(14); run.font.name = 'Times New Roman'
    add_para(doc, "[Generate List of Tables in Microsoft Word: References → Insert Table of Figures → Select 'Table' label]")

    # ── NOMENCLATURE ──────────────────────────────────────────────────────────
    page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run("NOMENCLATURE")
    run.bold = True; run.font.size = Pt(14); run.font.name = 'Times New Roman'

    nom = [
        ("\u03b8", "Theta band power (4\u20138 Hz)"),
        ("\u03b1", "Alpha band power (8\u201313 Hz)"),
        ("R", "Theta/Alpha ratio (drowsiness index)"),
        ("R_baseline", "Personal awake baseline ratio"),
        ("R_threshold", "Alert threshold = 1.5 \u00d7 R_baseline"),
        ("t_remaining", "Predicted minutes until drowsiness onset"),
        ("m", "Linear regression slope of ratio trend"),
        ("fs", "Sampling frequency (128 Hz)"),
        ("N", "Window length in samples"),
    ]
    add_table(doc, ["Symbol", "Description"], nom, "", "")

    # ── ACRONYMS ──────────────────────────────────────────────────────────────
    page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run("LIST OF ACRONYMS")
    run.bold = True; run.font.size = Pt(14); run.font.name = 'Times New Roman'

    acr = [
        ("EEG", "Electroencephalography"),
        ("PSD", "Power Spectral Density"),
        ("RF", "Random Forest"),
        ("SNR", "Signal-to-Noise Ratio"),
        ("BPF", "Bandpass Filter"),
        ("O1, O2", "Occipital electrodes (left, right)"),
        ("ROC", "Receiver Operating Characteristic"),
        ("AUC", "Area Under the Curve"),
        ("SDG", "Sustainable Development Goal"),
        ("OEM", "Original Equipment Manufacturer"),
        ("FFT", "Fast Fourier Transform"),
        ("ADC", "Analogue-to-Digital Converter"),
        ("DMS", "Driver Monitoring System"),
        ("CAN", "Controller Area Network"),
    ]
    add_table(doc, ["Acronym", "Meaning"], acr, "", "")
