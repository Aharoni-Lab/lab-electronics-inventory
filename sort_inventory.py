import os
import re
import pandas as pd

# Define the path to the text file
text_file_path = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/extracted_texts.txt'
output_excel_file = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/sorted_inventory.xlsx'
log_file_path = '/Users/abasaltbahrami/Desktop/lab-electronics-inventory/processing_log.txt'


def parse_component_info(lines, image_name):
    component_info = {}
    combined_text = " ".join(lines)

    if not combined_text.strip():  # Check if the file is empty or has no content
        log_message = f"Skipped empty or invalid content in file: {image_name}\n"
        log_processing(log_message)
        return None

    # Identify component type and subcategory
    if re.search(r'\bIC\b', combined_text):  # Look for IC alone, not part of any other word
        component_info['Component Name'] = "IC"

        # Extract the next two words that come immediately after "IC"
        subcategory_match = re.search(
            r'IC\s+(\w+\s+\w+)', combined_text, re.IGNORECASE)
        if subcategory_match:
            component_info['Subcategory'] = subcategory_match.group(1)

        # Extract Value for ICs (e.g., "-3.3U 500MA")
        value_match = re.search(
            r'(-?\d+(\.\d+)?[uUmMkK]? ?[A-Za-z]+ ?\d+ ?[A-Za-z]+)', combined_text)
        if value_match:
            component_info['Value'] = value_match.group(0)

    # Recognize connectors (CONN)
    elif re.search(r'\bCONN\b', combined_text, re.IGNORECASE):  # For connectors
        component_info['Component Name'] = "Connector"

        # Extract the next word after "CONN" as the subcategory
        subcategory_match = re.search(
            r'CONN\s+(\w+)', combined_text, re.IGNORECASE)
        if subcategory_match:
            component_info['Subcategory'] = subcategory_match.group(1)

        # Extract the number of positions (pins)
        position_match = re.search(r'(\d+)POS', combined_text, re.IGNORECASE)
        if position_match:
            component_info['Position'] = position_match.group(1) + " Position"

        # Extract the pitch (e.g., 0.1)
        pitch_match = re.search(r'(\d+(\.\d+)?)\s*', combined_text)
        if pitch_match:
            component_info['Pitch'] = pitch_match.group(1) + " inch"

        # Extract material or coating (e.g., TIN)
        material_match = re.search(
            r'\b(TIN|GOLD)\b', combined_text, re.IGNORECASE)
        if material_match:
            component_info['Material'] = material_match.group(0).capitalize()

        # Type for PCB
        if re.search(r'\bPCB\b', combined_text, re.IGNORECASE):
            component_info['Type'] = "PCB"

    elif "OHM" in combined_text:
        component_info['Component Name'] = "Resistor"
    elif any(unit in combined_text for unit in ["uF", "nF", "pF", "F", "kF"]):
        component_info['Component Name'] = "Capacitor"
    else:
        component_info['Component Name'] = "Other"

    # Extract Part Number
    part_number_match = re.search(r'\b[\d\w-]{6,}-ND\b', combined_text)
    if part_number_match:
        component_info['Part Number'] = part_number_match.group(0)

    # Extract MFG Part Number
    mfg_part_match = re.search(
        r'\b(?![\d\w-]{6,}-ND)[A-Za-z0-9-]{12,}\b', combined_text)
    if mfg_part_match and re.search(r'[A-Za-z]', mfg_part_match.group(0)) and re.search(r'[0-9]', mfg_part_match.group(0)):
        mfg_part_number = mfg_part_match.group(0)

        # Ensure the MFG part number is not the same as the Part Number
        if 'Part Number' not in component_info or component_info['Part Number'] != mfg_part_number:
            component_info['MFG Part Number'] = mfg_part_number

    # Extract manufacturer and quantity
    manufacturer_match = re.search(
        r'\b(MURATA|PANASONIC|TAIYO|SAMSUNG|KEMET|NICHICON|TDK|VISHAY|YAGEO|KOA|ON|STMICROELECTRONICS|ROHM|AVX|BOURNS|EPCOS|TE|AMPHENOL|MOLEX|LITTELFUSE)\b',
        combined_text, re.IGNORECASE)

    if manufacturer_match:
        component_info['Manufacturer'] = manufacturer_match.group(0)

        # Extract the first number after "QTY" for Quantity
        qty_match = re.search(r'\bQTY\s*(\d+)', combined_text, re.IGNORECASE)
        if qty_match:
            component_info['Quantity'] = int(qty_match.group(1))

    # Extract country
    country_match = re.search(
        r'(SINGAPORE|USA|JAPAN|GERMANY|CHINA|SOUTH KOREA|TAIWAN|MEXICO|MALAYSIA|VIETNAM)',
        combined_text, re.IGNORECASE)

    if country_match:
        component_info['Country'] = country_match.group(0)

    # Extract capacitance, resistance, voltage, power, tolerance
    capacitance_match = re.search(
        r'(\d+(\.\d+)?(uF|nF|pF|F|kF))', combined_text, re.IGNORECASE)
    resistance_match = re.search(
        r'(\d+(\.\d+)?[KMG]?\s*OHM)', combined_text, re.IGNORECASE)

    if capacitance_match:
        component_info['Value'] = capacitance_match.group(0)
    elif resistance_match:
        component_info['Value'] = resistance_match.group(0)

    voltage_match = re.search(r'(\d+V)', combined_text, re.IGNORECASE)
    if voltage_match:
        component_info['Voltage'] = voltage_match.group(0)

    power_match = re.search(
        r'(\d+(\.\d+)?(/[0-9]+)?W)', combined_text, re.IGNORECASE)
    if power_match:
        component_info['Power'] = power_match.group(0)

    tolerance_match = re.search(r'(\d+%)', combined_text)
    if tolerance_match:
        component_info['Tolerance'] = tolerance_match.group(0)

    # Extract footprint
    common_footprints = [
        '0201', '0402', '0603', '0805', '1206', '1210', '1812', '2220',
        'QFN', 'DFN', 'SOT', 'SOT-23', 'SOT-89', 'SOT-223',
        'SOIC', 'TSSOP', 'MSOP', 'LQFP', 'BGA', 'CSP',
        'TQFP', 'DIP'
    ]

    for footprint in common_footprints:
        if footprint in combined_text:
            component_info['Footprint'] = footprint
            break

    return component_info


def log_processing(message):
    with open(log_file_path, 'a') as log_file:
        log_file.write(message)


def process_text_file(file_path, output_excel):
    components_list = []
    current_image = ""

    with open(file_path, 'r') as file:
        lines = file.readlines()

        current_text_block = []
        for line in lines:
            line = line.strip()

            if line.startswith('Image:'):
                if current_text_block:
                    component_info = parse_component_info(
                        current_text_block, current_image)
                    if component_info:
                        component_info['Image'] = current_image
                        components_list.append(component_info)
                    current_text_block = []

                current_image = line.split(": ")[1]
                log_processing(f"Processing file: {current_image}\n")

            elif line.startswith('Extracted Text:'):
                current_text_block = []
            else:
                current_text_block.append(line)

        if current_text_block:
            component_info = parse_component_info(
                current_text_block, current_image)
            if component_info:
                component_info['Image'] = current_image
                components_list.append(component_info)

    components_df = pd.DataFrame(components_list)

    if 'Value' not in components_df.columns:
        components_df['Value'] = None

    sorted_components_df = components_df.sort_values(by='Component Name')

    columns_order = ['Image', 'Component Name', 'Subcategory', 'Value', 'Voltage', 'Power', 'Tolerance',
                     'Footprint', 'Quantity', 'Manufacturer', 'Part Number', 'MFG Part Number', 'Country']

    for col in columns_order:
        if col not in sorted_components_df.columns:
            sorted_components_df[col] = None

    sorted_components_df = sorted_components_df[columns_order]

    sorted_components_df.to_excel(output_excel, index=False)
    print(f"Sorted data saved to {output_excel}")


# Process the text file and extract component information
process_text_file(text_file_path, output_excel_file)
