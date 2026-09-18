# Deploying to AWS

Django API on **Lambda + API Gateway**, React on **S3 + CloudFront**, database
stays on **Supabase**.

There is no RDS, no VPC and no security groups here — the database is already
hosted and reachable over the internet, which removes the fiddliest part of a
first AWS deploy.

---

## Before anything else: rotate two secrets

Both of these are currently exposed, and both must change *before* this is
reachable from the internet.

**1. The Django secret key.** It is committed to the public repo, and it signs
every JWT this API issues — anyone who reads the repo can forge a token for
any user, including a staff one. Generate a new one:

```bash
.venv/Scripts/python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Keep the output somewhere safe. It goes into the deploy as `DjangoSecretKey`
and never into git.

**2. The Supabase database password.** Dashboard → Settings → Database → Reset
database password. Then update your local `.env` with the new string.

---

## Deploying into a workshop / shared account

If the account was handed to you rather than created by you, three things
differ.

**You probably cannot create IAM roles.** That is why a Lambda execution role
is usually supplied along with the login. Pass its ARN as the `LambdaRoleArn`
parameter and the template will use it instead of trying to make one. Left
empty, SAM creates its own — correct only in an account you control.

**Your secrets are visible to the account's administrators.** Lambda
environment variables are stored in plaintext and readable by anyone who can
call `lambda:GetFunctionConfiguration`, which includes the console. Secrets
Manager does not change this — admins can read that too. Either point the
deploy at a throwaway database, or reset the Supabase password the moment the
workshop ends.

**Assume it will be deleted.** Workshop accounts are typically reclaimed. For
a deployment you want to keep and link to, use your own account.

---

## One-time setup

```bash
aws configure                     # access key, secret, region
winget install Amazon.SAM-CLI     # then restart the terminal
sam --version                     # confirm it is on PATH
```

Given console access but no access key, make one for yourself: **IAM → Users →
your username → Security credentials → Create access key → Command Line
Interface (CLI)**. The secret is shown once.

Confirm it worked, and that you are who you expect to be:

```bash
aws sts get-caller-identity
```

### When PowerUserAccess and IAMFullAccess are not in the list

A restricted account hides most managed policies. Attach an **inline policy**
instead — IAM → the user → Add permissions → Create inline policy → JSON.

This grants what a SAM deploy actually performs, and nothing else. Because the
Lambda execution role is supplied rather than created, no `iam:CreateRole` is
needed — only permission to *pass* the role that already exists, which is a far
easier thing to be granted:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TheStackItself",
      "Effect": "Allow",
      "Action": ["cloudformation:*"],
      "Resource": "*"
    },
    {
      "Sid": "SamUploadsTheBuildHere",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket", "s3:ListBucket", "s3:GetBucketLocation",
        "s3:PutObject", "s3:GetObject", "s3:DeleteObject",
        "s3:PutBucketPolicy", "s3:PutBucketTagging",
        "s3:PutEncryptionConfiguration", "s3:PutBucketVersioning"
      ],
      "Resource": "*"
    },
    {
      "Sid": "TheFunctionAndItsApi",
      "Effect": "Allow",
      "Action": ["lambda:*", "apigateway:*", "logs:*"],
      "Resource": "*"
    },
    {
      "Sid": "HandTheSuppliedRoleToLambda",
      "Effect": "Allow",
      "Action": ["iam:PassRole", "iam:GetRole"],
      "Resource": "arn:aws:iam::*:role/REPLACE-WITH-YOUR-LAMBDA-ROLE-NAME"
    }
  ]
}
```

Replace the role name on the last statement with the one the workshop gave
you.

Two limits to be aware of. A user cannot be granted permissions its creator
does not hold, so this policy can only ever expose access you already have.
And a Service Control Policy or permission boundary sits above IAM entirely —
where one is blocking an action, attaching this changes nothing and the deploy
still fails. In that case CloudShell will not help either; the account simply
does not permit it.

### When access keys are blocked: CloudShell

A locked-down account will refuse to let you create an access key. That does
not block the deploy — it means the deploy happens somewhere else.

**AWS CloudShell** is a terminal in the browser, opened from the `>_` icon in
the console's top bar. It runs as your console identity with credentials
already in place, so there is no key to create and nothing to configure. It is
free, and it is in-region.

It also removes a problem rather than adding one. `psycopg2` ships compiled C
code that has to match Lambda's Linux runtime, which is why building on
Windows normally needs Docker. CloudShell already *is* Amazon Linux, so a
plain `sam build` produces the right binaries — which matters, because
CloudShell has no Docker.

The catch is that CloudShell starts empty, so the code has to arrive from
GitHub:

```bash
git clone https://github.com/khoi-a-ng/Banking-App-RESTAPI-nodb.git
cd Banking-App-RESTAPI-nodb
git checkout frontend_JWT
```

Anything uncommitted on your laptop will not be there. Push first.

Then check what the environment gives you, because the build needs a Python
that matches the template's `Runtime`:

```bash
aws sts get-caller-identity   # who am I, and does it work at all
python3 --version             # must satisfy Django 6.1 (3.12+)
sam --version                 # often absent; install below
```

SAM, if missing:

```bash
curl -L https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip -o sam.zip
unzip -q sam.zip -d sam-installation
sudo ./sam-installation/install
```

Only `$HOME` survives between CloudShell sessions (1 GB), so a long gap may
mean installing SAM again.

Build **without** `--use-container` here — there is no Docker, and none is
needed:

```bash
sam build
sam deploy --guided
```

**If SAM itself cannot be installed or run**, the same deploy is possible with
just the AWS CLI, which CloudShell always has: build a zip by hand
(`pip install -r requirements.txt -t package/`, copy `banking/` and `config/`
in, zip it), then `aws lambda update-function-code` and wire up API Gateway.
More steps, no extra permissions.

Docker must be running — SAM builds the dependencies inside a Lambda-like
Linux container, which is how `psycopg2` gets a binary that works on Lambda
rather than the Windows one in your `.venv`.

---

## Step 1 — Deploy the API

The connection string must use the **transaction pooler (port 6543)**, not the
session pooler you use locally. Each Lambda invocation opens its own
connection; a session pool would be exhausted. `select_for_update()` still
works correctly there — transaction-mode pooling pins a server connection for
the life of a transaction, which is exactly as long as the row lock needs.

Take your Supabase URL and change `:5432` to `:6543`.

```bash
sam build --use-container
sam deploy --guided
```

`--guided` asks a series of questions. The answers that matter:

| Prompt | Answer |
| --- | --- |
| Stack Name | `banking-api` |
| AWS Region | `us-east-1` (or wherever your account is) |
| Parameter DatabaseUrl | your Supabase URL **with port 6543** |
| Parameter DjangoSecretKey | the key you generated above |
| Parameter CorsOrigins | leave the default for now — Step 3 fixes it |
| Parameter LambdaRoleArn | the role ARN, in a workshop account; empty in your own |
| Confirm changes before deploy | `y` |
| Allow SAM CLI IAM role creation | `y` |
| Disable rollback | `N` |
| Save arguments to samconfig.toml | `y` |

If SAM cannot create its own artifact bucket (another thing shared accounts
often block), point it at one you are allowed to use:
`sam deploy --s3-bucket <existing-bucket>`.

Saying yes to the last one means future deploys are just `sam deploy`.

When it finishes it prints an **ApiUrl**. Check it:

```bash
curl https://YOUR-API-URL/api/
```

You should get the endpoint listing back. If not, read the logs:

```bash
sam logs -n BankingApi --stack-name banking-api --tail
```

> **`samconfig.toml` will contain your database URL and secret key.** Add it to
> `.gitignore` before committing anything.

---

## Step 2 — Deploy the frontend

Point the React build at the real API. In `frontend_React/.env.production`,
replace the placeholder with your ApiUrl — keeping the `/api` suffix:

```
VITE_API_URL=https://abc123.execute-api.us-east-2.amazonaws.com/api
```

Build and upload. Bucket names are globally unique, so pick your own:

```bash
cd frontend_React
npm run build

aws s3 mb s3://olivebank-frontend-<something-unique>
aws s3 sync dist/ s3://olivebank-frontend-<something-unique> --delete
```

Then put CloudFront in front of it. The console path is fine here:
**CloudFront → Create distribution → Origin = your S3 bucket → Origin access =
Origin access control**, and set the **Default root object** to `index.html`.
CloudFront will give you a policy to paste onto the bucket so it stays private
and is only readable through CloudFront.

This takes a few minutes to deploy. It hands you a domain like
`d111abcdef.cloudfront.net`.

---

## Step 3 — Let the two talk to each other

The API does not yet allow requests from CloudFront, so the site will load but
every call will fail CORS. Point the API at the real origin:

```bash
sam deploy --parameter-overrides CorsOrigins=https://d111abcdef.cloudfront.net
```

Then open the CloudFront URL and sign in. Watch the browser's Network tab —
`Authorization: Bearer ...` on requests, and a quiet `POST /auth/refresh/` once
an access token passes fifteen minutes.

---

## Running migrations

Migrations are **not** run by the deploy. Because Supabase is reachable from
anywhere, run them from your machine against the same database the Lambda
uses:

```bash
.venv/Scripts/python.exe manage.py migrate
```

---

## What this costs

Lambda's 1M requests/month and CloudFront's 1TB/month are permanent free
tiers, and API Gateway gives 1M requests/month for the first year. A project
at this traffic level rounds to zero. S3 storage for a ~250 KB bundle is
fractions of a cent.

To stop paying anything at all, delete the whole stack:

```bash
sam delete --stack-name banking-api
aws s3 rb s3://olivebank-frontend-<something-unique> --force
```

The CloudFront distribution has to be disabled first, then deleted, from the
console.

---

## Things worth knowing

**Cold starts.** The first request after an idle period spends a few seconds
importing Django. Subsequent requests are fast. This is inherent to running a
framework on Lambda, not something misconfigured.

**No static files.** This API returns only JSON — DRF's browsable API is
switched off and `django.contrib.admin` is not installed — so there is nothing
to run `collectstatic` for. That is why no S3 static bucket appears above.

**`conn_max_age=0`.** Set deliberately in `settings.py`. On a long-running
server you would want persistent connections; on Lambda they would accumulate
against the pooler until it refused new ones.
