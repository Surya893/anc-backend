#!/bin/bash
##############################################################################
# AWS Cloud Deployment Script for ANC Platform
# Deploys complete infrastructure using Terraform
##############################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Step 1: Checking Prerequisites"

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform not found. Please install: https://www.terraform.io/downloads"
        exit 1
    fi
    print_success "Terraform installed: $(terraform version | head -n 1)"

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install: https://aws.amazon.com/cli/"
        exit 1
    fi
    print_success "AWS CLI installed: $(aws --version)"

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Run: aws configure"
        exit 1
    fi
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=$(aws configure get region || echo "us-east-1")
    print_success "AWS Account: $AWS_ACCOUNT, Region: $AWS_REGION"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found"
        exit 1
    fi
    print_success "Python installed: $(python3 --version)"

    echo ""
}

# Create S3 bucket for Terraform state
setup_terraform_backend() {
    print_header "Step 2: Setting Up Terraform Backend"

    BUCKET_NAME="anc-platform-terraform-state-${AWS_ACCOUNT}"
    TABLE_NAME="terraform-lock"

    # Create S3 bucket if it doesn't exist
    if ! aws s3 ls "s3://${BUCKET_NAME}" 2>&1 > /dev/null; then
        print_info "Creating S3 bucket for Terraform state..."
        aws s3 mb "s3://${BUCKET_NAME}" --region "${AWS_REGION}"

        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "${BUCKET_NAME}" \
            --versioning-configuration Status=Enabled

        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket "${BUCKET_NAME}" \
            --server-side-encryption-configuration '{
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }'

        print_success "Created S3 bucket: ${BUCKET_NAME}"
    else
        print_success "S3 bucket already exists: ${BUCKET_NAME}"
    fi

    # Create DynamoDB table for state locking
    if ! aws dynamodb describe-table --table-name "${TABLE_NAME}" --region "${AWS_REGION}" 2>&1 > /dev/null; then
        print_info "Creating DynamoDB table for state locking..."
        aws dynamodb create-table \
            --table-name "${TABLE_NAME}" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "${AWS_REGION}" > /dev/null

        print_success "Created DynamoDB table: ${TABLE_NAME}"
    else
        print_success "DynamoDB table already exists: ${TABLE_NAME}"
    fi

    echo ""
}

# Package Lambda functions
package_lambda_functions() {
    print_header "Step 3: Packaging Lambda Functions"

    cd lambda

    for dir in */; do
        function_name=$(basename "$dir")
        print_info "Packaging ${function_name}..."

        cd "$dir"

        # Install dependencies
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt -t . --upgrade > /dev/null 2>&1
        fi

        # Create deployment package
        zip -r "../${function_name}.zip" . -x "*.pyc" -x "__pycache__/*" > /dev/null

        print_success "Packaged ${function_name}.zip"

        cd ..
    done

    cd ..
    echo ""
}

# Upload ML model to S3
upload_ml_model() {
    print_header "Step 4: Uploading ML Model to S3"

    MODEL_BUCKET="anc-platform-ml-models-${AWS_ACCOUNT}"

    # Create bucket if it doesn't exist
    if ! aws s3 ls "s3://${MODEL_BUCKET}" 2>&1 > /dev/null; then
        aws s3 mb "s3://${MODEL_BUCKET}" --region "${AWS_REGION}"
        print_success "Created ML models bucket: ${MODEL_BUCKET}"
    fi

    # Upload trained model (if exists)
    if [ -f "../models/noise_classifier_model.tar.gz" ]; then
        aws s3 cp ../models/noise_classifier_model.tar.gz \
            "s3://${MODEL_BUCKET}/models/noise_classifier/model.tar.gz"
        print_success "Uploaded ML model to S3"

        MODEL_URL="s3://${MODEL_BUCKET}/models/noise_classifier/model.tar.gz"
    else
        print_info "No trained model found, will use default"
        MODEL_URL=""
    fi

    echo ""
}

# Initialize Terraform
init_terraform() {
    print_header "Step 5: Initializing Terraform"

    cd terraform

    # Update backend configuration
    cat > backend.tf <<EOF
terraform {
  backend "s3" {
    bucket         = "${BUCKET_NAME}"
    key            = "production/terraform.tfstate"
    region         = "${AWS_REGION}"
    encrypt        = true
    dynamodb_table = "${TABLE_NAME}"
  }
}
EOF

    terraform init
    print_success "Terraform initialized"

    cd ..
    echo ""
}

# Create terraform.tfvars
create_tfvars() {
    print_header "Step 6: Creating Terraform Variables"

    cd terraform

    # Prompt for required variables
    read -p "Enter environment (dev/staging/production) [production]: " ENVIRONMENT
    ENVIRONMENT=${ENVIRONMENT:-production}

    read -p "Enter database password: " -s DB_PASSWORD
    echo ""

    read -p "Enter alarm email address: " ALARM_EMAIL

    # Create tfvars file
    cat > terraform.tfvars <<EOF
# ANC Platform Configuration
# Generated: $(date)

aws_region  = "${AWS_REGION}"
environment = "${ENVIRONMENT}"

# Database
db_password = "${DB_PASSWORD}"

# Monitoring
alarm_email = "${ALARM_EMAIL}"

# SageMaker
sagemaker_model_url = "${MODEL_URL}"

# Cost Optimization
enable_spot_instances = true
enable_auto_scaling   = true
EOF

    print_success "Created terraform.tfvars"

    cd ..
    echo ""
}

# Plan and apply Terraform
deploy_infrastructure() {
    print_header "Step 7: Deploying Infrastructure"

    cd terraform

    # Terraform plan
    print_info "Running Terraform plan..."
    terraform plan -out=tfplan

    # Confirm deployment
    echo ""
    read -p "Do you want to apply this plan? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        print_error "Deployment cancelled"
        exit 1
    fi

    # Apply
    print_info "Applying Terraform configuration..."
    terraform apply tfplan

    print_success "Infrastructure deployed successfully"

    # Save outputs
    terraform output -json > ../outputs.json

    cd ..
    echo ""
}

# Configure monitoring
setup_monitoring() {
    print_header "Step 8: Configuring Monitoring"

    # Create CloudWatch dashboard
    print_info "Creating CloudWatch dashboard..."

    DASHBOARD_NAME="ANC-Platform-${ENVIRONMENT}"

    aws cloudwatch put-dashboard \
        --dashboard-name "${DASHBOARD_NAME}" \
        --dashboard-body file://monitoring/dashboard.json \
        --region "${AWS_REGION}" > /dev/null

    print_success "CloudWatch dashboard created: ${DASHBOARD_NAME}"

    echo ""
}

# Display deployment summary
deployment_summary() {
    print_header "Deployment Summary"

    # Parse Terraform outputs
    REST_API_URL=$(cat outputs.json | python3 -c "import sys, json; print(json.load(sys.stdin)['api_gateway_rest_url']['value'])")
    WS_API_URL=$(cat outputs.json | python3 -c "import sys, json; print(json.load(sys.stdin)['api_gateway_websocket_url']['value'])")
    CLOUDFRONT_DOMAIN=$(cat outputs.json | python3 -c "import sys, json; print(json.load(sys.stdin)['cloudfront_domain']['value'])")

    echo ""
    echo "Deployment completed successfully!"
    echo ""
    echo "REST API URL:       ${REST_API_URL}"
    echo "WebSocket API URL:  ${WS_API_URL}"
    echo "CloudFront Domain:  ${CLOUDFRONT_DOMAIN}"
    echo ""
    echo "Next steps:"
    echo "  1. Test API: curl ${REST_API_URL}/health"
    echo "  2. Update frontend to use: ${CLOUDFRONT_DOMAIN}"
    echo "  3. Monitor: https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:name=${DASHBOARD_NAME}"
    echo ""
}

# Main execution
main() {
    print_header "ANC Platform - AWS Cloud Deployment"
    echo ""

    check_prerequisites
    setup_terraform_backend
    package_lambda_functions
    upload_ml_model
    init_terraform
    create_tfvars
    deploy_infrastructure
    setup_monitoring
    deployment_summary

    print_success "All done!"
}

# Run main function
main
