#!/bin/bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y curl unzip docker.io docker-compose-v2 snapd

# Install AWS CLI v2 using the official AWS installer.
curl -fsSL https://awscli.amazonaws.com/v2/install.sh | bash -s -- --system

# Docker
systemctl enable --now docker
usermod -aG docker ubuntu

# SSM Agent
snap install amazon-ssm-agent --classic
systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service

# JalOS directories
install -d -m 0750 -o root -g root /opt/jalos
install -d -m 0750 -o root -g root /opt/jalos/models

# Deployment configuration
cat > /etc/default/jalos-deploy <<'ENV'
JALOS_AWS_REGION='${aws_region}'
JALOS_BUCKET='${bucket_name}'
JALOS_DEPLOY_ENV='${environment}'
JALOS_RUNTIME_PARAMETER='${runtime_parameter_name}'
ENV

chmod 0600 /etc/default/jalos-deploy

source /etc/default/jalos-deploy

# Wait for the EC2 instance profile credentials to become available.
for attempt in $(seq 1 30); do
  if aws sts get-caller-identity \
    --region "$JALOS_AWS_REGION" >/dev/null 2>&1; then
    break
  fi

  sleep 2
done

# Verify that AWS credentials are actually available.
if ! aws sts get-caller-identity \
  --region "$JALOS_AWS_REGION" >/dev/null 2>&1; then

  echo "ERROR: EC2 instance profile credentials are unavailable." >&2
  exit 1
fi

# Fetch runtime environment from SSM Parameter Store.
aws --region "$JALOS_AWS_REGION" ssm get-parameter \
  --name "$JALOS_RUNTIME_PARAMETER" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text > /opt/jalos/.env

chmod 0600 /opt/jalos/.env

# Make sure SSM Agent is running after the instance profile is available.
systemctl restart snap.amazon-ssm-agent.amazon-ssm-agent.service

# -------------------------------------------------------------------
# JalOS deployment script
# -------------------------------------------------------------------

cat > /usr/local/sbin/jalos-deploy <<'DEPLOY'
#!/bin/bash
set -euo pipefail

source /etc/default/jalos-deploy

if [[ "$#" -ne 1 ]]; then
  echo "Expected a full 40-character Git commit SHA." >&2
  exit 2
fi

release_id="$1"

if [[ ! "$release_id" =~ ^[a-f0-9]{40}$ ]]; then
  echo "Expected a full 40-character Git commit SHA." >&2
  exit 2
fi

release_prefix="deploy/$JALOS_DEPLOY_ENV/$release_id"

echo "========================================"
echo "JalOS deployment"
echo "Release: $release_id"
echo "Environment: $JALOS_DEPLOY_ENV"
echo "========================================"

# -------------------------------------------------------------------
# Download backend image
# -------------------------------------------------------------------

echo "Downloading backend image..."

aws --region "$JALOS_AWS_REGION" s3 cp \
  "s3://$JALOS_BUCKET/$release_prefix/backend.tar.gz" \
  /tmp/jalos-backend.tar.gz

# -------------------------------------------------------------------
# Download admin-web image
# -------------------------------------------------------------------

echo "Downloading admin-web image..."

aws --region "$JALOS_AWS_REGION" s3 cp \
  "s3://$JALOS_BUCKET/$release_prefix/admin-web.tar.gz" \
  /tmp/jalos-admin-web.tar.gz

# -------------------------------------------------------------------
# Download Docker Compose configuration
# -------------------------------------------------------------------

echo "Downloading Docker Compose configuration..."

aws --region "$JALOS_AWS_REGION" s3 cp \
  "s3://$JALOS_BUCKET/$release_prefix/docker-compose.production.yml" \
  /opt/jalos/docker-compose.production.yml

chmod 0644 /opt/jalos/docker-compose.production.yml

# -------------------------------------------------------------------
# Download and validate ML model
# -------------------------------------------------------------------

echo "Downloading forecast model..."

aws --region "$JALOS_AWS_REGION" s3 cp \
  "s3://$JALOS_BUCKET/$release_prefix/forecast-model.json" \
  /opt/jalos/models/water-demand-ridge-v1.json.tmp

echo "Validating forecast model..."

python3 -c '
import json
import sys

path = sys.argv[1]

with open(path, encoding="utf-8") as f:
    model = json.load(f)

assert model.get("model_name"), "Missing model_name"
assert model.get("version"), "Missing version"

coefficients = model.get("coefficients", [])
feature_count = model.get("feature_count")

assert isinstance(coefficients, list), "coefficients must be a list"
assert feature_count is not None, "Missing feature_count"
assert len(coefficients) == feature_count, (
    f"Coefficient count {len(coefficients)} "
    f"does not match feature count {feature_count}"
)

print("Forecast model validation successful.")
' /opt/jalos/models/water-demand-ridge-v1.json.tmp

install \
  -o root \
  -g root \
  -m 0644 \
  /opt/jalos/models/water-demand-ridge-v1.json.tmp \
  /opt/jalos/models/water-demand-ridge-v1.json

rm -f /opt/jalos/models/water-demand-ridge-v1.json.tmp

# -------------------------------------------------------------------
# Load Docker images
# -------------------------------------------------------------------

echo "Loading backend Docker image..."

docker load \
  --input /tmp/jalos-backend.tar.gz

echo "Loading admin-web Docker image..."

docker load \
  --input /tmp/jalos-admin-web.tar.gz

# Remove temporary image archives.
rm -f \
  /tmp/jalos-backend.tar.gz \
  /tmp/jalos-admin-web.tar.gz

# -------------------------------------------------------------------
# Update runtime environment
# -------------------------------------------------------------------

echo "Updating runtime environment..."

grep -v '^JALOS_IMAGE_TAG=' \
  /opt/jalos/.env > /tmp/jalos-runtime.env || true

printf 'JALOS_IMAGE_TAG=%s\n' "$release_id" \
  >> /tmp/jalos-runtime.env

install \
  -o root \
  -g root \
  -m 0600 \
  /tmp/jalos-runtime.env \
  /opt/jalos/.env

rm -f /tmp/jalos-runtime.env

# -------------------------------------------------------------------
# Validate deployment files
# -------------------------------------------------------------------

echo "Validating Docker Compose configuration..."

cd /opt/jalos

docker compose \
  --env-file /opt/jalos/.env \
  -f /opt/jalos/docker-compose.production.yml \
  config > /tmp/jalos-compose-config.yml

# -------------------------------------------------------------------
# Start / update application
# -------------------------------------------------------------------

echo "Starting JalOS containers..."

docker compose \
  --env-file /opt/jalos/.env \
  -f /opt/jalos/docker-compose.production.yml \
  up -d --remove-orphans

# -------------------------------------------------------------------
# Health check
# -------------------------------------------------------------------

echo "Waiting for JalOS health endpoint..."

for attempt in $(seq 1 30); do

  if curl \
    --fail \
    --silent \
    http://127.0.0.1/health > /dev/null; then

    echo "========================================"
    echo "JalOS release $release_id is healthy."
    echo "========================================"

    docker compose \
      --env-file /opt/jalos/.env \
      -f /opt/jalos/docker-compose.production.yml \
      ps

    exit 0
  fi

  sleep 5
done

# -------------------------------------------------------------------
# Deployment failure diagnostics
# -------------------------------------------------------------------

echo "========================================"
echo "JalOS health check FAILED."
echo "Release: $release_id"
echo "========================================"

docker compose \
  --env-file /opt/jalos/.env \
  -f /opt/jalos/docker-compose.production.yml \
  ps || true

echo ""
echo "Backend logs:"
docker compose \
  --env-file /opt/jalos/.env \
  -f /opt/jalos/docker-compose.production.yml \
  logs --tail=100 backend || true

echo ""
echo "Admin-web logs:"
docker compose \
  --env-file /opt/jalos/.env \
  -f /opt/jalos/docker-compose.production.yml \
  logs --tail=100 admin-web || true

exit 1
DEPLOY

chmod 0750 /usr/local/sbin/jalos-deploy