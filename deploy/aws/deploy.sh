#!/bin/bash
# AWS EKS Deployment Script

set -e

CLUSTER_NAME=${CLUSTER_NAME:-anc-platform}
REGION=${AWS_REGION:-us-east-1}
NAMESPACE=anc-platform

echo "Deploying to AWS EKS..."
echo "Cluster: $CLUSTER_NAME"
echo "Region: $REGION"

# Configure kubectl for EKS
aws eks update-kubeconfig --name $CLUSTER_NAME --region $REGION

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
echo "Service URL: $(kubectl get ingress anc-system-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"
