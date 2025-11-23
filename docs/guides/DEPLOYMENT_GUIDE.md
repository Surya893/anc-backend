# ANC Platform - Deployment Guide

Complete deployment guide for all environments and cloud providers.

---

## Quick Start

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/your-org/anc-platform.git
cd anc-platform

# 2. Start with Docker Compose
docker-compose up -d

# 3. Access services
- API: http://localhost:5000
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

# 4. Run smoke tests
./scripts/smoke-tests.sh http://localhost:5000
```

### Production Deployment

```bash
# AWS EKS
cd deploy/aws
./deploy.sh

# GCP GKE
cd deploy/gcp
./deploy.sh

# Azure AKS
cd deploy/azure
./deploy.sh
```

---

## Prerequisites

### Required Tools

```bash
# Container tools
- Docker >= 20.10
- docker-compose >= 2.0

# Kubernetes tools
- kubectl >= 1.27
- helm >= 3.12

# Cloud CLIs (choose based on provider)
- AWS CLI >= 2.0
- gcloud SDK >= 400.0
- Azure CLI >= 2.50

# IaC tools
- Terraform >= 1.5
```

### Required Access

- Container registry access
- Kubernetes cluster admin
- Cloud provider credentials
- Domain name and SSL certificates

---

## Environment Configuration

### 1. Copy Environment Template

```bash
cp .env.example .env
```

### 2. Configure Required Variables

```bash
# Security
SECRET_KEY=<generate-strong-key>
JWT_SECRET_KEY=<generate-jwt-key>
API_KEYS=<comma-separated-api-keys>

# Database
DATABASE_URL=postgresql://user:pass@host:5432/anc_production
REDIS_URL=redis://host:6379/0

# Cloud Storage
S3_BUCKET=anc-platform-models
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>

# Monitoring
PROMETHEUS_ENABLED=true
LOG_LEVEL=INFO
```

---

## Docker Deployment

### Build Image

```bash
# Build production image
docker build -t anc-system:latest .

# Tag for registry
docker tag anc-system:latest ghcr.io/your-org/anc-system:v1.0.0

# Push to registry
docker push ghcr.io/your-org/anc-system:v1.0.0
```

### Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f anc-api

# Stop services
docker-compose down

# Clean up volumes
docker-compose down -v
```

---

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace anc-platform
```

### 2. Create Secrets

```bash
# API keys
kubectl create secret generic anc-api-keys \
  --from-literal=api-key-1=<key1> \
  --from-literal=api-key-2=<key2> \
  -n anc-platform

# Database credentials
kubectl create secret generic anc-db-credentials \
  --from-literal=username=<user> \
  --from-literal=password=<pass> \
  -n anc-platform

# SSL certificates
kubectl create secret tls anc-tls-cert \
  --cert=path/to/cert.pem \
  --key=path/to/key.pem \
  -n anc-platform
```

### 3. Apply Manifests

```bash
# Apply in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -n anc-platform

# Check services
kubectl get svc -n anc-platform

# Check ingress
kubectl get ingress -n anc-platform

# View logs
kubectl logs -f deployment/anc-system -n anc-platform
```

---

## AWS Deployment

### Using Terraform

```bash
cd deploy/aws

# Initialize Terraform
terraform init

# Plan deployment
terraform plan \
  -var="cluster_name=anc-production" \
  -var="aws_region=us-east-1"

# Apply configuration
terraform apply

# Get cluster info
terraform output cluster_endpoint
terraform output database_endpoint
```

### Using Deployment Script

```bash
cd deploy/aws

# Set environment variables
export CLUSTER_NAME=anc-production
export AWS_REGION=us-east-1

# Deploy
./deploy.sh
```

### Post-Deployment

```bash
# Configure kubectl
aws eks update-kubeconfig \
  --name anc-production \
  --region us-east-1

# Verify connectivity
kubectl get nodes

# Check application
kubectl get pods -n anc-platform
```

---

## GCP Deployment

### Setup

```bash
# Authenticate
gcloud auth login

# Set project
gcloud config set project anc-platform-prod

# Create GKE cluster
gcloud container clusters create anc-production \
  --region us-central1 \
  --num-nodes 3 \
  --machine-type n1-standard-2 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 10
```

### Deploy

```bash
cd deploy/gcp

# Set environment
export GCP_PROJECT_ID=anc-platform-prod
export CLUSTER_NAME=anc-production
export GCP_REGION=us-central1

# Deploy
./deploy.sh
```

---

## Azure Deployment

### Setup

```bash
# Login to Azure
az login

# Create resource group
az group create \
  --name anc-platform-rg \
  --location eastus

# Create AKS cluster
az aks create \
  --resource-group anc-platform-rg \
  --name anc-production \
  --node-count 3 \
  --enable-addons monitoring \
  --generate-ssh-keys
```

### Deploy

```bash
cd deploy/azure

# Set environment
export AZURE_RESOURCE_GROUP=anc-platform-rg
export CLUSTER_NAME=anc-production
export AZURE_LOCATION=eastus

# Deploy
./deploy.sh
```

---

## Monitoring Setup

### Prometheus

```bash
# Create monitoring namespace
kubectl create namespace monitoring

# Deploy Prometheus
kubectl apply -f monitoring/prometheus.yml -n monitoring

# Access Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```

### Grafana

```bash
# Deploy Grafana
helm install grafana grafana/grafana \
  --namespace monitoring \
  --set adminPassword=admin

# Import dashboard
# Use monitoring/grafana-dashboard.json
```

### Alerts

```bash
# Configure AlertManager
kubectl apply -f monitoring/alerts.yml -n monitoring

# Set up Slack/PagerDuty integration
# Edit AlertManager config with webhook URLs
```

---

## SSL/TLS Configuration

### Let's Encrypt with Cert-Manager

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml

# Create ClusterIssuer
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
