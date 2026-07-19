# Austin FloodOps deployment

## Recommended hackathon deployment

Use Red Hat OpenShift for the application runtime and the internal Kafka-compatible stream. Keep Supabase as the remote PostgreSQL mirror for events, decisions, and operator feedback.

Supabase Edge Functions are not a fit for the existing application server. They run Deno-compatible functions with bounded request and background-task duration; Austin FloodOps is a Python FastAPI server with an always-on polling heartbeat and Kafka consumer. Rewriting that runtime for an edge function would remove the tested deployment path without improving the demo.

The OpenShift deployment contains:

- one FastAPI application pod exposed through a Transport Layer Security route;
- one persistent volume for the local SQLite decision and audit ledger;
- one single-broker Redpanda StatefulSet and persistent volume for the hackathon streaming demonstration;
- one OpenShift Secret populated from the local uncommitted `.env` file;
- one OpenShift binary build so the private GitHub repository does not need to be made public or given to the cluster.

The single Redpanda broker is a real Kafka-compatible stream, not a mock. It is intentionally a hackathon-sized deployment rather than a fault-tolerant production cluster. A production government deployment would use at least three brokers across separate worker nodes or an approved managed Kafka-compatible service.

## Deploy

1. Install the official OpenShift command-line interface:

   ```bash
   brew install openshift-cli
   ```

2. In the OpenShift web console, open the user menu and choose **Copy login command**, or use browser login with the cluster application programming interface address:

   ```bash
   oc login --web https://api.<cluster-domain>:6443
   ```

3. Select the hackathon OpenShift project and deploy:

   ```bash
   oc project <project-name>
   ./scripts/deploy-openshift.sh
   ```

The script uploads the local source as a binary build, waits for Redpanda and the application, discovers the public route, and requires the `/health` endpoint to return successfully.

## Authentication for the public route

The OpenShift deployment forces role-based access control on. Visitors without a token receive the `viewer` role: they can inspect public source evidence and existing decisions but cannot run NVIDIA inference, simulations, approvals, feedback, exports, or responder delivery.

The deployment script generates independent `JWT_SECRET` and `AUTH_BOOTSTRAP_TOKEN` values inside an OpenShift Secret the first time it runs. They never enter `.env`, Git, or the container image. Copy the bootstrap token to the local clipboard when an authorized operator needs it:

```bash
oc get secret floodops-auth -o jsonpath='{.data.AUTH_BOOTSTRAP_TOKEN}' | base64 --decode | pbcopy
```

The operator pastes it into the dashboard's role switcher to request an in-memory token. The browser never stores that token in local storage.

For a shareable hackathon demonstration, the deploy script can create a separate email/password Secret without committing plaintext credentials:

```bash
DEMO_LOGIN_EMAIL='operator@example.com' DEMO_LOGIN_PASSWORD='<demo-password>' ./scripts/deploy-openshift.sh
```

The script stores only a keyed SHA-256 password digest in OpenShift; the independent authentication bootstrap secret is the key, so the stored digest is not a reusable plain password hash. Successful demo login issues an eight-hour `supervisor` token in browser memory. Anonymous visitors remain read-only, and failed login responses never reveal whether the email or password was incorrect.

## Supabase credit

Use the hackathon Supabase credit for the existing hosted project, database storage, application programming interface traffic, logs, and backups. The service-role key remains only in the OpenShift Secret and is never sent to browser JavaScript. Supabase is the remote mirror; the OpenShift persistent volume keeps the application ledger available during a Supabase outage.

## Other deployment options

- **Render free web service:** easiest fallback for the FastAPI container, but it sleeps after 15 minutes without inbound traffic and has an ephemeral filesystem. That breaks the always-on heartbeat unless a paid instance and external durable store are used.
- **Google Cloud Run:** strong container fallback with a free usage allowance, but an always-on polling worker needs instance-based billing or a separate scheduled worker. A hosted Kafka service is also still required.
- **Railway trial:** quick Docker deployment, but trial credit and duration are account-specific and the application still needs durable storage and Kafka.

For this hackathon, OpenShift is the best fit because it keeps the live-data agent awake, runs the tested container, hosts the real stream, and visibly uses the Red Hat sponsor platform.
