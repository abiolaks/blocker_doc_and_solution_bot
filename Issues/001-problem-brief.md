## Issue Brief: Building a RAG Chatbot for Team Blocker Resolution

### 1. Background

Team members often experience repeated technical blockers such as errors, bugs, failed configurations, deployment issues, environment problems, and tool-related challenges. In many cases, one team member solves a problem, but the solution is not properly documented or made easily accessible to others.

As a result, other team members may spend unnecessary time searching online, asking colleagues, or repeating the same troubleshooting steps. This leads to reduced productivity, knowledge loss, and inconsistent documentation.

To solve this, the organization can build a Chatbot that allows users to search for previously logged blockers and also document new blockers when they are not found in the knowledge base.

---



The current blocker resolution process is mostly manual and scattered across multiple channels such as chats, notebooks, GitHub issues, emails, and personal notes.

Key issues include:

 Blockers are not stored in one central location.
 Resolved issues are not always documented.
Team members repeatedly solve the same problems.
 New team members struggle to learn from past issues.
 Existing documentation is difficult to search.
 There is no intelligent system to recommend solutions based on past blocker logs.

---

Proposed Solution

The proposed solution is to build a RAG chatbot that serves as a central knowledge assistant for the team.

The chatbot will allow users to:

 Search for previously logged blockers.
 Retrieve accurate solutions from the knowledge base.
 View similar issues and how they were resolved.
 Log new blockers when no existing solution is found.
Document the cause, troubleshooting steps, and final resolution.
 Continuously expand the knowledge base over time.



  Objectives

The main objectives of the solution are to:

 Reduce time spent resolving repeated blockers.
 Centralize team knowledge and troubleshooting history.
 Improve documentation culture with minimal manual effort.
 Help new team members learn from previous project experiences.
 Enable faster and more accurate issue resolution.
 Build a searchable and intelligent technical support knowledge base.

---

### 5. How the RAG Chatbot Will Work

When a user encounters a blocker, they will type the issue into the chatbot.

Example:

> “I am getting an Azure Blob Storage connection error when trying to upload files from Python.”

The chatbot will then search the knowledge base for similar previously logged blockers.

If a similar blocker exists, the chatbot will return:

* A summary of the issue.
* The likely cause.
* The solution that worked previously.
* Step-by-step resolution instructions.
* Related blockers or documents.

If no matching blocker exists, the chatbot will respond that it could not find a reliable answer and prompt the user to document the new blocker.

---

### 6. New Blocker Documentation Flow

When a blocker does not exist in the knowledge base, the chatbot should guide the user through a structured logging process.

The user may be asked to provide:

* Blocker title
* Project name
* Tool or technology involved
* Error message
* Description of what they were trying to do
* Steps already attempted
* Root cause, if known
* Final resolution, once solved
* Links to supporting files, screenshots, tickets, or repositories
* Tags such as Azure, Python, API, deployment, database, authentication, etc.

Once submitted, the blocker becomes part of the knowledge base and can be retrieved by other users in the future.

---

### 7. Core Features

The chatbot should include the following features:

#### 1. Blocker Search

Users can describe their issue in natural language, and the chatbot retrieves the most relevant previously logged blockers.

#### 2. Similar Issue Recommendation

The system should return not only exact matches but also similar blockers based on meaning and context.

#### 3. Guided Blocker Logging

If no answer exists, the chatbot should guide the user to document the new blocker in a structured way.

#### 4. Knowledge Base Update

New blockers and resolutions should automatically be added to the knowledge base after validation.

#### 5. Tagging and Categorization

Blockers should be tagged by project, tool, error type, technology, severity, and status.

#### 6. Resolution Tracking

Each blocker should have a status such as:

* Open
* In Progress
* Resolved
* Reopened

#### 7. Source-Based Answers

The chatbot should answer only from the knowledge base and show the source of the retrieved solution.

#### 8. Feedback Mechanism

Users should be able to rate whether the answer was helpful or not.

#### 9. Admin Review

A team lead or admin can review newly submitted blockers before they become official knowledge base entries.

#### 10. Analytics Dashboard

The system can track frequent blockers, unresolved issues, common technologies affected, and average resolution time.

---

### 8. Recommended Data to Capture

Each blocker entry should contain:

| Field              | Description                                   |
| ------------------ | --------------------------------------------- |
| Blocker ID         | Unique identifier for each blocker            |
| Title              | Short name of the issue                       |
| Description        | Detailed explanation of the blocker           |
| Error Message      | Exact error shown                             |
| Project            | Project where the blocker occurred            |
| Technology         | Tool, platform, or framework involved         |
| Environment        | Local, Dev, Test, Production, Cloud, etc.     |
| Steps to Reproduce | How the issue occurred                        |
| Attempted Fixes    | Solutions already tried                       |
| Root Cause         | Main reason the blocker happened              |
| Final Resolution   | Confirmed solution                            |
| Date Logged        | When the blocker was created                  |
| Logged By          | User who submitted the blocker                |
| Status             | Open, In Progress, Resolved                   |
| Tags               | Keywords for search and filtering             |
| Supporting Links   | Screenshots, tickets, GitHub links, documents |

---

### 9. Expected Benefits

The solution will provide several business and operational benefits:

* Faster issue resolution.
* Reduced dependency on specific individuals.
* Improved knowledge sharing across the team.
* Better onboarding for new team members.
* Reduced repeated troubleshooting effort.
* Improved documentation quality.
* Centralized technical support knowledge base.
* Better visibility into recurring blockers.
* Data-driven insight into team pain points.
* Continuous improvement of internal processes.

---

### 10. High-Level Architecture

The solution will consist of the following components:

1. **User Interface**
   A chatbot interface where team members can search for blockers or log new ones.

2. **Knowledge Base**
   A structured storage system for blocker records, resolutions, documents, and metadata.

3. **Embedding Model**
   Converts blocker content into numerical representations for semantic search.

4. **Vector Database**
   Stores embeddings and enables similarity search.

5. **RAG Pipeline**
   Retrieves relevant blocker records and passes them to the language model.

6. **Language Model**
   Generates clear responses based on retrieved knowledge base content.

7. **Submission Workflow**
   Allows users to add new blockers and update unresolved ones.

8. **Admin Review Layer**
   Ensures new knowledge base entries are accurate before becoming searchable.

---

### 11. Suggested Technology Stack

A cost-optimized stack could include:

| Component         | Suggested Tool                                       |
| ----------------- | ---------------------------------------------------- |
| Chatbot Interface | Microsoft Teams Bot, Web App, or Streamlit           |
| Backend           | Python FastAPI                                       |
| Database          | PostgreSQL or Azure SQL                              |
| Vector Database   | PostgreSQL with pgvector, Azure AI Search, or Qdrant |
| Embedding Model   | Azure OpenAI Embeddings or open-source embeddings    |
| LLM               | Azure OpenAI GPT model                               |
| Storage           | Azure Blob Storage                                   |
| Authentication    | Microsoft Entra ID                                   |
| Deployment        | Azure App Service or Azure Container Apps            |
| Monitoring        | Azure Monitor / Application Insights                 |

---

### 12. Success Metrics

The project can be measured using the following indicators:

* Number of blockers logged.
* Number of successful blocker searches.
* Reduction in repeated blocker questions.
* Average time to resolution.
* Percentage of resolved blockers documented.
* User feedback rating on chatbot responses.
* Number of new knowledge base entries created.
* Reduction in dependency on senior team members.

---

### 13. Risks and Considerations

Possible risks include:

* Poorly documented blockers reducing answer quality.
* Duplicate entries in the knowledge base.
* Users failing to update blockers after resolution.
* Incorrect chatbot responses if retrieval is weak.
* Sensitive project information being exposed.
* Lack of adoption if the workflow is too complex.

These risks can be reduced by using structured templates, admin review, role-based access, clear tagging, and regular knowledge base cleanup.

---

### 14. Conclusion

A RAG chatbot for blocker resolution will help the team capture, retrieve, and reuse technical knowledge more effectively. Instead of solving the same problems repeatedly, users can quickly access previous solutions and document new issues as they occur.

Over time, the chatbot becomes a living knowledge base that improves team productivity, supports faster problem-solving, and strengthens organizational learning.
