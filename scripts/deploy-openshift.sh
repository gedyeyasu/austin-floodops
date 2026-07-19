#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

command -v oc >/dev/null 2>&1 || {
  echo "OpenShift CLI is required. Install it with: brew install openshift-cli" >&2
  exit 1
}

oc whoami >/dev/null 2>&1 || {
  echo "OpenShift login is required. Run: oc login --web <cluster-api-url>" >&2
  exit 1
}

test -f .env || {
  echo ".env is required so the deployment can create the server-side secret." >&2
  exit 1
}

PROJECT=${OPENSHIFT_PROJECT:-$(oc project -q)}
test -n "$PROJECT" || {
  echo "Select or create an OpenShift project before deploying." >&2
  exit 1
}

configure_supabase_dns_fallback() {
  # The Red Hat Developer Sandbox resolver can occasionally return NXDOMAIN
  # for a valid project-specific Supabase hostname even while other public
  # names resolve normally. Pin the current public A records into the pod's
  # /etc/hosts file on every deployment. TLS still validates the Supabase
  # hostname; only name resolution is bypassed. Set the toggle to false when
  # the cluster resolver handles the project hostname normally.
  if [[ "${OPENSHIFT_SUPABASE_DNS_FALLBACK:-true}" == "false" ]]; then
    return
  fi
  command -v dig >/dev/null 2>&1 || {
    echo "Skipping optional Supabase DNS fallback because dig is unavailable."
    return
  }

  SUPABASE_DEPLOY_URL=$(sed -n 's/^SUPABASE_URL=//p' .env | tail -1)
  SUPABASE_DEPLOY_URL=${SUPABASE_DEPLOY_URL%\"}
  SUPABASE_DEPLOY_URL=${SUPABASE_DEPLOY_URL#\"}
  SUPABASE_DEPLOY_HOST=${SUPABASE_DEPLOY_URL#*://}
  SUPABASE_DEPLOY_HOST=${SUPABASE_DEPLOY_HOST%%/*}
  if [[ ! "$SUPABASE_DEPLOY_HOST" =~ ^[A-Za-z0-9.-]+$ ]]; then
    echo "Skipping optional Supabase DNS fallback because SUPABASE_URL has no valid hostname."
    unset SUPABASE_DEPLOY_URL SUPABASE_DEPLOY_HOST
    return
  fi

  SUPABASE_DEPLOY_IPS=$(dig +short A "$SUPABASE_DEPLOY_HOST" | awk '/^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/' | head -2)
  SUPABASE_DEPLOY_IP_PRIMARY=$(printf '%s\n' "$SUPABASE_DEPLOY_IPS" | sed -n '1p')
  SUPABASE_DEPLOY_IP_SECONDARY=$(printf '%s\n' "$SUPABASE_DEPLOY_IPS" | sed -n '2p')
  if [[ -z "$SUPABASE_DEPLOY_IP_PRIMARY" ]]; then
    echo "Skipping optional Supabase DNS fallback because no public IPv4 address was found."
    unset SUPABASE_DEPLOY_URL SUPABASE_DEPLOY_HOST SUPABASE_DEPLOY_IPS SUPABASE_DEPLOY_IP_PRIMARY SUPABASE_DEPLOY_IP_SECONDARY
    return
  fi

  if [[ -n "$SUPABASE_DEPLOY_IP_SECONDARY" ]]; then
    SUPABASE_HOST_ALIASES=$(printf '{"spec":{"template":{"spec":{"hostAliases":[{"ip":"%s","hostnames":["%s"]},{"ip":"%s","hostnames":["%s"]}]}}}}' \
      "$SUPABASE_DEPLOY_IP_PRIMARY" "$SUPABASE_DEPLOY_HOST" \
      "$SUPABASE_DEPLOY_IP_SECONDARY" "$SUPABASE_DEPLOY_HOST")
  else
    SUPABASE_HOST_ALIASES=$(printf '{"spec":{"template":{"spec":{"hostAliases":[{"ip":"%s","hostnames":["%s"]}]}}}}' \
      "$SUPABASE_DEPLOY_IP_PRIMARY" "$SUPABASE_DEPLOY_HOST")
  fi
  oc patch deployment austin-floodops --type=merge -p "$SUPABASE_HOST_ALIASES" >/dev/null
  echo "Configured the OpenShift Supabase DNS fallback for $SUPABASE_DEPLOY_HOST."
  unset SUPABASE_DEPLOY_URL SUPABASE_DEPLOY_HOST SUPABASE_DEPLOY_IPS SUPABASE_DEPLOY_IP_PRIMARY SUPABASE_DEPLOY_IP_SECONDARY SUPABASE_HOST_ALIASES
}

echo "Deploying Austin FloodOps to OpenShift project: $PROJECT"

# Values stay in the cluster Secret. The command never prints secret data and
# .dockerignore prevents .env from entering the binary build context.
oc create secret generic floodops-secrets \
  --from-env-file=.env \
  --dry-run=client \
  -o yaml | oc apply -f - >/dev/null

# Generate stable production-only authentication secrets once. They never
# enter .env, Git, the container image, or command output.
if ! oc get secret floodops-auth >/dev/null 2>&1; then
  JWT_SECRET=$(openssl rand -hex 32)
  AUTH_BOOTSTRAP_TOKEN=$(openssl rand -hex 32)
  oc create secret generic floodops-auth \
    --from-literal=JWT_SECRET="$JWT_SECRET" \
    --from-literal=AUTH_BOOTSTRAP_TOKEN="$AUTH_BOOTSTRAP_TOKEN" >/dev/null
  unset JWT_SECRET AUTH_BOOTSTRAP_TOKEN
fi

if [[ -n "${DEMO_LOGIN_EMAIL:-}" && -n "${DEMO_LOGIN_PASSWORD:-}" ]]; then
  DEMO_LOGIN_PEPPER=$(oc get secret floodops-auth -o jsonpath='{.data.AUTH_BOOTSTRAP_TOKEN}' | base64 --decode)
  DEMO_LOGIN_PASSWORD_HMAC=$(printf '%s' "$DEMO_LOGIN_PASSWORD" | openssl dgst -sha256 -hmac "$DEMO_LOGIN_PEPPER" -binary | xxd -p -c 256)
  oc create secret generic floodops-demo-login \
    --from-literal=DEMO_LOGIN_EMAIL="$DEMO_LOGIN_EMAIL" \
    --from-literal=DEMO_LOGIN_PASSWORD_HMAC="$DEMO_LOGIN_PASSWORD_HMAC" \
    --dry-run=client -o yaml | oc apply -f - >/dev/null
  unset DEMO_LOGIN_PASSWORD DEMO_LOGIN_PASSWORD_HMAC DEMO_LOGIN_PEPPER
fi

oc process -f deploy/openshift-template.yaml \
  -p NAMESPACE="$PROJECT" | oc apply -f -

configure_supabase_dns_fallback

oc start-build austin-floodops --from-dir=. --follow --wait
oc rollout status statefulset/redpanda --timeout=300s
oc rollout status deployment/austin-floodops --timeout=300s

ROUTE_HOST=$(oc get route austin-floodops -o jsonpath='{.spec.host}')
APP_URL="https://${ROUTE_HOST}"

curl --fail --silent --show-error --retry 12 --retry-all-errors \
  --retry-delay 5 "$APP_URL/health" >/dev/null

echo "Austin FloodOps is live: $APP_URL"
echo "Health check passed: $APP_URL/health"
echo "Copy the operator bootstrap token to your clipboard with:"
echo "oc get secret floodops-auth -o jsonpath='{.data.AUTH_BOOTSTRAP_TOKEN}' | base64 --decode | pbcopy"
