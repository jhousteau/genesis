#!/bin/bash

# Deploy Monitoring Automation for Universal Platform
# This script sets up the complete monitoring automation stack

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-monitoring}"
ENVIRONMENT="${ENVIRONMENT:-production}"
CONFIG_DIR="${CONFIG_DIR:-./config}"
ORCHESTRATOR_IMAGE="${ORCHESTRATOR_IMAGE:-universal-platform/monitoring-orchestrator:latest}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi

    # Check if we can connect to Kubernetes
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    # Check if docker is available for building
    if ! command -v docker &> /dev/null; then
        log_warn "Docker is not available, will skip image building"
    fi

    # Check if helm is available
    if command -v helm &> /dev/null; then
        log_info "Helm detected, will use for deployment"
        USE_HELM=true
    else
        log_info "Helm not detected, will use kubectl"
        USE_HELM=false
    fi

    log_info "Prerequisites check completed"
}

# Create namespace
create_namespace() {
    log_info "Creating namespace: $NAMESPACE"

    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    kubectl label namespace "$NAMESPACE" name="$NAMESPACE" --overwrite

    log_info "Namespace $NAMESPACE ready"
}

# Create service account and RBAC
create_rbac() {
    log_info "Creating RBAC configuration..."

    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: monitoring-orchestrator
  namespace: $NAMESPACE
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: monitoring-orchestrator
rules:
- apiGroups: [""]
  resources: ["services", "pods", "endpoints", "nodes", "configmaps"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets", "daemonsets", "statefulsets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["extensions", "networking.k8s.io"]
  resources: ["ingresses"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["monitoring.coreos.com"]
  resources: ["servicemonitors", "prometheusrules"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: monitoring-orchestrator
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: monitoring-orchestrator
subjects:
- kind: ServiceAccount
  name: monitoring-orchestrator
  namespace: $NAMESPACE
EOF

    log_info "RBAC configuration created"
}

# Create ConfigMaps for configuration
create_config_maps() {
    log_info "Creating configuration ConfigMaps..."

    # Create orchestrator config
    kubectl create configmap orchestrator-config \
        --from-file=orchestrator-config.yaml \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -

    # Create discovery config
    kubectl create configmap discovery-config \
        --from-file=discovery-config.yaml \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -

    # Create config manager config
    kubectl create configmap config-manager-config \
        --from-file=config-manager.yaml \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -

    # Create templates configmap if directory exists
    if [ -d "templates" ]; then
        kubectl create configmap orchestrator-templates \
            --from-file=templates/ \
            --namespace="$NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
    fi

    log_info "Configuration ConfigMaps created"
}

# Create PersistentVolumeClaims
create_storage() {
    log_info "Creating storage resources..."

    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: orchestrator-data
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: fast-ssd
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: prometheus-config
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: fast-ssd
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: grafana-config
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: fast-ssd
EOF

    log_info "Storage resources created"
}

# Build Docker image
build_image() {
    if ! command -v docker &> /dev/null; then
        log_warn "Docker not available, skipping image build"
        return
    fi

    log_info "Building monitoring orchestrator image..."

    # Create Dockerfile
    cat <<EOF > Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    jq \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./
COPY *.yaml ./
COPY templates/ ./templates/

# Create necessary directories
RUN mkdir -p /var/lib/monitoring /var/log /etc/prometheus/targets /etc/grafana/provisioning

# Set permissions
RUN chmod +x *.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:8081/health || exit 1

# Default command
CMD ["python", "orchestrator.py", "--daemon"]
EOF

    # Create requirements.txt
    cat <<EOF > requirements.txt
kubernetes>=24.2.0
requests>=2.28.0
pyyaml>=6.0
jinja2>=3.1.0
python-consul>=1.1.0
asyncio>=3.4.3
prometheus-client>=0.14.0
EOF

    # Build image
    IMAGE_TAG="${DOCKER_REGISTRY}${ORCHESTRATOR_IMAGE}"
    docker build -t "$IMAGE_TAG" .

    # Push to registry if specified
    if [ -n "$DOCKER_REGISTRY" ]; then
        log_info "Pushing image to registry..."
        docker push "$IMAGE_TAG"
    fi

    log_info "Image built: $IMAGE_TAG"
}

# Deploy orchestrator
deploy_orchestrator() {
    log_info "Deploying monitoring orchestrator..."

    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: monitoring-orchestrator
  namespace: $NAMESPACE
  labels:
    app: monitoring-orchestrator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: monitoring-orchestrator
  template:
    metadata:
      labels:
        app: monitoring-orchestrator
    spec:
      serviceAccountName: monitoring-orchestrator
      containers:
      - name: orchestrator
        image: ${DOCKER_REGISTRY}${ORCHESTRATOR_IMAGE}
        args: ["--daemon"]
        env:
        - name: LOG_LEVEL
          value: "INFO"
        - name: ENVIRONMENT
          value: "$ENVIRONMENT"
        - name: NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        ports:
        - containerPort: 8080
          name: api
        - containerPort: 8081
          name: health
        - containerPort: 9090
          name: metrics
        livenessProbe:
          httpGet:
            path: /health
            port: 8081
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8081
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        volumeMounts:
        - name: orchestrator-config
          mountPath: /app/orchestrator-config.yaml
          subPath: orchestrator-config.yaml
        - name: discovery-config
          mountPath: /app/discovery-config.yaml
          subPath: discovery-config.yaml
        - name: config-manager-config
          mountPath: /app/config-manager.yaml
          subPath: config-manager.yaml
        - name: templates
          mountPath: /app/templates
        - name: data
          mountPath: /var/lib/monitoring
        - name: prometheus-config
          mountPath: /etc/prometheus
        - name: grafana-config
          mountPath: /etc/grafana
      volumes:
      - name: orchestrator-config
        configMap:
          name: orchestrator-config
      - name: discovery-config
        configMap:
          name: discovery-config
      - name: config-manager-config
        configMap:
          name: config-manager-config
      - name: templates
        configMap:
          name: orchestrator-templates
      - name: data
        persistentVolumeClaim:
          claimName: orchestrator-data
      - name: prometheus-config
        persistentVolumeClaim:
          claimName: prometheus-config
      - name: grafana-config
        persistentVolumeClaim:
          claimName: grafana-config
---
apiVersion: v1
kind: Service
metadata:
  name: monitoring-orchestrator
  namespace: $NAMESPACE
  labels:
    app: monitoring-orchestrator
spec:
  selector:
    app: monitoring-orchestrator
  ports:
  - name: api
    port: 8080
    targetPort: 8080
  - name: health
    port: 8081
    targetPort: 8081
  - name: metrics
    port: 9090
    targetPort: 9090
  type: ClusterIP
EOF

    log_info "Monitoring orchestrator deployed"
}

# Create ServiceMonitor for Prometheus
create_service_monitor() {
    log_info "Creating ServiceMonitor for monitoring..."

    cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: monitoring-orchestrator
  namespace: $NAMESPACE
  labels:
    app: monitoring-orchestrator
spec:
  selector:
    matchLabels:
      app: monitoring-orchestrator
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
EOF

    log_info "ServiceMonitor created"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    # Wait for deployment to be ready
    kubectl rollout status deployment/monitoring-orchestrator -n "$NAMESPACE" --timeout=300s

    # Check pod status
    kubectl get pods -n "$NAMESPACE" -l app=monitoring-orchestrator

    # Check service status
    kubectl get svc -n "$NAMESPACE" -l app=monitoring-orchestrator

    # Test health endpoint
    log_info "Testing health endpoint..."
    if kubectl exec -n "$NAMESPACE" deployment/monitoring-orchestrator -- curl -f http://localhost:8081/health; then
        log_info "Health check passed"
    else
        log_error "Health check failed"
        return 1
    fi

    # Test API endpoint
    log_info "Testing API endpoint..."
    if kubectl exec -n "$NAMESPACE" deployment/monitoring-orchestrator -- curl -f http://localhost:8080/status; then
        log_info "API check passed"
    else
        log_error "API check failed"
        return 1
    fi

    log_info "Deployment verification completed successfully"
}

# Show status
show_status() {
    log_info "Monitoring Automation Status:"
    echo ""

    echo "Namespace: $NAMESPACE"
    echo "Environment: $ENVIRONMENT"
    echo ""

    echo "Pods:"
    kubectl get pods -n "$NAMESPACE" -l app=monitoring-orchestrator
    echo ""

    echo "Services:"
    kubectl get svc -n "$NAMESPACE" -l app=monitoring-orchestrator
    echo ""

    echo "ConfigMaps:"
    kubectl get configmaps -n "$NAMESPACE" | grep -E "(orchestrator|discovery|config-manager)"
    echo ""

    echo "PVCs:"
    kubectl get pvc -n "$NAMESPACE"
    echo ""

    # Get orchestrator status via API
    POD_NAME=$(kubectl get pods -n "$NAMESPACE" -l app=monitoring-orchestrator -o jsonpath='{.items[0].metadata.name}')
    if [ -n "$POD_NAME" ]; then
        echo "Orchestrator Status:"
        kubectl exec -n "$NAMESPACE" "$POD_NAME" -- curl -s http://localhost:8080/status | jq '.' 2>/dev/null || echo "Status endpoint not available"
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up monitoring automation..."

    kubectl delete deployment monitoring-orchestrator -n "$NAMESPACE" --ignore-not-found
    kubectl delete service monitoring-orchestrator -n "$NAMESPACE" --ignore-not-found
    kubectl delete servicemonitor monitoring-orchestrator -n "$NAMESPACE" --ignore-not-found
    kubectl delete configmap orchestrator-config discovery-config config-manager-config orchestrator-templates -n "$NAMESPACE" --ignore-not-found
    kubectl delete pvc orchestrator-data prometheus-config grafana-config -n "$NAMESPACE" --ignore-not-found
    kubectl delete clusterrolebinding monitoring-orchestrator --ignore-not-found
    kubectl delete clusterrole monitoring-orchestrator --ignore-not-found
    kubectl delete serviceaccount monitoring-orchestrator -n "$NAMESPACE" --ignore-not-found

    log_info "Cleanup completed"
}

# Main function
main() {
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            create_namespace
            create_rbac
            create_storage
            create_config_maps
            build_image
            deploy_orchestrator
            create_service_monitor
            verify_deployment
            show_status
            ;;
        "status")
            show_status
            ;;
        "cleanup")
            cleanup
            ;;
        "update")
            create_config_maps
            kubectl rollout restart deployment/monitoring-orchestrator -n "$NAMESPACE"
            verify_deployment
            ;;
        *)
            echo "Usage: $0 [deploy|status|cleanup|update]"
            echo ""
            echo "Commands:"
            echo "  deploy  - Deploy the monitoring automation stack (default)"
            echo "  status  - Show deployment status"
            echo "  cleanup - Remove all monitoring automation resources"
            echo "  update  - Update configuration and restart"
            echo ""
            echo "Environment Variables:"
            echo "  NAMESPACE          - Kubernetes namespace (default: monitoring)"
            echo "  ENVIRONMENT        - Environment name (default: production)"
            echo "  DOCKER_REGISTRY    - Docker registry prefix"
            echo "  ORCHESTRATOR_IMAGE - Orchestrator image name"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
