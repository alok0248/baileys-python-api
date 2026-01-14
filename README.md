# Baileys Python API

A comprehensive WhatsApp API integration built with TypeScript/Node.js and Python FastAPI. This project bridges the powerful Baileys WhatsApp library with a FastAPI backend to provide RESTful endpoints for WhatsApp operations.

## 📋 Project Overview

This project consists of two main components:

1. **Baileys Server** (TypeScript/Node.js) - WebSocket-based WhatsApp client powered by [@whiskeysockets/baileys](https://github.com/WhiskeySockets/Baileys)
2. **FastAPI Server** (Python) - REST API bridge that communicates with the Baileys server

## 🚀 Features

- WhatsApp QR code generation and authentication
- Send and receive messages
- Media handling (images, videos, audio)
- Group management
- Contact and chat operations
- RESTful API for easy integration
- Real-time status updates via WebSocket

## 📦 Prerequisites

- **Node.js** 16+ (for Baileys server)
- **Python** 3.8+ (for FastAPI server)
- **npm** or **yarn** (Node package manager)
- **pip** (Python package manager)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/baileys-python-api.git
cd baileys-python-api
```

### 2. Install Dependencies

#### Option A: Automatic Setup (Windows)
Run the provided setup script:

```bash
python run_all.py
```

This will automatically:
- Install Node dependencies
- Install Python dependencies
- Start both servers

#### Option B: Manual Setup

**Node Server:**
```bash
cd baileys-server
npm install
```

**Python Server:**
```bash
cd fastapi-server
pip install -r requirements.txt
```

## 🏃 Running the Project

### Start Both Servers
```bash
python run_all.py
```

### Start Servers Individually

**Baileys Server:**
```bash
cd baileys-server
npm start
```

**FastAPI Server:**
```bash
cd fastapi-server
python main.py
```

## 📡 API Endpoints

### QR Code Operations
- `GET /qr` - Get QR data for authentication
- `GET /qr/image` - Get QR as PNG image

### Message Operations
- `POST /send/text` - Send text message
- `POST /send/media` - Send media file
- `GET /messages/{chatId}` - Get chat messages

### Chat Operations
- `GET /chats` - Get all chats
- `GET /chats/{id}` - Get specific chat

### Status
- `GET /status` - Get connection status

## 🔧 Configuration

### FastAPI Server Configuration
Edit `fastapi-server/config.py`:

```python
NODE_BASE_URL = "http://localhost:3000"  # Baileys server URL
```

## 📁 Project Structure

```
baileys-python-api/
├── baileys-server/          # TypeScript WhatsApp client
│   ├── src/
│   │   └── server.ts       # Express server & WebSocket handler
│   ├── auth_info/          # WhatsApp authentication data
│   ├── media/              # Downloaded media files
│   ├── package.json
│   └── tsconfig.json
├── fastapi-server/          # Python REST API
│   ├── main.py             # FastAPI application
│   ├── config.py           # Configuration settings
│   ├── requirements.txt
│   └── __pycache__/
├── run_all.py              # Automated startup script
├── package.json            # Root dependencies
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## 🔐 Authentication

1. Start the servers using `python run_all.py`
2. Access the QR endpoint: `GET http://localhost:8000/qr/image`
3. Scan the QR code with your WhatsApp device
4. Connection will be established automatically

**Note:** The `auth_info/` folder contains sensitive authentication data. Keep it secure and never commit it to version control.

## 🐛 Troubleshooting

### Node dependencies not installing
```bash
cd baileys-server
npm install --legacy-peer-deps
```

### Python package conflicts
```bash
python -m pip install --upgrade pip
pip install -r fastapi-server/requirements.txt --force-reinstall
```

### Port already in use
- Change port in `baileys-server/src/server.ts`
- Change port in `fastapi-server/main.py`

### QR Code not loading
- Ensure Baileys server is running on port 3000
- Check `NODE_BASE_URL` in `fastapi-server/config.py`

## 📝 Environment Variables

Create a `.env` file in the root directory:

```
NODE_PORT=3000
FASTAPI_PORT=8000
FASTAPI_HOST=0.0.0.0
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👤 Author

**Alok Kumar**
- Email: [alokkumar2812@gmail.com](mailto:alokkumar2812@gmail.com)
- GitHub: [@0248](https://github.com/alok0248)

## ⚠️ Disclaimer

This project is for educational and personal use only. Use responsibly and in compliance with WhatsApp's Terms of Service. The maintainers are not responsible for misuse or violations of service terms.

## 🔗 Related Projects

- [Baileys](https://github.com/WhiskeySockets/Baileys) - WhatsApp Web API client
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Express.js](https://expressjs.com/) - Node.js web framework

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Email: alokkumar2812@gmail.com

---

**Last Updated:** January 14, 2026
