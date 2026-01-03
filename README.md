# **`README.md`**

# FedSight AI: Multi-Agent System Architecture for Federal Funds Target Rate Prediction

<!-- PROJECT SHIELDS -->
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![arXiv](https://img.shields.io/badge/arXiv-2512.15728v1-b31b1b.svg)](https://arxiv.org/abs/2512.15728v1)
[![Journal](https://img.shields.io/badge/Journal-ArXiv%20Preprint-003366)](https://arxiv.org/abs/2512.15728v1)
[![Workshop](https://img.shields.io/badge/Workshop-NeurIPS%202025%20GenAI%20in%20Finance-purple)](https://neurips.cc/)
[![Year](https://img.shields.io/badge/Year-2025-purple)](https://github.com/chirindaopensource/multi_agent_system_architecture_for_federal_funds_target_rate_prediction)
[![Discipline](https://img.shields.io/badge/Discipline-Computational%20Finance%20%7C%20Macroeconomics-00529B)](https://github.com/chirindaopensource/multi_agent_system_architecture_for_federal_funds_target_rate_prediction)
[![Data Sources](https://img.shields.io/badge/Data-FRED%20(St.%20Louis%20Fed)-lightgrey)](https://fred.stlouisfed.org/)
[![Data Sources](https://img.shields.io/badge/Data-Federal%20Reserve%20Board-lightgrey)](https://www.federalreserve.gov/)
[![Core Method](https://img.shields.io/badge/Method-Multi--Agent%20Simulation-orange)](https://github.com/chirindaopensource/multi_agent_system_architecture_for_federal_funds_target_rate_prediction)
[![Analysis](https://img.shields.io/badge/Analysis-Chain--of--Draft%20Reasoning-red)](https://github.com/chirindaopensource/multi_agent_system_architecture_for_federal_funds_target_rate_prediction)
[![Validation](https://img.shields.io/badge/Validation-In--Context%20Learning-green)](https://github.com/chirindaopensource/multi_agent_system_architecture_for_federal_funds_target_rate_prediction)
[![Robustness](https://img.shields.io/badge/Robustness-Backtesting%20(2023--2024)-yellow)](https://github.com/chirindaopensource/multi_agent_system_architecture_for_federal_funds_target_rate_prediction)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type Checking: mypy](https://img.shields.io/badge/type%20checking-mypy-blue)](http://mypy-lang.org/)
[![NumPy](https://img.shields.io/badge/numpy-%23013243.svg?style=flat&logo=numpy&logoColor=white)](https://numpy.org/)
[![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=flat&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-%23F7931E.svg?style=flat&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-%23412991.svg?style=flat&logo=openai&logoColor=white)](https://openai.com/)
[![Jupyter](https://img.shields.io/badge/Jupyter-%23F37626.svg?style=flat&logo=Jupyter&logoColor=white)](https://jupyter.org/)

**Repository:** `https://github.com/chirindaopensource/multi_agent_system_architecture_for_federal_funds_target_rate_prediction`

**Owner:** 2025 Craig Chirinda (Open Source Projects)

This repository contains an **independent**, professional-grade Python implementation of the research methodology from the 2025 paper entitled **"FedSight AI: Multi-Agent System Architecture for Federal Funds Target Rate Prediction"** by:

*   **Yuhan Hou** (Duke University)
*   **Tianji Rao** (Duke University; BNY AI Hub)
*   **Jeremy Matthew Tan** (Duke University)
*   **Adler Viton** (Duke University; BNY AI Hub)
*   **Xiyue Zhang** (Duke University)
*   **David Ye** (Duke University)
*   **Abhishek Kodi** (BNY AI Hub)
*   **Sanjana Dulam** (BNY AI Hub)
*   **Aditya Paul** (BNY AI Hub)
*   **YiKai Feng** (BNY AI Hub)

The project provides a complete, end-to-end computational framework for replicating the paper's findings. It delivers a modular, auditable, and extensible pipeline that executes the entire research workflow: from the ingestion and cleansing of macroeconomic indicators and unstructured narratives to the rigorous simulation of FOMC deliberations via Large Language Models (LLMs), culminating in accurate interest rate forecasts.

## Table of Contents

- [Introduction](#introduction)
- [Theoretical Background](#theoretical-background)
- [Features](#features)
- [Methodology Implemented](#methodology-implemented)
- [Core Components (Notebook Structure)](#core-components-notebook-structure)
- [Key Callable: `execute_full_study_lifecycle`](#key-callable-execute_full_study_lifecycle)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Input Data Structure](#input-data-structure)
- [Usage](#usage)
- [Output Structure](#output-structure)
- [Project Structure](#project-structure)
- [Customization](#customization)
- [Contributing](#contributing)
- [Recommended Extensions](#recommended-extensions)
- [License](#license)
- [Citation](#citation)
- [Acknowledgments](#acknowledgments)

## Introduction

This project provides a Python implementation of the analytical framework presented in Hou et al. (2025). The core of this repository is the iPython Notebook `multi_agent_system_architecture_for_federal_funds_target_rate_prediction_draft.ipynb`, which contains a comprehensive suite of functions to replicate the paper's findings. The pipeline is designed to simulate the deliberative institutional process of the Federal Open Market Committee (FOMC), moving beyond black-box forecasting to provide interpretable, reasoning-based predictions.

The paper addresses the challenge of forecasting monetary policy in a complex economic environment where decisions reflect diverse philosophies and regional concerns. This codebase operationalizes the paper's framework, allowing users to:
-   Rigorously validate and manage the entire experimental configuration via a single `config.yaml` file.
-   Cleanse and normalize structured macroeconomic data (e.g., inflation, employment) and unstructured narratives (e.g., Beige Book, Dot Plots).
-   Construct canonical "meeting packets" that strictly enforce information cutoffs to prevent look-ahead bias.
-   Simulate FOMC deliberations using a multi-agent system (MAS) with distinct roles (Analyst, Economist, Members).
-   Implement advanced reasoning protocols including Chain-of-Draft (CoD) and In-Context Learning (ICL).
-   Evaluate performance using rigorous metrics such as Total Accuracy, Agent Accuracy, Voting Stability, and Semantic Similarity.

## Theoretical Background

The implemented methods combine techniques from Multi-Agent Systems, Natural Language Processing, and Financial Economics.

**1. Multi-Agent System (MAS) Simulation:**
The FOMC decision-making process is modeled as a collaborative workflow among heterogeneous agents.
-   **Analyst:** Interprets market signals (Fed Funds Futures).
-   **Economist:** Formulates policy options based on macro data.
-   **Members:** Deliberate and vote based on their specific archetypes (Regional Pragmatists, Academic Balancers, Central Policymakers).

**2. Chain-of-Draft (CoD) Reasoning:**
To improve reasoning quality and reduce hallucinations, member agents operate under a CoD protocol. This enforces concise, multi-stage reasoning steps (e.g., $\le 30$ words per step) followed by a revision phase, ensuring that the final vote is grounded in a logical progression.

**3. In-Context Learning (ICL):**
Agents are "trained" by simulating historical meetings (e.g., 2019, 2022). They vote, receive the ground truth outcome, and generate "lessons learned" which are stored in a long-term memory vector store. These lessons are retrieved and injected into the context during inference to guide future decisions.

**4. Unsupervised Clustering of Archetypes:**
Historical FOMC participants are clustered using K-Means based on features like hawkishness, regional affiliation, and policy focus. The resulting centroids define the "System Personas" adopted by the simulated member agents.

Below is a diagram which summarizes the proposed approach:

<div align="center">
  <img src="https://github.com/chirindaopensource/multi_agent_system_architecture_for_federal_funds_target_rate_prediction/blob/main/multi_agent_system_architecture_for_federal_funds_target_rate_prediction_summary_three.png" alt="FedSight AI Architecture Summary" width="100%">
</div>

## Features

The provided iPython Notebook (`multi_agent_system_architecture_for_federal_funds_target_rate_prediction_draft.ipynb`) implements the full research pipeline, including:

-   **Modular, Multi-Task Architecture:** The pipeline is decomposed into 30 distinct, modular tasks, each with its own orchestrator function.
-   **Configuration-Driven Design:** All study parameters (LLM settings, simulation rules, data schemas) are managed in an external `config.yaml` file.
-   **Rigorous Data Validation:** A multi-stage validation process checks schema integrity, type coercion feasibility, and temporal alignment.
-   **Deterministic Execution:** Enforces reproducibility through seed control, deterministic sorting, and rigorous logging of all stochastic outputs.
-   **Comprehensive Evaluation:** Computes a suite of metrics including Accuracy (93.75% reported), Stability (93.33% reported), and Semantic Similarity.
-   **Reproducible Artifacts:** Generates structured dictionaries, serializable outputs, and cryptographic manifests for every intermediate result.

## Methodology Implemented

The core analytical steps directly implement the methodology from the paper:

1.  **Validation & Cleansing (Tasks 1-5):** Ingests raw macro and narrative data, validates schemas, enforces the "two-days-prior" cutoff, and normalizes text.
2.  **Packet Construction (Tasks 6-8):** Joins data into canonical meeting packets, verbalizes Dot Plots, and bundles context for agents.
3.  **Agent Engineering (Tasks 9-12):** Clusters participants to define archetypes, configures the LLM client with retry logic, and defines the CrewAI architecture.
4.  **Simulation Execution (Tasks 13-18):** Runs the multi-agent workflow across three variants (Baseline, ICL, CoD), enforcing protocols like CoD constraints and ICL memory injection.
5.  **Storage & Provenance (Task 19):** Persists simulation artifacts to a SQLite database with full provenance tracking.
6.  **Metric Computation (Tasks 21-27):** Calculates Total Accuracy, Agent Accuracy, Voting Stability, Semantic Similarity, Average Tokens, and MAE.
7.  **Reporting & Archiving (Tasks 28-30):** Generates the final results table, packages artifacts for reproducibility, and signs off on the study completion.

## Core Components (Notebook Structure)

The notebook is structured as a logical pipeline with modular orchestrator functions for each of the 30 major tasks. All functions are self-contained, fully documented with type hints and docstrings, and designed for professional-grade execution.

## Key Callable: `execute_full_study_lifecycle`

The project is designed around a single, top-level user-facing interface function:

-   **`execute_full_study_lifecycle`:** This master orchestrator function runs the entire automated research pipeline from end-to-end. A single call to this function reproduces the entire computational portion of the project, managing data flow between cleansing, simulation, and evaluation modules.

## Prerequisites

-   Python 3.9+
-   Core dependencies: `pandas`, `numpy`, `scikit-learn`, `openai`, `crewai`, `pyyaml`, `nest_asyncio`.

## Installation

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/chirindaopensource/multi_agent_system_architecture_for_federal_funds_target_rate_prediction.git
    cd multi_agent_system_architecture_for_federal_funds_target_rate_prediction
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Python dependencies:**
    ```sh
    pip install pandas numpy scikit-learn openai crewai pyyaml nest_asyncio
    ```

## Input Data Structure

The pipeline requires five primary DataFrames:
1.  **`df_macro_raw`**: Structured macroeconomic indicators (Inflation, Employment, Yields).
2.  **`df_unstructured_raw`**: Narrative texts (Beige Book, FedWatch) and Dot Plot distributions.
3.  **`df_participants_raw`**: Metadata for historical FOMC participants (for clustering).
4.  **`df_meeting_outcomes`**: Ground truth decisions (FFTR change in bps).
5.  **`df_fomc_statements_actual`**: Official FOMC statements for semantic comparison.

## Usage

The notebook provides a complete, step-by-step guide. The primary workflow is to execute the final cell, which demonstrates how to use the top-level `execute_full_study_lifecycle` orchestrator:

```python
# Final cell of the notebook

# This block serves as the main entry point for the entire project.
if __name__ == '__main__':
    # 1. Load the master configuration from the YAML file.
    import yaml
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # 2. Load raw datasets (Example using synthetic generator provided in the notebook)
    # In production, load from CSV/Parquet: pd.read_csv(...)
    (df_macro, df_unstruct, df_parts, df_outcomes, df_statements) = generate_synthetic_datasets()
    
    # 3. Execute the entire replication study.
    results = execute_full_study_lifecycle(
        df_macro_raw=df_macro,
        df_unstructured_raw=df_unstruct,
        df_participants_raw=df_parts,
        df_meeting_outcomes=df_outcomes,
        df_fomc_statements_actual=df_statements,
        config=config,
        output_dir="fedsight_reproduction_output"
    )
    
    # 4. Access results
    if results['final_status']['final_verdict'] == 'SUCCESS':
        print(results['pipeline_results']['reports']['formatted_results'])
```

## Output Structure

The pipeline returns a dictionary containing:
-   **`pipeline_results`**: A `FedSightResults` object with all artifacts, metrics, and the execution ledger.
-   **`reproducibility_paths`**: A dictionary mapping component names to their file paths in the reproduction package.
-   **`final_status`**: A completion record with timestamps and verification verdicts.

## Project Structure

```
multi_agent_system_architecture_for_federal_funds_target_rate_prediction/
│
├── multi_agent_system_architecture_for_federal_funds_target_rate_prediction_draft.ipynb  # Main implementation notebook
├── config.yaml                                                                           # Master configuration file
├── requirements.txt                                                                      # Python package dependencies
│
├── LICENSE                                                                               # MIT Project License File
└── README.md                                                                             # This file
```

## Customization

The pipeline is highly customizable via the `config.yaml` file. Users can modify study parameters such as:
-   **LLM Settings:** `model_name`, `temperature`, `max_tokens`.
-   **Simulation:** `runs_per_meeting`, `vote_aggregation_rule`.
-   **Preprocessing:** `cod_max_words_per_step`, `dot_plot_missing_policy`.
-   **ICL:** `training_meetings`, `memory_retrieval_policy`.

## Contributing

Contributions are welcome. Please fork the repository, create a feature branch, and submit a pull request with a clear description of your changes. Adherence to PEP 8, type hinting, and comprehensive docstrings is required.

## Recommended Extensions

Future extensions could include:
-   **Real-Time Data Integration:** Connecting the pipeline to live FRED and FedWatch APIs for real-time forecasting.
-   **Agent Heterogeneity:** Expanding the number of archetypes or introducing dynamic persona evolution.
-   **Multimodal Inputs:** Incorporating visual data (charts) directly into the agent context.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Citation

If you use this code or the methodology in your research, please cite the original paper:

```bibtex
@article{hou2025fedsight,
  title={FedSight AI: Multi-Agent System Architecture for Federal Funds Target Rate Prediction},
  author={Hou, Yuhan and Rao, Tianji and Tan, Jeremy Matthew and Viton, Adler and Zhang, Xiyue and Ye, David and Kodi, Abhishek and Dulam, Sanjana and Paul, Aditya and Feng, YiKai},
  journal={arXiv preprint arXiv:2512.15728v1},
  year={2025}
}
```

For the implementation itself, you may cite this repository:
```
Chirinda, C. (2025). FedSight AI Replication Pipeline: An Open Source Implementation.
GitHub repository: https://github.com/chirindaopensource/multi_agent_system_architecture_for_federal_funds_target_rate_prediction
```

## Acknowledgments

-   Credit to **Yuhan Hou, Tianji Rao, Jeremy Matthew Tan, Adler Viton, Xiyue Zhang, David Ye, Abhishek Kodi, Sanjana Dulam, Aditya Paul, and YiKai Feng** for the foundational research that forms the entire basis for this computational replication.
-   This project is built upon the exceptional tools provided by the open-source community. Sincere thanks to the developers of the scientific Python ecosystem, including **Pandas, NumPy, Scikit-Learn, OpenAI, and CrewAI**.

--

*This README was generated based on the structure and content of the `multi_agent_system_architecture_for_federal_funds_target_rate_prediction_draft.ipynb` notebook and follows best practices for research software documentation.*
