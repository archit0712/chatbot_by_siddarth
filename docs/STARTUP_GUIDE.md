# TechConsult Inc Knowledge Chatbot - Startup Guide

## 🚀 How to Run the Application

After the recent directory reorganization, there are multiple ways to start the application:

### ✅ **Recommended Method (From Project Root)**
```bash
# Navigate to the project root directory
cd /path/to/chatbot

# Run the application
streamlit run run_app.py
```

### 🔧 **Alternative Methods**

#### Method 1: Using the main entry point
```bash
streamlit run main.py
```

#### Method 2: Direct core app execution
```bash
streamlit run core/app.py
```

## 📁 **Updated Directory Structure**

The project has been reorganized for better maintainability:

```
chatbot/
├── config/              # Configuration files
│   ├── .env
│   ├── firebase_config.json
│   └── firebase-adminsdk.json
├── core/                # Core application modules
│   ├── app.py          # Main Streamlit application
│   ├── database.py     # Vector database management
│   ├── firebase_auth.py # Authentication
│   └── admin.py        # Admin interface
├── document_modules/    # Document processing
├── llm_modules/        # LLM integration
├── ui/                 # User interface components
├── utils/              # Utilities and filters
├── vector_db/          # Vector database storage
├── docs/               # Documentation
├── tests/              # Test results
├── requirements/       # Dependencies
├── run_app.py          # Recommended startup script
└── main.py            # Alternative entry point
```

## 🔧 **Import Resolution**

The application now includes proper Python path setup to resolve module imports regardless of how it's started. This ensures compatibility with:

- Direct Streamlit execution
- IDE debugging
- Docker deployments
- Production hosting

## 📝 **Environment Setup**

### **Option 1: Environment Variables (Recommended)**

Configure your environment variables in `config/.env`:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key


# Vector Database Configuration
VECTOR_DB_PATH=./vector_db

# Application Configuration
AUDIT_LOG_ENABLED=true
USE_LLM_CLASSIFICATION=true
USE_GUARDRAILS=true
USE_UNIFIED_ANALYZER=true
```


## 🎯 **Quick Start**

1. **Install dependencies:**
   ```bash
   pip install -r requirements/requirements.txt
   ```

2. **Configure environment:**
   - Copy `env.example` to `config/.env` and fill in your values

3. **Run the application:**
   ```bash
   streamlit run run_app.py
   ```

## 🐛 **Troubleshooting**

### Module Import Errors
If you encounter `ModuleNotFoundError`, ensure you're running from the project root directory and using one of the recommended startup methods.

### Environment File Not Found
Make sure your `.env` file is located in the `config/` directory, not the project root. Copy `env.example` to `config/.env` and fill in your values.
