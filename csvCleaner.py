import csv
import re

def clean_csv(input_file, output_file):
    """
    Cleans a CSV file by removing all numbers, dashes, double quotes, 
    and ensuring no duplicate values exist globally across the file.
    Outputs the cleaned data as a single comma-separated line.

    Args:
        input_file (str): Path to the input CSV file.
        output_file (str): Path to save the cleaned file.
    """
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        unique_values = set()  # Track all unique values globally

        for row in reader:
            for cell in row:
                cleaned_cell = re.sub(r'\d', '', cell)  # Remove numbers
                cleaned_cell = re.sub(r'\-', '', cleaned_cell)  # Remove dashes
                cleaned_cell = re.sub(r'\"', '', cleaned_cell)  # Remove double quotes
                if cleaned_cell not in unique_values and cleaned_cell.strip():  # Avoid duplicates and empty cells
                    unique_values.add(cleaned_cell)

    # Write all unique values as a single comma-separated line
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write(','.join(unique_values))

if __name__ == "__main__":
    input_file = "AllTickers.csv"  # Replace with your input file path
    output_file = "cleaned_output.csv"  # Replace with your desired output file path
    clean_csv(input_file, output_file)
    print(f"Cleaned file saved to {output_file}")
