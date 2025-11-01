#!/bin/bash
# Railway startup script for Streamlit
export STREAMLIT_SERVER_PORT=${PORT:-8501}
streamlit run dashboard_main.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true

