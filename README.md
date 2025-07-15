# QuantumLeap Trading - Backend API

A FastAPI-based backend service that connects to the Zerodha Kite Connect API to provide trading and portfolio management functionality.

## Features

- **OAuth2 Authentication**: Secure broker authentication using Kite Connect
- **Portfolio Management**: Fetch holdings, positions, and portfolio summary
- **Secure Storage**: Encrypted storage of user credentials in SQLite database
- **RESTful API**: Clean, well-documented API endpoints
- **Error Handling**: Comprehensive error handling and logging
- **OpenAPI Documentation**: Auto-generated API documentation

## Technology Stack

- **Framework**: FastAPI
- **Database**: SQLite with encrypted credential storage
- **Broker Integration**: Zerodha Kite Connect API (pykiteconnect)
- **Authentication**: OAuth2 flow
- **Encryption**: Cryptography library for secure data storage

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**:
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` file and set your configuration:
   ```bash
   # Generate encryption key
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

5. **Start the server**:
   ```bash
   python run.py
   ```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:

- **Interactive API Documentation**: http://localhost:8000/docs
- **Alternative API Documentation**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## API Endpoints

### Authentication

#### POST `/api/broker/generate-session`
Exchanges a request_token from the broker's OAuth flow for a valid access_token.

**Request Body**:
```json
{
  "request_token": "string",
  "user_id": "string",
  "api_key": "string",
  "api_secret": "string"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Broker connected successfully.",
  "data": {
    "user_id": "string",
    "user_name": "string",
    "email": "string"
  }
}
```

### Portfolio Data

#### GET `/api/portfolio/summary`
Fetches a high-level summary of the user's portfolio.

**Parameters**:
- `user_id` (query): User ID

**Response**:
```json
{
  "status": "success",
  "data": {
    "total_value": 100000.0,
    "total_pnl": 5000.0,
    "todays_pnl": 500.0
  }
}
```

#### GET `/api/portfolio/holdings`
Fetches the user's long-term equity holdings.

**Parameters**:
- `user_id` (query): User ID

**Response**:
```json
{
  "status": "success",
  "data": [
    {
      "symbol": "RELIANCE",
      "quantity": 10,
      "avg_price": 2500.0,
      "current_price": 2600.0,
      "pnl": 1000.0
    }
  ]
}
```

#### GET `/api/portfolio/positions`
Fetches the user's current day positions.

**Parameters**:
- `user_id` (query): User ID

**Response**:
```json
{
  "status": "success",
  "data": {
    "net": [...],
    "day": [...]
  }
}
```

## Security Features

1. **Encrypted Storage**: All sensitive data (API keys, secrets, access tokens) are encrypted before storage
2. **Secure Database**: SQLite database with proper indexing and constraints
3. **Error Handling**: Comprehensive error handling without exposing sensitive information
4. **Input Validation**: Pydantic models for request/response validation
5. **CORS Configuration**: Configurable CORS settings for production deployment

## Development

### Project Structure

```
backend/
├── main.py              # FastAPI application
├── models.py            # Pydantic models
├── database.py          # Database operations
├── kite_service.py      # Kite Connect API service
├── config.py            # Configuration management
├── run.py               # Application startup script
├── requirements.txt     # Python dependencies
├── env.example          # Environment variables example
└── README.md           # This file
```

### Running in Development Mode

```bash
# Set DEBUG=true in .env file
python run.py
```

### Testing

You can test the API endpoints using:

1. **Interactive Documentation**: Visit http://localhost:8000/docs
2. **cURL**: 
   ```bash
   curl -X GET "http://localhost:8000/health"
   ```
3. **Postman**: Import the OpenAPI schema from http://localhost:8000/openapi.json

## Deployment

### Production Deployment

1. **Environment Variables**: Set production values in `.env`
2. **Database**: Ensure SQLite database is properly backed up
3. **Security**: Use strong encryption keys and secure CORS settings
4. **Monitoring**: Implement proper logging and monitoring

### Docker Deployment (Optional)

Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "run.py"]
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed and virtual environment is activated
2. **Database Errors**: Check file permissions and disk space
3. **Kite API Errors**: Verify API credentials and network connectivity
4. **Encryption Errors**: Ensure ENCRYPTION_KEY is properly set

### Logging

Logs are output to console. For production, configure proper log files:

```python
import logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Check the logs for error details
4. Open an issue in the repository 