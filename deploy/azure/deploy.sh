#!/bin/bash
# Azure AKS Deployment Script

set -e

RESOURCE_GROUP=${AZURE_RESOURCE_GROUP:-anc-platform-rg}
CLUSTER_NAME=${CLUSTER_NAME:-anc-platform}
LOCATION=${AZURE_LOCATION:-eastus}
NAMESPACE=anc-platform

echo "Deploying to Azure AKS..."
echo "Resource Group: $RESOURCE_GROUP"
echo "Cluster: $CLUSTER_NAME"
echo "Location: $LOCATION"

# Configure kubectl for AKS
az aks get-credentials --resource-group $RESOURCE_GROUP --name $CLUSTER_NAME

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
