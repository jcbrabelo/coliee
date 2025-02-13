# COLIEE - Case Law data preparation
This repo contains code to aid with the case law data prep.

## Setup
Make sure you are using Python 3.8.

Run:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Google Cloud Setup
The application requires access to case files stored in Google Cloud Storage. Follow these steps:

1. Install Google Cloud CLI:
   - Download and install from: https://cloud.google.com/sdk/docs/install
   - Initialize with: `gcloud init`

2. Configure Authentication:
   - Run: `gcloud auth application-default login`
   - Ensure you're logged in with the correct account (e.g., your_email@ualberta.ca)
   - Important: You must have project-level Owner or Editor permissions on the 'coliee-data' project
   - Note: Bucket-level permissions alone are not sufficient - THIS IS IMPORTANT

3. Verify Setup:
   - Run: `python test_gcloud.py`
   - This should successfully list the contents of the storage bucket

### Troubleshooting

1. Environment Variable Issues:
   - If you see warnings about GOOGLE_APPLICATION_CREDENTIALS, unset this variable (and then re-verify your account):
   ```bash
   # Windows CMD
   set "GOOGLE_APPLICATION_CREDENTIALS="
   
   # PowerShell
   $env:GOOGLE_APPLICATION_CREDENTIALS=""
   
   # Linux/Mac
   unset GOOGLE_APPLICATION_CREDENTIALS
   ```

2. Permission Errors:
   - "Permission denied" or 403 errors usually indicate insufficient permissions
   - Ensure you have project-level (not just bucket-level) permissions
   - Contact the project administrator if you only see bucket-level access

3. Authentication Issues:
   - Make sure you're logged in with your institutional email
   - If you see quota project warnings, run:
   ```bash
   gcloud auth application-default set-quota-project coliee-data
   ```

4. Common Gotchas:
   - The GUI tools expect coliee.db to be in your working directory
   - Case files are fetched from Google Cloud, not stored locally
   - Task 1 and Task 2 have different preparation workflows
   - Always check you're using Python 3.8 as newer versions may have compatibility issues, I recommend using an Anaconda environment to install Python 3.8.

### Database Setup
The application uses a SQLite database (coliee.db) for metadata and citations:
- Ensure coliee.db is present in your working directory
- The database contains case metadata and citations but not the full case texts
- Full case texts are stored in Google Cloud Storage

## Task 1 - Retrieval
For the retrieval task, the process is fully automatic: we need to run the code that grabs a sample still not used from the dataset, removes the direct citations present in the case contents and it the cases + labels to the test dataset.

## Task 2 - Entailment
For the entailment task, we need to perform a few manual steps. There is a utility UI to help with this process.
Just run task2_gui.py and it will load a "base case" (a case that cites a precedent) on the left panel, and a cited case (the aforementioned precedent) on the right panel. 
Then you need to find a fragment in the base case that is entailed by one or more paragraphs from the precedent, which requires quite a bit of a manual analysis. 
A good strategy to follow when looking for those entailment relationships is to look for "pinpoint citations" (ie, citations directly mentioning the paragraph number(s)) in the base case.
The UI will highlight in red mentions to paragraphs in the base case, so that you can quickly identify those instances and check in the precedent if the cited paragraphs do hold an entailment relationship with some fragment in the base case (which will be around that paragraph citation).
If you do find that relationship, select the entailed fragment and hit the "d" key. If there is information in the base case that can give away that entailment relationship (for example, the citation + paragraph number) you can "block" it by selecting that fragment and hitting the "b" key.
Then, on the precedent case, you need to select the paragraph(s) that entail that fragment in the base case. Just click on a paragraph, which will turn red, and then click on "e".

In each COLIEE edition, we use as training set all the cases used in the previous editions. The test set is usually comprised of 100 new cases labelled as detailed above.

# IMPORTANT

## File Overview

### Core Utilities
- `case_files_utils.py`: Handles fetching and processing case files from Google Cloud Storage
- `dbutils.py`: Database operations for case metadata and citations using SQLite
- `gui_commons.py`: Common GUI utilities shared between Task 1 and Task 2 interfaces

### Task-Specific Tools
- `task1_gui.py`: GUI tool for Task 1 data preparation and labeling
- `task2_gui.py`: GUI tool for Task 2 entailment annotation
- `task1_autoprep.py`: Automated preparation utilities for Task 1 data
- `prepare_data.py`: Core data preparation functions for both tasks
- `package_data.py`: Functions to package and organize prepared data

### Data Management
- `fetch_data.py`: Functions to fetch case data from external sources
- `export_data.py`: Tools for exporting prepared data in required formats
- `validate_data.py`: Validation utilities for prepared datasets
- `check_uniqueness.py`: Tools to check and ensure data uniqueness
- `inspect_data.py`: Utilities for data inspection and analysis

### Testing and Setup
- `test_gcloud.py`: Test Google Cloud Storage connectivity and permissions
- `test_sqlite.py`: Test SQLite database connectivity
- `cert_fix.py`: SSL certificate fix for NLTK downloads

### Analysis
- `stat_analysis.py`: Statistical analysis tools for prepared data

### Support Files
- `requirements.txt`: Python package dependencies
- `extra_dict.txt`: Additional dictionary terms for text processing
- `coliee.db`: SQLite database containing case metadata and citations

Note: Some files may contain hardcoded paths that need to be updated for your environment. Always check path variables before running tools.
