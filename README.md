# gas-station-finder


Data: GasStationfinder -> stations_california_clean_5_columns.csv

UI:gas_stations (xcode) (make sure update your ip.address to your own backend sever at APIclient.swift)

backend:GasStaionfinder->  run command line:  cd .\gas-station-finder
  .\apisetting\.venv\Scripts\Activate.ps1
  python -m uvicorn api_main:app --app-dir .\apisetting\.venv --host 0.0.0.0 --port 8000 --reload


Data collector 
Web scrawler refer https://github.com/unclecode/crawl4ai for installation
    then python scripts\batch_crawler.py
    python srcipts\batch\parse_gasbuddy.py
    data will store at stations_all.csv
