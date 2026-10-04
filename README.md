# 🌱 Bloom — Watch Your Story Grow

**Bloom** is an AI-assisted creative writing application developed as my **Bachelor's Degree Project in Computer Science**.

The application explores how machine learning and natural language processing can support the creative writing process by analyzing user-provided text and presenting useful feedback through an interactive web application.

Bloom combines a **Python/FastAPI backend**, **PostgreSQL database**, **React frontend**, and machine learning functionality into a full-stack application.

## ✨ Features

- AI-assisted analysis of user-provided creative writing
- User authentication and authorization
- Analysis history and persistence
- REST API connecting the frontend, backend, database, and ML functionality
- Interactive React-based user interface
- Automated backend and API testing
- Validation and error handling across application workflows

## 🛠️ Tech Stack

### Backend
- Python
- FastAPI
- PostgreSQL
- REST APIs

### Frontend
- React
- JavaScript

### Machine Learning
- Python
- Natural Language Processing
- Machine learning models integrated with the application backend

### Testing
- pytest
- HTTPX
- Fixtures
- Mocking and monkeypatching
- Positive and negative API testing

## 🏗️ Architecture

Bloom is divided into three main components:

```text
Bloom/
├── backend/       # FastAPI application, API endpoints and database integration
├── frontend/      # React web application
├── training/      # Machine learning model training and experimentation
└── README.md
```

The application follows a client-server architecture:

```text
                 ┌─────────────────┐
                 │  React Frontend │
                 └────────┬────────┘
                          │
                       REST API
                          │
                 ┌────────▼────────┐
                 │ FastAPI Backend │
                 └───┬─────────┬───┘
                     │         │
              ┌──────▼───┐ ┌──▼──────────┐
              │PostgreSQL│ │ ML Component│
              └──────────┘ └─────────────┘
```

The frontend communicates with the FastAPI backend through REST endpoints. The backend handles application logic, authentication, persistence, and communication with the machine learning functionality.

## 🧪 Testing

Testing was an important part of the project.

The backend includes automated API tests built with **pytest** and **HTTPX**, covering scenarios such as:

- Authentication and authorization
- Request validation
- Database persistence
- Analysis history
- Resource deletion
- Invalid requests and error handling
- Expected HTTP status codes and response payloads

Fixtures, mocks, and monkeypatching are used where appropriate to isolate dependencies and make tests repeatable.

Both positive and negative scenarios are tested to validate not only successful workflows but also application behavior when invalid input or unexpected conditions occur.

## 🎯 What I Learned

Building Bloom gave me experience taking an AI-oriented application from an initial idea to an integrated full-stack system.

The project strengthened my understanding of:

- Designing and implementing REST APIs with FastAPI
- Integrating machine learning functionality into a web application
- Working with relational data and PostgreSQL
- Connecting frontend, backend, database, and ML components
- Designing reliable automated API tests
- Debugging issues across multiple application layers
- Structuring a larger software project into maintainable components

One of the most valuable parts of the project was learning that building an AI application involves much more than the model itself. The surrounding APIs, data persistence, testing, error handling, and user-facing application are equally important in turning an ML experiment into a usable software system.

## 🚀 Running the Project

> Detailed setup instructions will be added as the project is prepared for reproducible local deployment.

The project consists of separate backend, frontend, and ML/training components. Each component requires its respective dependencies and configuration.

## 📚 About the Project

Bloom was developed as my **Bachelor's Degree Project in Computer Science at Babeș-Bolyai University**.

The project combines my interests in **artificial intelligence, natural language processing, backend development, and software engineering** to explore practical ways AI can assist rather than replace the creative writing process.

---

**Author:** Larisa-Elena Săvoiu
