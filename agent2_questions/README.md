# How It Works

## Interview Prep Agent Workflow - 8-Step Process Flow
1. **Resume Parsing**: The agent receives the user's resume in various formats (PDF, DOCX, TXT).
2. **Job Interaction**: The user interacts with the job database to identify relevant job details.
3. **Job JSON Parsing**: Extracts necessary information from job postings to prepare for interview questions.
4. **Concurrent LLM Processing**: Utilizes `asyncio.gather` to process multiple requests concurrently, improving efficiency.
5. **Question Generation with Retries**: Generates interview questions based on the parsed information and retries in case of failure.
6. **Result Aggregation**: Compiles all the generated questions and relevant responses into a single format.
7. **Final Response Output**: Presents the aggregated results to the user in a clear manner.

## Detailed ASCII Data Flow Diagram
```
        +------------------+
        |  User's Resume   |
        +--------+---------+
                 |
       (Resume Parsing)
                 |
        +--------v---------+
        |  Job JSON Parser  |
        +--------+---------+
                 |
      (Job Interaction)
                 |
        +--------v---------+
        | Concurrent LLM    |
        |   Processing      |
        +--------+---------+
                 |
   (Question Generation with Retries)
                 |
        +--------v---------+
        |  Result Aggregator |
        +--------+---------+
                 |
         (Final Response Output)
                 |
        +--------v---------+
        |  User Output      |
        +------------------+
```  

## Key Features
- **Multi-Format Support**: Handles various resume formats including PDF, DOCX, and TXT.
- **Concurrent Processing**: Efficiently processes multiple requests using `asyncio.gather`.
- **Retry Logic**: Implements retry mechanisms for question generation to ensure reliability.
- **Fault Tolerance**: Built-in error handling to manage unexpected issues during processing.

# Workflow.py Architecture and Components

## 1. Data Structures
- **JobJD**: Contains job description details.
- **InterviewQuestion**: Represents individual interview questions.
- **InterviewPrepResponse**: Holds responses to generated questions.
- **BatchInterviewPrepResponse**: Manages responses for batches of questions.

## 2. Resume Parsing
- **PDF, DOCX, TXT Parsers**: Each parser extracts text and relevant features from the respective file formats.

## 3. Core Agent Logic
- **Job-Level Processing**: Handles individual job processing logic.
- **Batch Orchestration**: Manages processing of multiple jobs at once.
- **LLM Integration**: Interfaces with language model APIs for question generation.
- **Prompt Engineering**: Designs prompts for the language model to optimize response quality.

## 4. FastAPI Deployment
- **Endpoints**: Defines the API endpoints for the agent's functionality.
- **Validation**: Ensures input data is formatted correctly before processing.
- **Error Handling**: Handles errors gracefully during API calls.

## 5. Health Checks
Regular status checks to ensure the agent is functioning correctly.

## 6. NANDA Ecosystem Integration
Integration points with other components of the NANDA ecosystem.

## 7. Technical Stack
- **Python**: Primary programming language.
- **FastAPI**: Framework for building APIs.
- **Asyncio**: For concurrent processing.

## 8. Setup & Environment
- **Requirements**: List of dependencies required to run the agent.
- **Running Instructions**: Step-by-step guide on how to deploy and run the agent.
