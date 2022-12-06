# seeh3

FastAPI app to generate h3 grids in geojson.

Part of the iSamples project.

To use:

1. Create a virtual environment
2. poetry install
3. `cd app`
4. `uvicorn main:app --reload`
5. In another terminal, `ssh -L8984:localhost:8983 mars`
6. Visit http://localhost:8000 or http://localhost:8000/3
