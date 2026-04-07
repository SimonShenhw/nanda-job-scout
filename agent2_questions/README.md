# Agent 2 - Interview Questions
## Workflow.py Architecture and Components
### Data Structures
Workflow.py utilizes a set of data structures designed to efficiently handle data related to job candidates and resumes. Key structures include:

- **Candidate Class**: Stores detailed information about the candidate including their name, contact information, and a list of their resumes.
- **Resume Class**: Represents individual resumes, encapsulating details such as content, metadata, and parsing results.

### Resume Parsing
The resume parsing component is responsible for extracting relevant information from various resume formats. This process includes:

- **Text Extraction**: Libraries such as `pdfminer` or `PyMuPDF` are utilized to pull text from PDF and Word formats.
- **Data Normalization**: Extracted data is normalized and structured into candidate objects to ensure consistency.
- **Keyword Matching**: The parser identifies key skills and experience, leveraging Natural Language Processing (NLP) techniques.

### Core Agent Logic
The core agent logic is the heart of workflow.py, responsible for:

- **Decision Making**: Based on the parsed data, the agent decides how to score or rank candidates for specific roles.
- **Integration with External Services**: It interacts with job boards and applicant tracking systems to pull in real-time data.
- **Feedback Loop**: Gathers feedback on candidate performance and adjusts future candidate scoring mechanisms accordingly.

### FastAPI Deployment
This component deals with exposing the agent's functionalities via a RESTful API using FastAPI:

- **Endpoints**: Provides endpoints for submitting resumes, retrieving candidate scores, and fetching overall statistics.
- **Asynchronous Processing**: Leveraging FastAPI's async capabilities for efficient handling of multiple requests concurrently.
- **Validation**: Input validation is rigorously enforced to maintain data integrity.

### Health Checks
The health check module ensures that the various components are functioning as expected:

- **Endpoint Monitoring**: Regular pings to critical API endpoints to ensure they are responsive.
- **Resource Usage Tracking**: Monitors CPU and memory usage to predict and handle potential issues before they affect service availability.
- **Error Logging**: Captures errors and exceptions with detailed logging for further analysis.
