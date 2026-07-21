# Dictionary API

A modular REST API built with FastAPI for retrieving word definitions and synonyms. The application integrates with DictionaryAPI and Datamuse to provide accurate lexical information through a simple and well-structured API.

---

## Features

- Retrieve word definitions
- Fetch synonyms for a given word
- Interactive API documentation with Swagger UI
- Modular project structure for easy maintenance
- Clean separation of routes, services, and utilities
- Easily extensible for additional language features

---

## Tech Stack

- FastAPI
- Uvicorn
- Requests
- DictionaryAPI
- Datamuse API

---

## Project Structure

```
dictionary-api/
│
├── app/
│   ├── config/         # Application configuration
│   ├── routes/         # API endpoints
│   ├── services/       # Business logic
│   └── utils/          # External API integrations
│
├── tests/              # Unit tests
├── run.py              # Application entry point
├── requirements.txt
└── README.md
```

---

## Getting Started

### Clone the Repository

```
git clone https://github.com/gopal092003/Dictionary-API.git

cd Dictionary-API
```

### Create a Virtual Environment

```
python -m venv venv
```

Activate the environment:

**Windows**

```
venv\Scripts\activate
```

**Linux / macOS**

```
source venv/bin/activate
```

### Install Dependencies

```
pip install -r requirements.txt
```

---

## Running the Application

Start the development server:

```
python run.py
```

The API will be available at:

```
http://127.0.0.1:8000
```

---

## Interactive API Documentation

FastAPI automatically generates API documentation.

Swagger UI:

```
http://127.0.0.1:8000/docs
```

ReDoc:

```
http://127.0.0.1:8000/redoc
```

---

## API Endpoints

### Health Check

```http
GET /
```

Returns the application status.

### Get Word Information

```http
GET /define/{word}
```

Example:

```http
GET /define/apple
```

### Example Response

```json
{
  "word": "apple",
  "meanings": [
    "A common, round fruit produced by the tree Malus domestica."
  ],
  "synonyms": [
    "orchard apple tree",
    "malus pumila"
  ]
}
```

---

## How It Works

1. A client sends a request with a word.
2. The API retrieves definitions from DictionaryAPI.
3. Synonyms are fetched from Datamuse.
4. The results are combined into a single response and returned to the client.

---

## External Services

- DictionaryAPI – Provides word definitions and meanings.
- Datamuse API – Provides synonyms and related words.

---

## Error Handling

| Status Code | Description |
|-------------|-------------|
| 200 | Request completed successfully |
| 404 | Word not found |
| 500 | Internal server error |

---

## Running Tests

Run the test suite using:

```
pytest
```

If the project is configured with `unittest`, those tests can be executed as well.

---

## Future Improvements

- Support antonyms
- Add pronunciation and phonetics
- Cache frequently requested words
- Support multiple dictionaries
- Rate limiting
- Docker support
- Cloud deployment
- API authentication

---

## Author

**Gopal Gupta**

GitHub: https://github.com/gopal092003

---

## License

This project is licensed under the MIT License.
