# gas-station-finder


Data: GasStationfinder -> stations_california_clean_5_columns.csv

UI:gas_stations (xcode) (make sure update your ip.address to your own backend sever at APIclient.swift)

# backend:

1. Set up virtual environment

   cd apisetting
   
   python -m venv .venv
   
3. Activate virtual environment
   
   Windows (PowerShell):
   
   .\.venv\Scripts\Activate.ps1
   
   Mac/Linux:
   
   source .venv/bin/activate
3. Install dependencies
   
    pip install fastapi uvicorn
    
    (OR if requirements.txt exists)
    
    pip install -r requirements.txt
5. Run the server
   
    cd ..
   
    python -m uvicorn api_main:app --app-dir apisetting --host 0.0.0.0 --port 8000 --reload


Data collector 
 
Web scrawler refer https://github.com/unclecode/crawl4ai for installation

    python scripts\batch_crawler.py
    
    python srcipts\batch\parse_gasbuddy.py
    
   data will store at stations_all.csv
