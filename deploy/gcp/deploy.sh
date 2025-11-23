#!/bin/bash
# GCP GKE Deployment Script

set -e

PROJECT_ID=${GCP_PROJECT_ID:-anc-platform}
CLUSTER_NAME=${CLUSTER_NAME:-anc-platform}
REGION=${GCP_REGION:-us-central1}
NAMESPACE=anc-platform

echo "Deploying to GCP GKE..."
echo "Project: $PROJECT_ID"
echo "Cluster: $CLUSTER_NAME"
echo "Region: $REGION"

# Configure kubectl for GKE
gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION --project $PROJECT_ID

# Create namespace
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply Kubernetes manifests
kubectl apply -f ../../k8s/namespace.yaml
kubectl apply -f ../../k8s/configmap.yaml
kubectl apply -f ../../k8s/pvc.yaml
kubectl apply -f ../../k8s/deployment.yaml
kubectl apply -f ../../k8s/service.yaml
kubectl apply -f ../../k8s/ingress.yaml
kubectl apply -f ../../k8s/hpa.yaml

# Wait for rollout
kubectl rollout status deployment/anc-system -n $NAMESPACE

echo "✓ Deployment complete"
echo "Service URL: $(kubectl get ingress anc-system-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
