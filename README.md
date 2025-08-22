# 🚀 **QUANTUMLEAP TRADING BACKEND**

## 📋 **Overview**
Backend API for the Vitan Task platform with modular architecture, supporting OTP authentication, WhatsApp integration, and comprehensive task management.

## 🏗️ **Architecture**
- **Modular Design**: Dynamic module loading system
- **Express.js**: Fast, unopinionated web framework
- **Service Container**: Dependency injection and service management
- **Event Bus**: Inter-module communication
- **Database**: PostgreSQL with connection pooling

## 📦 **Modules**

### **Core Modules**
- **auth**: OTP-based authentication and user management
- **dashboard**: Dashboard analytics and metrics
- **tasks**: Task management and assignment
- **projects**: Project organization and tracking
- **team**: Team collaboration and member management
- **analytics**: Data analytics and reporting
- **templates**: Task and project templates
- **whatsapp**: WhatsApp integration and messaging
- **system**: System monitoring and health checks
- **contacts**: Contact management and organization
- **ai**: AI-powered features and services
- **users**: User management and profiles

## 🚀 **Quick Start**

### **Prerequisites**
- Node.js >= 18.0.0
- PostgreSQL database
- Environment variables configured

### **Installation**
```bash
npm install
```

### **Environment Variables**
Create a `.env` file with:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/vitan_task

# JWT
JWT_SECRET=your-secret-key

# WhatsApp (Meta)
META_PHONE_NUMBER_ID=your-phone-number-id
META_ACCESS_TOKEN=your-access-token
WHATSAPP_VERIFY_TOKEN=your-verify-token

# CORS
CORS_ORIGIN=https://vitan-task-frontend.up.railway.app

# Server
MODULAR_PORT=4000
NODE_ENV=production
```

### **Running the Server**
```bash
# Development
npm run dev

# Production
npm start
```

## 🔧 **API Endpoints**

### **Health Check**
- `GET /health` - Server health status
- `GET /api/modules/*/health` - Module health checks

### **Authentication**
- `POST /api/modules/auth/otp/request` - Request OTP
- `POST /api/modules/auth/otp/verify` - Verify OTP
- `POST /api/modules/auth/login` - User login

### **Tasks**
- `GET /api/modules/tasks` - List tasks
- `POST /api/modules/tasks` - Create task
- `PUT /api/modules/tasks/:id` - Update task
- `DELETE /api/modules/tasks/:id` - Delete task

### **Projects**
- `GET /api/modules/projects` - List projects
- `POST /api/modules/projects` - Create project
- `PUT /api/modules/projects/:id` - Update project
- `DELETE /api/modules/projects/:id` - Delete project

### **WhatsApp**
- `POST /api/modules/whatsapp/send` - Send message
- `POST /api/modules/whatsapp/webhook` - Webhook endpoint
- `GET /api/modules/whatsapp/health` - WhatsApp service health

## 🧪 **Testing**
```bash
npm test
```

## 📊 **Monitoring**
- **Health Checks**: Built-in health monitoring
- **Logging**: Winston-based structured logging
- **Error Handling**: Comprehensive error handling middleware
- **Rate Limiting**: Built-in rate limiting for security

## 🔒 **Security**
- **Helmet**: Security headers
- **CORS**: Configurable cross-origin resource sharing
- **Rate Limiting**: Protection against abuse
- **Input Validation**: Request validation and sanitization
- **JWT Authentication**: Secure token-based authentication

## 🚀 **Deployment**
- **Railway**: Auto-deployment from GitHub main branch
- **Environment**: Production-ready configuration
- **Scaling**: Modular architecture supports horizontal scaling

## 📚 **Documentation**
- **API Docs**: Comprehensive endpoint documentation
- **Module Guide**: Detailed module implementation guide
- **Architecture**: System architecture and design patterns

---

## 🔗 **Links**
- **Frontend**: https://vitan-task-frontend.up.railway.app
- **Backend**: https://vitan-task-production.up.railway.app
- **GitHub**: https://github.com/JagPat/quantumleap-trading-backend.git

---

*Built with ❤️ for the Vitan Task platform*
