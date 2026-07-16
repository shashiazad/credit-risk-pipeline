# Phase 1: Project Setup & Standard Practices

In this phase, we establish a production-grade workspace setup. We configure directory layouts, dependency management, virtual environments, logging, and environment variables.

---

## 1. Virtual Environments (Theory)

### What is a Virtual Environment?
In Python, packages installed via `pip` are placed in a global directory on your system by default. 
*   **The Problem:** If Project A requires `pandas==1.5.0` and Project B requires `pandas==2.2.0`, you cannot run both on the same machine without conflicts. This is known as "dependency hell."
*   **The Solution:** A virtual environment is an isolated directory tree that contains its own Python executable and its own copy of libraries. When you activate it, your terminal points to this isolated copy of Python.

---

## 2. Dependency Management: `requirements.txt` vs. `pyproject.toml`

### requirements.txt
A simple, flat text file listing the direct dependencies of a project.
*   **Best Practice:** Always pin versions (e.g., `pandas==2.2.0`, not just `pandas`). If you don't pin versions, running `pip install` next year will install the newest versions, which may contain breaking changes and crash your pipeline.

### pyproject.toml
Introduced in **PEP 518**, `pyproject.toml` is the modern configuration hub for Python projects.
*   Instead of having separate config files for every tool (like `.pytest.ini` for testing, `.flake8` for linting, and `setup.cfg` for packages), `pyproject.toml` consolidates all developer tool settings in one place.

---

## 3. Production-Grade Logging
In data engineering, **never use `print()` statements** to monitor your pipelines. 
### Why `print()` is a Production Anti-Pattern:
1.  **No Severity Levels:** You cannot easily separate regular info from critical failures.
2.  **No Metadata:** Standard `print()` outputs lack timestamps, file names, or line numbers showing where the log originated.
3.  **No Routing:** You cannot easily route logs to external files, Cloud Logging systems (like Google Cloud Logging), or Slack.

### Structured Logging:
Using Python’s built-in `logging` module, we configure a standard formatter that outputs:
`[TIMESTAMP] [LEVEL] [MODULE:LINE]: MESSAGE`
This makes debugging errors in multi-step Airflow runs straightforward.

---

## 4. Configuration and Environment Variables
A production pipeline runs in multiple environments:
1.  **Development (Local):** Small datasets, local files, fake database credentials.
2.  **Staging:** Semi-production environment to test scaling and integration.
3.  **Production:** Real database credentials, automated schedules, cloud-scale compute.

### Rules of Secrets Management:
*   **Rule #1: NEVER commit credentials/secrets to GitHub.** If you commit a GCP service account key or database password, automated scanners will steal it within minutes.
*   **Rule #2: Separate Config from Code.** Use environment variables for variables that change between environments (like credentials or file paths).
*   **Rule #3: Use `.env` files locally and `.env.example` in version control.** Keep a template file with placeholder values committed to Git, and let developer-specific keys reside in a local `.env` file that is listed in `.gitignore`.
