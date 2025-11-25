#!/bin/bash
# Setup HTTPS/SSL for EUI Icon Embeddings services on GCP
# This script sets up Cloud Load Balancer with Google-managed SSL certificates

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration variables (update these)
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-your-project-id}"
REGION="${REGION:-us-central1}"
FRONTEND_DOMAIN="${FRONTEND_DOMAIN:-icons.example.com}"
API_DOMAIN="${API_DOMAIN:-api.icons.example.com}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-eui-frontend}"
API_SERVICE="${API_SERVICE:-eui-python-api}"

echo -e "${GREEN}Setting up HTTPS for EUI Icon Embeddings${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Frontend Domain: $FRONTEND_DOMAIN"
echo "API Domain: $API_DOMAIN"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    exit 1
fi

# Set the project
gcloud config set project "$PROJECT_ID"

# Step 1: Reserve static IP address
echo -e "${YELLOW}Step 1: Reserving static IP address...${NC}"
if gcloud compute addresses describe eui-icons-ip --global &> /dev/null; then
    echo "Static IP already exists, skipping..."
else
    gcloud compute addresses create eui-icons-ip --global
    echo -e "${GREEN}Static IP reserved${NC}"
fi

LB_IP=$(gcloud compute addresses describe eui-icons-ip --global --format='value(address)')
echo "Load Balancer IP: $LB_IP"
echo ""
echo -e "${YELLOW}Please configure your DNS records:${NC}"
echo "  $FRONTEND_DOMAIN     A     $LB_IP"
echo "  $API_DOMAIN          A     $LB_IP"
echo ""
read -p "Press Enter after DNS records are configured..."

# Step 2: Create SSL certificate
echo -e "${YELLOW}Step 2: Creating SSL certificate...${NC}"
if gcloud compute ssl-certificates describe eui-icons-ssl-cert --global &> /dev/null; then
    echo "SSL certificate already exists, skipping..."
else
    gcloud compute ssl-certificates create eui-icons-ssl-cert \
        --domains="$FRONTEND_DOMAIN,$API_DOMAIN" \
        --global
    echo -e "${GREEN}SSL certificate created${NC}"
    echo -e "${YELLOW}Note: Certificate provisioning may take 30-60 minutes${NC}"
fi

# Step 3: Create health checks
echo -e "${YELLOW}Step 3: Creating health checks...${NC}"
if gcloud compute health-checks describe eui-python-api-health-check --global &> /dev/null; then
    echo "Python API health check already exists, skipping..."
else
    gcloud compute health-checks create http eui-python-api-health-check \
        --port 8000 \
        --request-path /health \
        --global
    echo -e "${GREEN}Python API health check created${NC}"
fi

if gcloud compute health-checks describe eui-frontend-health-check --global &> /dev/null; then
    echo "Frontend health check already exists, skipping..."
else
    gcloud compute health-checks create http eui-frontend-health-check \
        --port 3000 \
        --request-path / \
        --global
    echo -e "${GREEN}Frontend health check created${NC}"
fi

# Step 4: Create Serverless NEGs
echo -e "${YELLOW}Step 4: Creating Serverless Network Endpoint Groups...${NC}"
if gcloud compute network-endpoint-groups describe eui-python-api-neg --region="$REGION" &> /dev/null; then
    echo "Python API NEG already exists, skipping..."
else
    gcloud compute network-endpoint-groups create eui-python-api-neg \
        --region="$REGION" \
        --network-endpoint-type=serverless \
        --cloud-run-service="$API_SERVICE"
    echo -e "${GREEN}Python API NEG created${NC}"
fi

if gcloud compute network-endpoint-groups describe eui-frontend-neg --region="$REGION" &> /dev/null; then
    echo "Frontend NEG already exists, skipping..."
else
    gcloud compute network-endpoint-groups create eui-frontend-neg \
        --region="$REGION" \
        --network-endpoint-type=serverless \
        --cloud-run-service="$FRONTEND_SERVICE"
    echo -e "${GREEN}Frontend NEG created${NC}"
fi

# Step 5: Create backend services
echo -e "${YELLOW}Step 5: Creating backend services...${NC}"
if gcloud compute backend-services describe eui-python-api-backend --global &> /dev/null; then
    echo "Python API backend service already exists, skipping..."
else
    gcloud compute backend-services create eui-python-api-backend \
        --global \
        --protocol HTTP \
        --health-checks eui-python-api-health-check \
        --port-name http
    echo -e "${GREEN}Python API backend service created${NC}"
fi

if gcloud compute backend-services describe eui-frontend-backend --global &> /dev/null; then
    echo "Frontend backend service already exists, skipping..."
else
    gcloud compute backend-services create eui-frontend-backend \
        --global \
        --protocol HTTP \
        --health-checks eui-frontend-health-check \
        --port-name http
    echo -e "${GREEN}Frontend backend service created${NC}"
fi

# Add NEGs to backend services
echo "Adding NEGs to backend services..."
gcloud compute backend-services add-backend eui-python-api-backend \
    --global \
    --network-endpoint-group eui-python-api-neg \
    --network-endpoint-group-region "$REGION" 2>/dev/null || echo "Python API backend already configured"

gcloud compute backend-services add-backend eui-frontend-backend \
    --global \
    --network-endpoint-group eui-frontend-neg \
    --network-endpoint-group-region "$REGION" 2>/dev/null || echo "Frontend backend already configured"

# Step 6: Create URL map
echo -e "${YELLOW}Step 6: Creating URL map...${NC}"
if gcloud compute url-maps describe eui-icons-url-map --global &> /dev/null; then
    echo "URL map already exists, skipping..."
else
    gcloud compute url-maps create eui-icons-url-map \
        --default-service eui-frontend-backend \
        --global
    echo -e "${GREEN}URL map created${NC}"
fi

# Add host rule for API subdomain
gcloud compute url-maps add-host-rule eui-icons-url-map \
    --hosts "$API_DOMAIN" \
    --default-service eui-python-api-backend \
    --global 2>/dev/null || echo "API host rule already exists"

# Step 7: Create HTTPS target proxy
echo -e "${YELLOW}Step 7: Creating HTTPS target proxy...${NC}"
if gcloud compute target-https-proxies describe eui-icons-https-proxy --global &> /dev/null; then
    echo "HTTPS target proxy already exists, skipping..."
else
    gcloud compute target-https-proxies create eui-icons-https-proxy \
        --url-map eui-icons-url-map \
        --ssl-certificates eui-icons-ssl-cert \
        --global
    echo -e "${GREEN}HTTPS target proxy created${NC}"
fi

# Step 8: Create forwarding rule
echo -e "${YELLOW}Step 8: Creating forwarding rule...${NC}"
if gcloud compute forwarding-rules describe eui-icons-https-forwarding-rule --global &> /dev/null; then
    echo "Forwarding rule already exists, skipping..."
else
    gcloud compute forwarding-rules create eui-icons-https-forwarding-rule \
        --global \
        --target-https-proxy eui-icons-https-proxy \
        --ports 443 \
        --address "$LB_IP"
    echo -e "${GREEN}Forwarding rule created${NC}"
fi

echo ""
echo -e "${GREEN}HTTPS setup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Wait for SSL certificate provisioning (check status with):"
echo "   gcloud compute ssl-certificates describe eui-icons-ssl-cert --global"
echo ""
echo "2. Update Cloud Run services with HTTPS URLs:"
echo "   See docs/HTTPS_SETUP.md for service configuration commands"
echo ""
echo "3. Test your endpoints:"
echo "   curl https://$FRONTEND_DOMAIN"
echo "   curl https://$API_DOMAIN/health"
echo ""

