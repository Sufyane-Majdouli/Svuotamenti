# Svuotamenti - Emptying Log Interpreter Web Application

Svuotamenti is a web-based application for visualizing and analyzing waste collection data. It allows users to upload CSV files containing emptying records or download them from FTP servers, and then displays the emptying locations on an interactive map.

## Features

- Upload local CSV files with emptying data
- Connect to FTP servers to browse and download files
- Visualize emptying locations on an interactive map
- Display statistics about emptying records
- Configurable FTP connection settings

## Installation

1. Clone this repository or download the source code
2. Create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

1. Ensure your virtual environment is activated
2. Run the application:
   ```
   python run.py
   ```
3. Open your web browser and navigate to `http://127.0.0.1:5000`

## CSV File Format

The application expects CSV files with the following columns:
1. **Timestamp**: Date and time of the emptying (various formats supported)
2. **Tag Code**: Identifier code for the waste container
3. **Waste Type**: Type of waste (e.g., plastic, paper, glass)
4. **Latitude**: GPS latitude coordinate
5. **Longitude**: GPS longitude coordinate
6. **Weight**: Weight of the collected waste (optional)

Example:
```
timestamp,tag_code,waste_type,latitude,longitude,weight
2023-05-01-10:30:45,BIN12345,plastic,45.4654,9.1859,12.5
```

## License

This project is licensed under the MIT License.

## Acknowledgements

This web application is based on the desktop version created using PyQt5 and Folium. 