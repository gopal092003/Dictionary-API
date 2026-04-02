# 📘 Dictionary API – Detailed Documentation

This document provides **technical documentation** for developers using the Dictionary API.

---

## 🔹 Base URL

```id="d9n2k1"
http://127.0.0.1:8000
```

---

## 🔹 Endpoint: `/`

### 📌 Description

Health check endpoint to verify that the API is running.

### 📌 Method

`GET`

### 📌 Response

```json id="n2k4sd"
{
  "message": "Dictionary API is running 🚀",
  "usage": "/define/{word}"
}
```

---

## 🔹 Endpoint: `/define/{word}`

### 📌 Description

Fetch meanings and synonyms for a given word.

---

### 📌 Method

```id="0d9fsl"
GET
```

---

### 📌 Path Parameter

| Parameter | Type   | Required | Description    |
| --------- | ------ | -------- | -------------- |
| `word`    | string | Yes      | Word to search |

---

### 📌 Example Request

```http id="f9s0dk"
GET /define/apple
```

---

### 📌 Example Response

```json id="dk29f0"
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

## 🔹 Response Fields

| Field      | Type   | Description         |
| ---------- | ------ | ------------------- |
| `word`     | string | Queried word        |
| `meanings` | list   | List of definitions |
| `synonyms` | list   | List of synonyms    |

---

## ⚠️ Error Handling

### 🔸 404 – Word Not Found

Returned when:

* The word does not exist in the dictionary API

**Example:**

```json id="k2d9sl"
{
  "detail": "Word 'xyzabc' not found"
}
```

---

### 🔸 500 – Internal Server Error

Returned when:

* External API fails
* Unexpected server issues occur

**Example:**

```json id="x2ls9d"
{
  "detail": "Internal server error"
}
```

---

## 🔄 Internal Workflow

```id="sl2kd9"
Client Request
     ↓
FastAPI Route (/define/{word})
     ↓
Service Layer (dictionary_service)
     ↓
External API Calls
     ├── Dictionary API (meanings)
     └── Datamuse API (synonyms)
     ↓
Processed Response Returned
```

---

## 🌐 External APIs Used

### 1️⃣ Dictionary API

```id="p0d92k"
https://api.dictionaryapi.dev/api/v2/entries/en/{word}
```

Used for:

* Word meanings
* Definitions

---

### 2️⃣ Datamuse API

```id="l20s9d"
https://api.datamuse.com/words?rel_syn={word}
```

Used for:

* Synonyms

---

## 🧪 Testing the API

### 🔹 Browser

```id="d02ksl"
http://127.0.0.1:8000/define/apple
```

---

### 🔹 cURL

```bash id="a9dk20"
curl http://127.0.0.1:8000/define/apple
```

---

### 🔹 FastAPI Docs

```id="l2d0sk"
http://127.0.0.1:8000/docs
```

---

## 📌 Supported Input

* Only English words are supported
* Case-insensitive input (handled internally)

---

## 🚧 Limitations

* No caching (each request hits external APIs)
* No rate limiting
* Depends on availability of third-party APIs
* Limited metadata (no phonetics or examples yet)

---

## 🔮 Future Enhancements

* Add `/antonyms/{word}` endpoint
* Add phonetics and pronunciation
* Add caching layer (Redis / in-memory)
* Add request validation and rate limiting
* Deploy to cloud platform

---

## 📎 Notes

* API follows REST principles
* Responses are JSON formatted
* Designed with modular architecture for scalability

---
