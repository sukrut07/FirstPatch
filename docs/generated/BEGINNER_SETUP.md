# 🛠️ Beginner Development Environment Setup: octocat/Hello-World

Follow these steps to set up a clean, reproducible development environment on your machine:

## Step 1: Fork & Clone
```bash
# 1. Fork the repo on GitHub to your username
# 2. Clone your personal fork locally:
git clone https://github.com/YOUR_USERNAME/Hello-World.git
cd Hello-World

# 3. Add the official upstream remote:
git remote add upstream https://github.com/octocat/Hello-World.git
```

## Step 2: Create a Working Branch
```bash
git checkout -b my-first-contribution
```

## Step 3: Install Dependencies
```bash
# Create and activate a clean virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies:
pip install -e .
pip install pytest
```

## Step 4: Run the Test Suite
```bash
pytest
```
*Expected Result:* All tests should pass before making any code modifications.
