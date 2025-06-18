# Github Repo Analyzer

An interactive web application built with Streamlit that provides in-depth analysis of GitHub repositories. Visualize commit activity, track contributor statistics, and gain insights into repository development patterns. Perfect for open-source maintainers, team leads, and developers looking to understand project dynamics through beautiful, interactive charts and metrics.

## Setup

### Option 1: Using Docker (Recommended)


1. Build the Docker image:
```bash
docker build -t github-repo-analyzer .
```

2. Run the container:
```bash
docker run -p 8501:8501 github-repo-analyzer
```

The application will be available at http://localhost:8501

### Option 2: Python Virtual Environment


1. Create and activate virtual environment:
```bash
python -m venv .myenv
\.myenv\Scripts\Activate.ps1
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app.py
```
The application will be available at http://localhost:8501