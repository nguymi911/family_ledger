# Annie Budget - AWS Stack Technical Specification

## Overview

Rebuild Annie Budget as a serverless, AI-first application on AWS. The app provides household expense tracking with natural language input powered by Amazon Bedrock.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         CloudFront CDN                           │
└─────────────────────────────┬────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────┐
│              S3 Static Hosting (React/Next.js SPA)               │
└─────────────────────────────┬────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────┐
│                      Amazon API Gateway                          │
│   /auth/*    /transactions/*    /categories/*    /parse/*        │
└───────┬─────────────┬────────────────┬───────────────┬───────────┘
        │             │                │               │
        ▼             ▼                ▼               ▼
┌───────────┐  ┌─────────────┐  ┌───────────┐  ┌─────────────────┐
│  Cognito  │  │   Lambda    │  │  Lambda   │  │     Lambda      │
│   Auth    │  │transactions │  │categories │  │  parse_expense  │
└───────────┘  └──────┬──────┘  └─────┬─────┘  └────────┬────────┘
                      │               │                 │
                      ▼               ▼                 ▼
              ┌───────────────────────────┐    ┌───────────────┐
              │        DynamoDB           │    │    Bedrock    │
              │  - transactions           │    │    Claude     │
              │  - categories             │    └───────────────┘
              │  - user_profiles          │
              └───────────────────────────┘
```

## AWS Services

| Service | Purpose | Pricing Tier |
|---------|---------|--------------|
| **Cognito** | User authentication | Free < 50k MAU |
| **API Gateway** | REST API | $1/million requests |
| **Lambda** | Serverless compute | Free 1M requests/month |
| **DynamoDB** | NoSQL database | Free 25GB + 25 WCU/RCU |
| **Bedrock** | LLM (Claude Haiku) | $0.25/1M input tokens |
| **S3** | Static hosting | ~$0.023/GB |
| **CloudFront** | CDN | Free 1TB/month |
| **CloudWatch** | Logging & monitoring | Free tier available |

**Estimated Monthly Cost:** $2-10 for household usage

---

## Data Model (DynamoDB)

### Table: `annie-budget-users`

```
PK: USER#{user_id}
SK: PROFILE

Attributes:
- user_id: string (Cognito sub)
- email: string
- display_name: string
- created_at: string (ISO 8601)
- household_id: string (for shared access)
```

### Table: `annie-budget-data`

**Transactions:**
```
PK: HOUSEHOLD#{household_id}
SK: TX#{date}#{tx_id}

Attributes:
- tx_id: string (ULID)
- user_id: string
- amount: number
- description: string
- category_id: string
- is_annie_related: boolean
- date: string (YYYY-MM-DD)
- created_at: string (ISO 8601)

GSI1: user_id-date-index
- GSI1PK: USER#{user_id}
- GSI1SK: TX#{date}
```

**Categories:**
```
PK: HOUSEHOLD#{household_id}
SK: CAT#{category_id}

Attributes:
- category_id: string (ULID)
- name: string
- monthly_budget: number
- is_fixed: boolean
- created_at: string (ISO 8601)
```

### Access Patterns

| Pattern | Key Condition |
|---------|---------------|
| Get all household transactions for month | PK = HOUSEHOLD#{id}, SK begins_with TX#{YYYY-MM} |
| Get user's transactions | GSI1PK = USER#{id}, GSI1SK begins_with TX# |
| Get all categories | PK = HOUSEHOLD#{id}, SK begins_with CAT# |
| Get single transaction | PK = HOUSEHOLD#{id}, SK = TX#{date}#{tx_id} |

---

## API Design

### Authentication Endpoints (Cognito)

```
POST /auth/signup
POST /auth/signin
POST /auth/signout
POST /auth/refresh
GET  /auth/me
```

### Transaction Endpoints

```
GET    /transactions?year=2024&month=1
POST   /transactions
PUT    /transactions/{tx_id}
DELETE /transactions/{tx_id}
```

**Request/Response Examples:**

```json
// POST /transactions
Request:
{
  "amount": 50000,
  "description": "Coffee",
  "category_id": "cat_01HX...",
  "date": "2024-01-15",
  "is_annie_related": false
}

Response:
{
  "tx_id": "tx_01HX...",
  "amount": 50000,
  "description": "Coffee",
  "category_id": "cat_01HX...",
  "category_name": "Dining",
  "date": "2024-01-15",
  "is_annie_related": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Category Endpoints

```
GET    /categories
POST   /categories
PUT    /categories/{category_id}
DELETE /categories/{category_id}
```

### AI Parse Endpoint

```
POST /parse
```

**Request/Response:**

```json
// POST /parse
Request:
{
  "input": "coffee 50k, lunch with Annie 200k yesterday"
}

Response:
{
  "expenses": [
    {
      "amount": 50000,
      "description": "Coffee",
      "category": "Dining",
      "date": "2024-01-15",
      "is_annie_related": false
    },
    {
      "amount": 200000,
      "description": "Lunch with Annie",
      "category": "Dining",
      "date": "2024-01-14",
      "is_annie_related": true
    }
  ]
}
```

---

## Lambda Functions

### 1. parse_expense

```python
# functions/parse_expense/handler.py
import json
import boto3
from datetime import date, timedelta

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

SYSTEM_PROMPT = """You are an expense parser for a Vietnamese household budget app.
Parse the user's natural language input into structured expense data.

Rules:
- Currency: VND. "k" = thousand, "M" = million (e.g., 50k = 50000, 1.5M = 1500000)
- Detect if expense is related to "Annie" (child-related)
- Infer category from description
- Parse relative dates: "yesterday", "last week", etc.

Return JSON array:
[{"amount": number, "description": string, "category": string, "date": "YYYY-MM-DD", "is_annie_related": boolean}]
"""

def handler(event, context):
    body = json.loads(event.get('body', '{}'))
    user_input = body.get('input', '')
    categories = body.get('categories', [])

    today = date.today().isoformat()

    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-haiku-20240307-v1:0',
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "system": SYSTEM_PROMPT,
            "messages": [{
                "role": "user",
                "content": f"Today is {today}. Categories: {categories}. Parse: {user_input}"
            }],
            "max_tokens": 1024
        })
    )

    result = json.loads(response['body'].read())
    content = result['content'][0]['text']

    # Extract JSON from response
    expenses = json.loads(content)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'expenses': expenses})
    }
```

### 2. transactions

```python
# functions/transactions/handler.py
import json
import boto3
from decimal import Decimal
from datetime import datetime
import ulid

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('annie-budget-data')

def handler(event, context):
    method = event['httpMethod']
    user_id = event['requestContext']['authorizer']['claims']['sub']
    household_id = get_household_id(user_id)

    if method == 'GET':
        return get_transactions(event, household_id)
    elif method == 'POST':
        return create_transaction(event, household_id, user_id)
    elif method == 'PUT':
        return update_transaction(event, household_id)
    elif method == 'DELETE':
        return delete_transaction(event, household_id)

def get_transactions(event, household_id):
    params = event.get('queryStringParameters', {}) or {}
    year = params.get('year', datetime.now().year)
    month = params.get('month', datetime.now().month)

    prefix = f"TX#{year}-{int(month):02d}"

    response = table.query(
        KeyConditionExpression='PK = :pk AND begins_with(SK, :prefix)',
        ExpressionAttributeValues={
            ':pk': f'HOUSEHOLD#{household_id}',
            ':prefix': prefix
        },
        ScanIndexForward=False
    )

    return {
        'statusCode': 200,
        'body': json.dumps(response['Items'], default=str)
    }

def create_transaction(event, household_id, user_id):
    body = json.loads(event['body'])
    tx_id = str(ulid.new())
    tx_date = body['date']

    item = {
        'PK': f'HOUSEHOLD#{household_id}',
        'SK': f'TX#{tx_date}#{tx_id}',
        'tx_id': tx_id,
        'user_id': user_id,
        'amount': Decimal(str(body['amount'])),
        'description': body['description'],
        'category_id': body.get('category_id'),
        'is_annie_related': body.get('is_annie_related', False),
        'date': tx_date,
        'created_at': datetime.utcnow().isoformat(),
        'GSI1PK': f'USER#{user_id}',
        'GSI1SK': f'TX#{tx_date}'
    }

    table.put_item(Item=item)

    return {
        'statusCode': 201,
        'body': json.dumps({'tx_id': tx_id})
    }
```

### 3. categories

```python
# functions/categories/handler.py
import json
import boto3
from decimal import Decimal
from datetime import datetime
import ulid

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('annie-budget-data')

def handler(event, context):
    method = event['httpMethod']
    user_id = event['requestContext']['authorizer']['claims']['sub']
    household_id = get_household_id(user_id)

    if method == 'GET':
        return get_categories(household_id)
    elif method == 'POST':
        return create_category(event, household_id)
    elif method == 'PUT':
        return update_category(event, household_id)
    elif method == 'DELETE':
        return delete_category(event, household_id)

def get_categories(household_id):
    response = table.query(
        KeyConditionExpression='PK = :pk AND begins_with(SK, :prefix)',
        ExpressionAttributeValues={
            ':pk': f'HOUSEHOLD#{household_id}',
            ':prefix': 'CAT#'
        }
    )

    return {
        'statusCode': 200,
        'body': json.dumps(response['Items'], default=str)
    }

def create_category(event, household_id):
    body = json.loads(event['body'])
    cat_id = str(ulid.new())

    item = {
        'PK': f'HOUSEHOLD#{household_id}',
        'SK': f'CAT#{cat_id}',
        'category_id': cat_id,
        'name': body['name'],
        'monthly_budget': Decimal(str(body.get('monthly_budget', 0))),
        'is_fixed': body.get('is_fixed', False),
        'created_at': datetime.utcnow().isoformat()
    }

    table.put_item(Item=item)

    return {
        'statusCode': 201,
        'body': json.dumps({'category_id': cat_id})
    }
```

---

## Frontend (React + Vite)

### Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── SmartInput.tsx
│   │   ├── TransactionList.tsx
│   │   ├── BudgetOverview.tsx
│   │   └── CategoryManager.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useTransactions.ts
│   │   └── useCategories.ts
│   ├── lib/
│   │   ├── api.ts
│   │   └── auth.ts (Amplify/Cognito)
│   ├── pages/
│   │   ├── Home.tsx
│   │   ├── Transactions.tsx
│   │   └── Categories.tsx
│   └── App.tsx
├── package.json
└── vite.config.ts
```

### Key Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-router-dom": "^6.0.0",
    "@aws-amplify/ui-react": "^6.0.0",
    "aws-amplify": "^6.0.0",
    "@tanstack/react-query": "^5.0.0",
    "tailwindcss": "^3.4.0"
  }
}
```

### Auth Hook Example

```typescript
// src/hooks/useAuth.ts
import { useAuthenticator } from '@aws-amplify/ui-react';

export function useAuth() {
  const { user, signOut } = useAuthenticator();

  return {
    user,
    isAuthenticated: !!user,
    signOut,
    userId: user?.userId,
  };
}
```

### API Client

```typescript
// src/lib/api.ts
import { fetchAuthSession } from 'aws-amplify/auth';

const API_BASE = import.meta.env.VITE_API_URL;

async function authFetch(path: string, options: RequestInit = {}) {
  const session = await fetchAuthSession();
  const token = session.tokens?.idToken?.toString();

  return fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
  });
}

export const api = {
  getTransactions: (year: number, month: number) =>
    authFetch(`/transactions?year=${year}&month=${month}`).then(r => r.json()),

  createTransaction: (data: CreateTransactionInput) =>
    authFetch('/transactions', { method: 'POST', body: JSON.stringify(data) }),

  parseExpense: (input: string, categories: string[]) =>
    authFetch('/parse', { method: 'POST', body: JSON.stringify({ input, categories }) })
      .then(r => r.json()),

  getCategories: () =>
    authFetch('/categories').then(r => r.json()),
};
```

---

## Infrastructure as Code (AWS SAM)

### template.yaml

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Annie Budget API

Globals:
  Function:
    Timeout: 30
    Runtime: python3.11
    MemorySize: 256
    Environment:
      Variables:
        TABLE_NAME: !Ref DataTable

Resources:
  # Cognito User Pool
  UserPool:
    Type: AWS::Cognito::UserPool
    Properties:
      UserPoolName: annie-budget-users
      AutoVerifiedAttributes:
        - email
      UsernameAttributes:
        - email
      Schema:
        - Name: email
          Required: true
          Mutable: true

  UserPoolClient:
    Type: AWS::Cognito::UserPoolClient
    Properties:
      UserPoolId: !Ref UserPool
      GenerateSecret: false
      ExplicitAuthFlows:
        - ALLOW_USER_PASSWORD_AUTH
        - ALLOW_REFRESH_TOKEN_AUTH

  # DynamoDB Table
  DataTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: annie-budget-data
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: PK
          AttributeType: S
        - AttributeName: SK
          AttributeType: S
        - AttributeName: GSI1PK
          AttributeType: S
        - AttributeName: GSI1SK
          AttributeType: S
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: GSI1
          KeySchema:
            - AttributeName: GSI1PK
              KeyType: HASH
            - AttributeName: GSI1SK
              KeyType: RANGE
          Projection:
            ProjectionType: ALL

  # API Gateway
  Api:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      Auth:
        DefaultAuthorizer: CognitoAuthorizer
        Authorizers:
          CognitoAuthorizer:
            UserPoolArn: !GetAtt UserPool.Arn
      Cors:
        AllowOrigin: "'*'"
        AllowHeaders: "'Content-Type,Authorization'"
        AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"

  # Lambda Functions
  ParseExpenseFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: handler.handler
      CodeUri: functions/parse_expense/
      Policies:
        - Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action:
                - bedrock:InvokeModel
              Resource: '*'
      Events:
        Api:
          Type: Api
          Properties:
            RestApiId: !Ref Api
            Path: /parse
            Method: POST

  TransactionsFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: handler.handler
      CodeUri: functions/transactions/
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref DataTable
      Events:
        GetTransactions:
          Type: Api
          Properties:
            RestApiId: !Ref Api
            Path: /transactions
            Method: GET
        CreateTransaction:
          Type: Api
          Properties:
            RestApiId: !Ref Api
            Path: /transactions
            Method: POST
        UpdateTransaction:
          Type: Api
          Properties:
            RestApiId: !Ref Api
            Path: /transactions/{tx_id}
            Method: PUT
        DeleteTransaction:
          Type: Api
          Properties:
            RestApiId: !Ref Api
            Path: /transactions/{tx_id}
            Method: DELETE

  CategoriesFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: handler.handler
      CodeUri: functions/categories/
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref DataTable
      Events:
        GetCategories:
          Type: Api
          Properties:
            RestApiId: !Ref Api
            Path: /categories
            Method: GET
        CreateCategory:
          Type: Api
          Properties:
            RestApiId: !Ref Api
            Path: /categories
            Method: POST

Outputs:
  ApiUrl:
    Value: !Sub 'https://${Api}.execute-api.${AWS::Region}.amazonaws.com/prod'
  UserPoolId:
    Value: !Ref UserPool
  UserPoolClientId:
    Value: !Ref UserPoolClient
```

---

## Deployment Steps

### Prerequisites

```bash
# Install AWS CLI and SAM CLI
brew install awscli aws-sam-cli

# Configure AWS credentials
aws configure
```

### Deploy Backend

```bash
# Build and deploy
cd backend
sam build
sam deploy --guided

# Note the outputs: ApiUrl, UserPoolId, UserPoolClientId
```

### Deploy Frontend

```bash
# Build React app
cd frontend
npm run build

# Create S3 bucket and sync
aws s3 mb s3://annie-budget-frontend
aws s3 sync dist/ s3://annie-budget-frontend --delete

# Create CloudFront distribution (or use Amplify Hosting)
```

---

## Migration Plan

| Phase | Tasks | Duration |
|-------|-------|----------|
| 1 | Set up AWS account, IAM, Cognito | 1 day |
| 2 | Deploy DynamoDB, create tables | 1 day |
| 3 | Build & deploy Lambda functions | 2-3 days |
| 4 | Build React frontend | 3-4 days |
| 5 | Migrate data from Supabase | 1 day |
| 6 | Testing & go-live | 1-2 days |

**Total: ~2 weeks part-time**

---

## Future AI Enhancements

Once on AWS with Bedrock, you can easily add:

1. **Spending Insights** - Weekly AI summaries of spending patterns
2. **Anomaly Detection** - Alert on unusual transactions
3. **Budget Recommendations** - AI-suggested budget adjustments
4. **Receipt Scanning** - Textract + Bedrock for receipt parsing
5. **Voice Input** - Transcribe + Bedrock for voice expense entry
