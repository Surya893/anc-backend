# Starting the Layered Architecture

## Quick Start (All Layers)

### Option 1: Docker Compose (Recommended)

Start all layers with one command:

```bash
# Copy environment file
cp .env.example.layered .env

# Edit .env with your configuration
nano .env

# Start all services
docker-compose -f docker-compose.layered.yml up -d

# View logs
docker-compose -f docker-compose.layered.yml logs -f

# Stop all services
docker-compose -f docker-compose.layered.yml down
```

### Option 2: Individual Layer Startup

Start each layer separately for development:

#### 1. Start Database Layer

```bash
# Start PostgreSQL
docker run -d \
  --name anc-postgres \
  -e POSTGRES_USER=anc_user \
  -e POSTGRES_PASSWORD=anc_password \
  -e POSTGRES_DB=anc_system \
  -p 5432:5432 \
  postgres:14-alpine

# Start Redis
docker run -d \
  --name anc-redis \
  -p 6379:6379 \
  redis:7-alpine

# Initialize database schema
psql -U anc_user -h localhost -d anc_system -f database/schema.sql
```

#### 2. Start Backend Layer

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run database migrations (if needed)
python -c "from config.database import init_db; init_db()"

# Start Flask server
python server.py

# In another terminal, start Celery worker
celery -A server.celery worker --loglevel=info
```

Backend will be available at: `http://localhost:5000`

#### 3. Start Frontend Layer

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

Frontend will be available at: `http://localhost:3000`

#### 4. (Optional) Deploy Cloud Layer

```bash
cd cloud/terraform

# Initialize Terraform
terraform init

# Deploy to AWS
terraform apply -auto-approve

# Get outputs
terraform output
```

## Verify Each Layer

### 1. Database Layer

```bash
# Test PostgreSQL connection
psql -U anc_user -h localhost -d anc_system -c "SELECT 1;"

# Test Redis connection
redis-cli ping
# Expected: PONG
```

### 2. Backend Layer

```bash
# Health check
curl http://localhost:5000/health
# Expected: {"status": "healthy", ...}

# API documentation
curl http://localhost:5000/api/docs
```

### 3. Frontend Layer

```bash
# Open in browser
open http://localhost:3000

# Or curl
curl http://localhost:3000
```

### 4. Cloud Layer

```bash
# Test Lambda function
aws lambda invoke \
  --function-name anc-audio-receiver \
  --payload '{"test": true}' \
  response.json

# Test IoT connection
python cloud/iot/iot_connection.py
```

## Architecture Validation

### Test Layer Communication

```bash
# Frontend → Backend → Database
# Open browser to http://localhost:3000
# Click "Start ANC" button
# Check backend logs for database queries

# Backend → Cloud
# From backend, invoke Lambda:
python -c "
import boto3
lambda_client = boto3.client('lambda')
response = lambda_client.invoke(
    FunctionName='anc-audio-receiver',
    Payload='{\"test\": true}'
)
print(response)
"

# IoT Device → Cloud → Backend
# Run IoT publisher
python cloud/iot/telemetry_publisher.py

# Check backend receives data via webhooks
```

## Layer Endpoints

### Frontend Layer
- Web UI: `http://localhost:3000`
- Development: `http://localhost:3000`

### Backend Layer
- API: `http://localhost:5000`
- Health: `http://localhost:5000/health`
- API Docs: `http://localhost:5000/api/docs`
- WebSocket: `ws://localhost:5000`

### Database Layer
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

### Cloud Layer
- API Gateway: `https://<api-id>.execute-api.us-east-1.amazonaws.com`
- WebSocket: `wss://<ws-id>.execute-api.us-east-1.amazonaws.com`
- IoT Endpoint: `<endpoint>.iot.us-east-1.amazonaws.com`

### Monitoring
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001` (admin/admin)

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check logs
docker logs anc-postgres

# Reset database
docker-compose -f docker-compose.layered.yml down -v
docker-compose -f docker-compose.layered.yml up -d postgres
```

### Backend Issues

```bash
# Check backend logs
docker logs anc-backend

# Check if dependencies are installed
pip list | grep Flask

# Rebuild backend
docker-compose -f docker-compose.layered.yml build backend
```

### Frontend Issues

```bash
# Check frontend logs
docker logs anc-frontend

# Clear node_modules and reinstall
rm -rf frontend/node_modules
cd frontend && npm install

# Rebuild frontend
docker-compose -f docker-compose.layered.yml build frontend
```

### Cloud Deployment Issues

```bash
# Check AWS credentials
aws sts get-caller-identity

# Check Terraform state
cd cloud/terraform
terraform show

# View Lambda logs
aws logs tail /aws/lambda/anc-audio-receiver --follow
```

## Production Deployment

For production deployment:

1. Update `.env` with production values
2. Set `FLASK_ENV=production`
3. Use strong secrets for `SECRET_KEY` and `JWT_SECRET_KEY`
4. Enable HTTPS (SSL certificates)
5. Configure proper CORS origins
6. Set up database backups
7. Deploy cloud infrastructure
8. Configure monitoring and alerts

See `/docs/deployment/PRODUCTION_DEPLOYMENT.md` for details.

## Next Steps

1. ✅ Verify all layers are running
2. ✅ Test inter-layer communication
3. ✅ Configure monitoring
4. ✅ Deploy to cloud (optional)
5. ✅ Run integration tests
6. ✅ Set up CI/CD pipeline

## Support

For issues or questions:
- Check layer-specific READMEs
- Review architecture documentation: `/ARCHITECTURE.md`
- Check logs for each layer
- Consult main README: `/README.md`
