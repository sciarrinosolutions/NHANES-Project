from pathlib import Path
import pandas as pd
import os
import logging

# Set up logging configuration
logging.basicConfig(filename='error_log.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

DATA_FOLDER = Path("data")

CSV_FOLDER = Path("csv")

os.makedirs(CSV_FOLDER, exist_ok=True)

# Iterate through all folders in the data directory and create a folder with the same name in the CSV directory
for folder in DATA_FOLDER.iterdir():
    if folder.is_dir():
        csv_subfolder = CSV_FOLDER / folder.name
        os.makedirs(csv_subfolder, exist_ok=True)

        print(f"Processing folder: {folder.name} -> {csv_subfolder}")

        # Iterate through all .xpt files in the current folder
        for xpt_file in folder.glob("*.xpt"):
            print(xpt_file)

            try:
                # Read the .xpt file into a pandas DataFrame
                df = pd.read_sas(xpt_file, format='xport', encoding='utf-8')

                # Create the output CSV file path
                csv_file_path = csv_subfolder / (xpt_file.stem + ".csv")

                # Save the DataFrame to a CSV file
                df.to_csv(csv_file_path, index=False)
            
            except Exception as e:
                # Log the error and continue processing the next file
                logging.error(f"Error processing file {xpt_file}: {e}")
                continue
