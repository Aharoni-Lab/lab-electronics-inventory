import re

# Define the path to your file
file_path = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/extracted_texts.txt"
output_path = "/Users/abasaltbahrami/Desktop/lab-electronics-inventory/extracted_mfg_parts.txt"

# Define a regular expression pattern to match manufacturing part numbers with multi-line support
# Matches various forms like "MFG P/N" and "Manufacturer Part Number" across multiple lines
mfg_part_number_pattern = re.compile(
    r"(?:MFG\s*[./]*\s*P[/]?N|MFG\s*[./]*\s*N|1FG\s*/N|Manufacturer\s*Part\s*Number)[:#-]?\s*([\w/-]+)",
    re.IGNORECASE
)

# Open and read the file
with open(file_path, 'r') as file:
    content = file.read()

# Pre-process content by removing newlines right after MFG patterns
# This way, part numbers spanning multiple lines are treated as a single line
processed_content = re.sub(
    r"(MFG\s*[./]*\s*P[/]?N|MFG\s*[./]*\s*N|1FG\s*/N|Manufacturer\s*Part\s*Number)[:#-]?\s*\n\s*", r"\1 ", content)

# Find all matches in the processed content
matches = mfg_part_number_pattern.findall(processed_content)

# Save results to the output file
with open(output_path, 'w') as output_file:
    for match in matches:
        output_file.write(f"MFG: {match}\n")

print(f"Extracted part numbers saved to {output_path}")
