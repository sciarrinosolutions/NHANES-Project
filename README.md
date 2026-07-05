# NHANES-Project
Analysis of NHANES datasets, supplementary applications, ML Model Development and Evaluation, and Django Web Application for Blood Screening Recommendation System

Data Downloaded from CDC website, available in the Google Drive folder [here](https://drive.google.com/drive/folders/1x93sOFpR4IGW7YT4ZFQKV5mDLOO2AVch?usp=drive_link).

## CSV Conversion

Run ```convert_to_csv.py``` to convert SAS .xpt files from Google Drive folder to CSVs.

## NHANES Explorer

A Django application that helps navigate the NHANES codebook with fuzzy search. Allows for correlation analysis against blood test measurements.

To run, navigate to the NHANES_Explorer folder and run:

```python manage.py runserver```

