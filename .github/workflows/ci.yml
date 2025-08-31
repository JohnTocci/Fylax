name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.8', '3.9', '3.10', '3.11', '3.12']

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Lint with flake8
      run: |
        flake8 src/fylax/ --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 src/fylax/ --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics

    - name: Format check with Black
      run: |
        black --check src/fylax/

    - name: Import sort check with isort
      run: |
        isort --check-only --diff src/fylax/

    - name: Type check with mypy
      run: |
        mypy src/fylax/ --ignore-missing-imports

    - name: Test with pytest
      run: |
        pytest tests/ -v

    - name: Test application imports
      run: |
        # --- CORRECTED IMPORT TEST ---
        python -c "from fylax import main, gui; print('All imports successful')"

  build:
    runs-on: windows-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller

    - name: Build executable
      run: |
        pyinstaller --noconfirm --windowed --onefile --name Fylax --icon assets/app.ico --add-data "assets;assets" src/fylax/gui.py

    - name: Upload executable
      uses: actions/upload-artifact@v4
      with:
        name: Fylax-Windows-Executable
        path: dist/Fylax.exe
