# 🚀 Deploy Tender Engine API to AWS ECS Fargate (Cape Town)

**Difficulty:** Beginner Friendly 🎒
**Time needed:** About 1 hour (mostly waiting for AWS)
**Cost:** ~$0.19/hour for 2 vCPU + 4GB RAM (~$140/month)

---

## 📖 What Are We Doing?

Imagine you have a **robot chef** (your API) that cooks meals in your kitchen (your laptop).
Right now, you can only use it when your laptop is on and you're home.

**AWS ECS Fargate** is like renting a cloud kitchen — your robot chef works there 24/7,
and Amazon takes care of the electricity, water, and cleaning. Anyone on the internet can
order meals (call your API) any time.

**Cape Town (af-south-1)** = The AWS data centre in Cape Town, South Africa. Good for
South African users because they connect faster (lower latency).

---

## ✅ What You Need Before Starting

Check each box before you begin:

- [ ] **An AWS account** — sign up free at https://aws.amazon.com
- [ ] **AWS CLI installed** — open Command Prompt (search for "cmd") and type: `aws --version`
      If you see `'aws' is not recognized`, download from: https://aws.amazon.com/cli/
- [ ] **Docker Desktop installed** — open Command Prompt and type: `docker --version`
      If you see `'docker' is not recognized`, download from: https://www.docker.com/products/docker-desktop/
- [ ] **Your AWS Account ID** — we'll get this in the first step below
- [ ] **About 1 hour** of free time

---

## 🔑 A Note on AWS Regions

Every AWS command in this guide includes `--region af-south-1` (Cape Town).
This is IMPORTANT because:
1. Some AWS services are NOT available in every region — but ECS Fargate works in af-south-1 ✅
2. You want your app to run in South Africa for fast speeds for SA users
3. Prices vary by region — af-south-1 is slightly more expensive than US/EU regions

If you ever get an error like `Resource is not supported in this region`, it means
you forgot to add `--region af-south-1` to your command.

---

## 🏁 STEP 1: Find Your AWS Account ID

This is a 12-digit number that identifies your AWS account.

```cmd
aws sts get-caller-identity --region af-south-1
```

Look for the `Account` field in the output. Something like: `"Account": "123456789012"`
**Write this number down — you'll need it in the next steps.**

---

## 🏁 STEP 2: Configure AWS CLI

Open Command Prompt and run:

```cmd
aws configure
```

It will ask you for 4 things. Type them in (one at a time, pressing Enter after each):

```
AWS Access Key ID [None]: AKIAXXXXXXXXXXXXXXXX
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: af-south-1
Default output format [None]: json
```

**How to get your Access Key (if you don't have one):**
1. Go to https://console.aws.amazon.com
2. Click your name in the top-right corner → **Security credentials**
3. Scroll down to **Access keys** → **Create access key**
4. Choose **Command Line Interface (CLI)** → check the box → **Next**
5. Copy the **Access Key ID** and **Secret Access Key**
6. Paste them into the `aws configure` command above

> ⚠️ **CRITICAL:** Never share these keys! Never commit them to GitHub!
> If someone gets these, they can use your AWS account and you'll get a huge bill.

---

## 🏁 STEP 3: Create an ECR Repository (Docker Image Storage)

ECR = Elastic Container Registry. Think of it as a **private folder on AWS** where you'll
store your Docker image. ECS will pull the image from here to run it.

Open Command Prompt and run these commands ONE AT A TIME (copy-paste each, press Enter):

### 3A: Create the repository

```cmd
aws ecr create-repository --repository-name tender-engine-api --region af-south-1
```

**Expected output:** You'll see a JSON response with repository details (look for `repositoryUri`).

### 3B: Log in to ECR so you can push images

Replace `YOUR_ACCOUNT_ID` with the 12-digit number from Step 1:

```cmd
aws ecr get-login-password --region af-south-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.af-south-1.amazonaws.com
```

**Expected output:** `Login Succeeded`

---

## 🏁 STEP 4: Build and Push Your Docker Image

Now we'll create the Docker image and upload it to AWS.

### 4A: Build the Docker image

```cmd
docker build -t tender-engine-api .
```

This reads your `Dockerfile` and creates a ready-to-run image.
**This will take 5-15 minutes the first time** (downloads packages).
Later builds will be faster because of caching.

### 4B: Tag the image for AWS

Replace `YOUR_ACCOUNT_ID`:

```cmd
docker tag tender-engine-api:latest YOUR_ACCOUNT_ID.dkr.ecr.af-south-1.amazonaws.com/tender-engine-api:latest
```

### 4C: Push the image to AWS

Replace `YOUR_ACCOUNT_ID`:

```cmd
docker push YOUR_ACCOUNT_ID.dkr.ecr.af-south-1.amazonaws.com/tender-engine-api:latest
```

**This will take 3-10 minutes** depending on your internet speed.

**If you get "Access Denied":** You forgot to run `aws ecr get-login-password...` in step 3B. Run it again, then retry.

---

## 🏁 STEP 5: Store Your Secrets in AWS SSM Parameter Store

Your app needs secret values like `SECRET_KEY` and `PAYFAST_MERCHANT_ID`.
We store these in AWS SSM (a secure locker) instead of putting them in code.

Run these commands ONE AT A TIME, replacing `YOUR_ACCOUNT_ID`:

```cmd
aws ssm put-parameter --name "/tender-engine/SECRET_KEY" --value "8d3e3bdc52a2bde66df0830996b0c384d4501291733dacddb170145b9171bed5" --type SecureString --region af-south-1

aws ssm put-parameter --name "/tender-engine/PAYFAST_MERCHANT_ID" --value "10000100" --type SecureString --region af-south-1

aws ssm put-parameter --name "/tender-engine/PAYFAST_MERCHANT_KEY" --value "46f0cd694581a" --type SecureString --region af-south-1

aws ssm put-parameter --name "/tender-engine/TENDER_API_KEY" --value "test_key_123" --type SecureString --region af-south-1
```

**Expected output for each:** Look for `"Version": 1` in the JSON response.

> 🔒 `SecureString` means AWS encrypts these values. Only your ECS task can read them.
> If you change a secret later, re-run the command — it will create "Version": 2, etc.

---

## 🏁 STEP 6: Create IAM Roles (Permissions)

IAM Roles are like **identity cards** that give AWS services permission to do things.
ECS needs two identity cards:

1. **Execution Role** — lets ECS pull your Docker image and write logs
2. **Task Role** — lets your app read secrets from SSM

### 6A: Create the trust policy file

Copy this EXACTLY and save it as `ecs-trust-policy.json` in your project folder:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### 6B: Create the Execution Role

```cmd
aws iam create-role --role-name ecsTaskExecutionRole --assume-role-policy-document file://ecs-trust-policy.json
```

```cmd
aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

### 6C: Create the Task Role policy file

Copy this EXACTLY and save it as `task-role-policy.json` in your project folder:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameters",
                "ssm:GetParameter"
            ],
            "Resource": "arn:aws:ssm:af-south-1:YOUR_ACCOUNT_ID:parameter/tender-engine/*"
        }
    ]
}
```

**IMPORTANT:** Replace `YOUR_ACCOUNT_ID` with your real 12-digit account ID in the JSON file above.

### 6D: Create the Task Role

```cmd
aws iam create-role --role-name ecsTaskRole --assume-role-policy-document file://ecs-trust-policy.json
```

```cmd
aws iam put-role-policy --role-name ecsTaskRole --policy-name SSMParameterAccess --policy-document file://task-role-policy.json
```

---

## 🏁 STEP 7: Edit the Task Definition File

Open `ecs-task-definition.json` in your editor (VS Code).
You need to find and replace **3 things**:

1. **`YOUR_ACCOUNT_ID`** — replace ALL 4 instances with your 12-digit account number
2. **`fs-YOUR_EFS_FILESYSTEM_ID`** — we'll create this in the next step, leave it for now
3. **`fsap-YOUR_EFS_ACCESS_POINT_ID`** — same, we'll update this later

For now, just replace `YOUR_ACCOUNT_ID` everywhere (there are 4 places).
Save the file after editing.

---

## 🏁 STEP 8: Create an EFS File System (Persistent Storage)

EFS is like a **network hard drive** that persists even when your container restarts.
Without this, your SQLite database would be erased every time you update your app.

### 8A: Create the EFS filesystem

```cmd
aws efs create-file-system --performance-mode generalPurpose --throughput-mode bursting --region af-south-1
```

**Note the `FileSystemId`** in the output (looks like `fs-12345678`). Save it!

### 8B: Find your default VPC and subnets

```cmd
aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --region af-south-1 --query "Vpcs[0].VpcId" --output text
```

**Save that VPC ID** (looks like `vpc-xxxxxxxx`). You'll need it for the next command:

```cmd
aws ec2 describe-subnets --filters "Name=vpc-id,Values=YOUR_VPC_ID" --region af-south-1 --query "Subnets[*].{ID:SubnetId,AZ:AvailabilityZone}" --output table
```

**Save at least 2 subnet IDs** (looks like `subnet-xxxxxxxx`). Pick ones in different
availability zones (e.g., `af-south-1a` and `af-south-1b`).

### 8C: Create mount targets (connects EFS to your VPC)

Run this for EACH subnet you want to use. Replace `fs-xxxxxxxx` with your EFS file system ID
and `subnet-xxxxxxxx` with each subnet ID:

```cmd
aws efs create-mount-target --file-system-id fs-xxxxxxxx --subnet-id subnet-xxxxxxxx --security-groups sg-xxxxxxxx --region af-south-1
```

Wait 2-3 minutes for the mount targets to become available.

### 8D: Create an EFS Access Point

This gives your ECS task a "doorway" into the EFS filesystem. It also sets
permissions so the `appuser` inside the container can read/write.

```cmd
aws efs create-access-point --file-system-id fs-xxxxxxxx --root-directory Path=/tender-engine-data,CreationInfo='{OwnerUid=1001,OwnerGid=1001,Permissions=0775}' --posix-user Uid=1001,Gid=1001 --region af-south-1
```

**Save the `AccessPointId`** (looks like `fsap-xxxxxxxx`).

### 8E: Update ecs-task-definition.json with EFS IDs

Open `ecs-task-definition.json` again and replace:
- `fs-YOUR_EFS_FILESYSTEM_ID` → your actual EFS file system ID (e.g., `fs-12345678`)
- `fsap-YOUR_EFS_ACCESS_POINT_ID` → your actual access point ID (e.g., `fsap-12345678`)

---

## 🏁 STEP 9: Register the ECS Task Definition

Now we tell ECS exactly how to run your container.

```cmd
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json --region af-south-1
```

**Expected output:** You'll see the task definition JSON with `"revision": 1` at the bottom.

**If you get a JSON error:** Double-check your `ecs-task-definition.json` file for
missing commas or quotes. Use a JSON validator like https://jsonlint.com.

---

## 🏁 STEP 10: Create a Security Group (Firewall)

This is like a **bouncer** at a club. It lets people in on port 8000 but blocks
everything else.

### 10A: Create the security group

```cmd
aws ec2 create-security-group --group-name tender-engine-sg --description "Allow HTTP access to Tender Engine API on port 8000" --region af-south-1
```

**Save the GroupId** (looks like `sg-xxxxxxxx`).

### 10B: Allow incoming traffic on port 8000

```cmd
aws ec2 authorize-security-group-ingress --group-id sg-xxxxxxxx --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region af-south-1
```

> ⚠️ `0.0.0.0/0` means "anyone on the internet." In a production app, you'd restrict
> this to only your users' IPs. For now, it's fine.

---

## 🏁 STEP 11: Create an ECS Cluster

A cluster is just a **group** where your containers run. Think of it as a "neighbourhood"
for your services.

```cmd
aws ecs create-cluster --cluster-name tender-engine-cluster --region af-south-1
```

**Expected output:** You'll see the cluster details with `"status": "ACTIVE"`.

---

## 🏁 STEP 12: Create a CloudWatch Log Group

This is where your app's **console output and error messages** will be stored.
When something breaks, you'll look here to find out why.

```cmd
aws logs create-log-group --log-group-name /ecs/tender-engine-api --region af-south-1
```

**No output** means it worked.

---

## 🏁 STEP 13: Create an ECS Service (Run Your App!)

This is the exciting part — you **start your app** on AWS!

Replace the placeholders in the command below:
- `sg-xxxxxxxx` → your security group ID from Step 10
- `subnet-xxxxxxxx` and `subnet-yyyyyyyy` → your subnet IDs from Step 8B

```cmd
aws ecs create-service \
    --cluster tender-engine-cluster \
    --service-name tender-engine-api-service \
    --task-definition tender-engine-api \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxxxxx,subnet-yyyyyyyy],securityGroups=[sg-xxxxxxxx],assignPublicIp=ENABLED}" \
    --region af-south-1
```

**Expected output:** You'll see the service details with `"status": "ACTIVE"`.

---

## 🏁 STEP 14: Find Your App's Public IP

Give it about 1-2 minutes for the task to start.

### Method A: AWS Console (Easiest — Use this!)

1. Go to https://console.aws.amazon.com/ecs/v2/clusters/tender-engine-cluster/services
2. Click on `tender-engine-api-service`
3. Click the **Tasks** tab
4. Click the running task (it should say `Status: RUNNING` and `Health: HEALTHY`)
5. Look for **Public IP** near the bottom

### Method B: Command Line (If you're a CLI person)

```cmd
aws ecs list-tasks --cluster tender-engine-cluster --region af-south-1
```

This gives you a task ARN. Copy it, then:

```cmd
aws ecs describe-tasks --cluster tender-engine-cluster --tasks arn:aws:ecs:af-south-1:YOUR_ACCOUNT_ID:task/tender-engine-cluster/YOUR_TASK_ID --region af-south-1 --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" --output text
```

This gives you an ENI ID. Then:

```cmd
aws ec2 describe-network-interfaces --network-interface-ids eni-xxxxxxxx --region af-south-1 --query "NetworkInterfaces[0].Association.PublicIp" --output text
```

### Test Your API

Open your browser and go to:
```
http://YOUR_PUBLIC_IP:8000/api/health
```

You should see:
```json
{"status":"ok","services":["extract","validate","price","doc"]}
```

Also try the API docs:
```
http://YOUR_PUBLIC_IP:8000/docs
```

---

## 🏁 STEP 15: (Optional) Set Up a Domain with an Application Load Balancer

Using a raw IP address works, but if the container restarts, your IP changes!
An **Application Load Balancer (ALB)** gives you a **fixed address** that forwards
traffic to your container, no matter what its IP is.

This is optional and more advanced. If you're just testing, skip this and use the
IP directly.

---

## 🔄 How to Update Your App (After Making Code Changes)

Every time you change your code and want to deploy the new version:

```cmd
:: Step 1: Rebuild the Docker image
docker build -t tender-engine-api .

:: Step 2: Tag it for AWS (replace YOUR_ACCOUNT_ID)
docker tag tender-engine-api:latest YOUR_ACCOUNT_ID.dkr.ecr.af-south-1.amazonaws.com/tender-engine-api:latest

:: Step 3: Push to AWS
docker push YOUR_ACCOUNT_ID.dkr.ecr.af-south-1.amazonaws.com/tender-engine-api:latest

:: Step 4: Tell ECS to restart with the new image
aws ecs update-service --cluster tender-engine-cluster --service tender-engine-api-service --force-new-deployment --region af-south-1
```

The **update** takes about 2-3 minutes. The old container runs until the new one
is healthy, so there's **no downtime**.

---

## 🛑 How to Stop the App (To Save Money)

When you're not using it, stop it so you don't get charged:

```cmd
aws ecs update-service --cluster tender-engine-cluster --service tender-engine-api-service --desired-count 0 --region af-south-1
```

To **start it again:**

```cmd
aws ecs update-service --cluster tender-engine-cluster --service tender-engine-api-service --desired-count 1 --region af-south-1
```

---

## 🧹 How to Clean Everything Up (Uninstall)

If you want to delete everything to avoid future costs:

```cmd
:: 1. Delete the ECS service (stop the app)
aws ecs delete-service --cluster tender-engine-cluster --service tender-engine-api-service --force --region af-south-1

:: 2. Delete the ECS cluster
aws ecs delete-cluster --cluster tender-engine-cluster --region af-south-1

:: 3. Delete the log group (saves ~$0.50/month)
aws logs delete-log-group --log-group-name /ecs/tender-engine-api --region af-south-1

:: 4. Delete the ECR repository and its images
aws ecr delete-repository --repository-name tender-engine-api --force --region af-south-1

:: 5. Delete the EFS filesystem (replace fs-xxxxxxxx)
aws efs delete-file-system --file-system-id fs-xxxxxxxx --region af-south-1

:: 6. Delete the security group (replace sg-xxxxxxxx)
aws ec2 delete-security-group --group-id sg-xxxxxxxx --region af-south-1

:: 7. Delete IAM roles
aws iam detach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
aws iam delete-role --role-name ecsTaskExecutionRole
aws iam delete-role-policy --role-name ecsTaskRole --policy-name SSMParameterAccess
aws iam delete-role --role-name ecsTaskRole

:: 8. Delete SSM parameters
aws ssm delete-parameter --name /tender-engine/SECRET_KEY --region af-south-1
aws ssm delete-parameter --name /tender-engine/PAYFAST_MERCHANT_ID --region af-south-1
aws ssm delete-parameter --name /tender-engine/PAYFAST_MERCHANT_KEY --region af-south-1
aws ssm delete-parameter --name /tender-engine/TENDER_API_KEY --region af-south-1
```

---

## 💰 Cost Breakdown (How Much Will This Cost?)

AWS Fargate pricing in **af-south-1** (Cape Town — more expensive than US):

| Item | Cost per month |
|------|---------------|
| 2 vCPU + 4 GB RAM (running 24/7) | ~$140 |
| ECR storage (your Docker image) | ~$0.10 |
| CloudWatch logs (storing log messages) | ~$3 |
| EFS storage (your database) | ~$5 |
| **Total** | **~$148/month** |

### How to save money:

| Method | Savings |
|--------|---------|
| **Stop the app when not using it** | ~$140/month if you only use it during work hours |
| **Use smaller CPU/RAM** (edit ecs-task-definition.json: `"cpu": "1024"`, `"memory": "2048"`) | ~$70/month |
| **AWS Free Tier** (first 12 months) | Free for limited hours (750 hours/month of Fargate) |

---

## ❓ Troubleshooting (When Things Go Wrong)

### "Service did not stabilize" error
The container keeps crashing.
1. Open AWS Console → ECS → Clusters → `tender-engine-cluster` → Tasks
2. Click the **stopped** task
3. Look at **Stopped reason** (e.g., "CannotPullContainerError", "OutOfMemoryError")
4. Click the **Logs** tab to see your app's error messages

### "CannotPullContainerError"
ECS can't pull your Docker image from ECR.
- Did you push the image? Run step 4C again
- Did you log in to ECR with `aws ecr get-login-password`? Run step 3B again
- Is `YOUR_ACCOUNT_ID` correct in `ecs-task-definition.json`?

### "ResourceInitializationError: unable to pull secrets"
ECS can't read your secrets from SSM.
- Make sure you created the parameters in Step 5
- Make sure your account ID in the `secrets` section of `ecs-task-definition.json` is correct
- Make sure you created the Task Role in Step 6D

### "Port 8000 connection refused" / Can't connect
The container is running but no app is listening on port 8000.
1. Check the **Logs** tab for Python errors (missing imports, database errors, etc.)
2. Try the health check URL: `http://YOUR_IP:8000/api/health`
3. Make sure the security group allows port 8000 (Step 10)

### "Access Denied" when pushing Docker
You didn't log in to ECR properly. Run step 3B again:
```cmd
aws ecr get-login-password --region af-south-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.af-south-1.amazonaws.com
docker push YOUR_ACCOUNT_ID.dkr.ecr.af-south-1.amazonaws.com/tender-engine-api:latest
```

### "The service is having trouble starting" or "Health check keeps failing"
Your app might be taking too long to start.
- Check the start period in the health check (currently 15s)
- You may need to increase it if your app loads ML models on startup
- Edit `ecs-task-definition.json` → `healthCheck.startPeriod` → increase to 60 or 120

---

## 📂 Files We Use

| File | What It Does |
|------|-------------|
| `Dockerfile` | Instructions to build your app into a container image |
| `.dockerignore` | Tells Docker what to EXCLUDE (keeps the image small) |
| `docker-compose.yml` | Run locally with `docker compose up` (for development) |
| `ecs-task-definition.json` | Tells AWS ECS how to run your container (for production) |
| `DEPLOY_TO_ECS.md` | This guide |

---

## ✅ Deployment Checklist

Before you try to deploy, make sure you've completed these steps:

- [ ] Docker is installed and working (`docker --version`)
- [ ] AWS CLI is installed and configured (`aws configure`)
- [ ] You have your AWS Account ID (12-digit number)
- [ ] ECR repository is created (Step 3A)
- [ ] Docker image is built and pushed to ECR (Step 4)
- [ ] SSM parameters are created with your secrets (Step 5)
- [ ] IAM roles are created (Step 6)
- [ ] `ecs-task-definition.json` has YOUR_ACCOUNT_ID replaced
- [ ] EFS filesystem and access point are created (Step 8)
- [ ] Task definition is registered (Step 9)
- [ ] Security group is created (Step 10)
- [ ] ECS cluster is created (Step 11)
- [ ] Log group is created (Step 12)
- [ ] ECS service is created and task is RUNNING (Step 13)
- [ ] API responds at `http://YOUR_PUBLIC_IP:8000/api/health` (Step 14)

---

**Congratulations!** 🎉 You've deployed your Tender Engine API to AWS ECS Fargate in Cape Town!