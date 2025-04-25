import os
import csv
import re
from datetime import datetime

class Emptying:
    """
    Class representing a single emptying record
    """
    def __init__(self, timestamp=None, tag_code="", waste_type="", latitude=0.0, longitude=0.0, weight=0.0):
        self.timestamp = timestamp if timestamp else datetime.now()
        self.tag_code = tag_code
        self.waste_type = waste_type
        self.latitude = latitude
        self.longitude = longitude
        self.weight = weight

    def __str__(self):
        return f"Emptying: {self.tag_code} - {self.waste_type} - {self.weight}kg at {self.timestamp}"

    @classmethod
    def from_csv_row(cls, row):
        """
        Create an Emptying object from a CSV row

        Expected CSV format:
        timestamp, tag_code, waste_type, latitude, longitude, weight
        """
        try:
            # Parse timestamp (format may vary)
            timestamp_str = row[0] if len(row) > 0 else ""
            timestamp = None
            formats_to_try = ["%Y-%m-%d-%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", 
                             "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S", 
                             "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"] # Add more formats if needed
            for fmt in formats_to_try:
                 try:
                     timestamp = datetime.strptime(timestamp_str, fmt)
                     break # Found a working format
                 except ValueError:
                     continue # Try next format
            if timestamp is None: # Default if no format worked
                 timestamp = datetime.now()

            # Parse tag code
            tag_code = row[1].strip() if len(row) > 1 else ""

            # Parse waste type
            waste_type = row[2].strip() if len(row) > 2 else ""

            # Parse coordinates
            lat_str = row[3] if len(row) > 3 else ""
            lon_str = row[4] if len(row) > 4 else ""

            # Clean and normalize coordinate strings
            def clean_coord(coord_str):
                # First try to directly convert to float
                try:
                    return float(coord_str)
                except (ValueError, TypeError):
                    # If that fails, try to clean the string
                    if not coord_str or not isinstance(coord_str, str):
                        return 0.0
                    # Keep only digits, decimal point, and minus sign
                    cleaned = re.sub(r'[^\d.\-]', '', coord_str)
                    # Handle multiple decimal points
                    parts = cleaned.split('.')
                    if len(parts) > 2:
                        cleaned = parts[0] + '.' + ''.join(parts[1:])
                    try:
                        return float(cleaned)
                    except (ValueError, TypeError):
                        return 0.0

            latitude = clean_coord(lat_str)
            longitude = clean_coord(lon_str)
            
            # Check for obviously wrong values
            if abs(latitude) > 90:
                # Fix common case where coordinates are swapped
                if abs(longitude) <= 90:
                    latitude, longitude = longitude, latitude
            
            if abs(longitude) > 180:
                # Set to fallback value if completely out of range
                longitude = 0.0

            # Parse weight, removing 'kg' if present
            weight = 0.0
            if len(row) > 5 and row[5]:
                weight_str = str(row[5]).lower().replace('kg', '').strip()
                try:
                    weight = float(weight_str) if weight_str else 0.0
                except ValueError:
                    weight = 0.0

            return cls(timestamp, tag_code, waste_type, latitude, longitude, weight)
        except Exception as e:
            # Create a clearly marked 'error' record that will still show in the table
            return cls(datetime.now(), f"ERROR_PARSING: {str(row)[:30]}...", "error", 0.0, 0.0, 0.0)

def read_emptyings_from_csv(filepath):
    """
    Read emptying records from a CSV file

    Returns:
    list: List of Emptying objects
    """
    emptyings = []
    line_num = 0
    
    try:
        # First check if file exists
        if not os.path.isfile(filepath):
            return emptyings
        
        # Check file size
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            return emptyings
            
        with open(filepath, 'r', encoding='utf-8') as csvfile:
            # Try to detect the CSV dialect
            sample = csvfile.read(1024)
            csvfile.seek(0)  # Reset file pointer
            dialect = None
            try:
                dialect = csv.Sniffer().sniff(sample)
                reader = csv.reader(csvfile, dialect)
            except:
                reader = csv.reader(csvfile)
                
            try:
                headers = next(reader)  # Skip header row
                line_num += 1
            except StopIteration:
                 return emptyings # File is empty

            # Process rows
            for row in reader:
                line_num += 1
                if not row: # Skip empty rows
                    continue
                emptying = Emptying.from_csv_row(row)
                emptyings.append(emptying)

    except Exception as e:
        # Return whatever we've parsed so far
        pass

    return emptyings

def save_emptyings_to_csv(emptyings, filepath):
    """
    Save emptying records to a CSV file

    Parameters:
    emptyings (list): List of Emptying objects
    filepath (str): Path to save the CSV file
    """
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Write header
            writer.writerow([
                "timestamp", "tag_code", "waste_type", "latitude", "longitude", "weight"
            ])

            # Write data
            for emptying in emptyings:
                writer.writerow([
                    emptying.timestamp.strftime("%Y-%m-%d-%H:%M:%S"),
                    emptying.tag_code,
                    emptying.waste_type,
                    emptying.latitude,
                    emptying.longitude,
                    f"{emptying.weight}"
                ])

        return True
    except Exception as e:
        return False 