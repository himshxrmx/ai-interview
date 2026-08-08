$ErrorActionPreference = "Stop"

$RoleName = "abtalks-lambda-role"
$LambdaName = "abtalks-api"
$Region = "us-east-1"
$ApiName = "abtalks-api-gateway"

Write-Host "1. Setting up IAM Role..."
$ErrorActionPreference = "Continue"
$RoleExists = aws iam get-role --role-name $RoleName 2>$null
$ErrorActionPreference = "Stop"
if (-not $RoleExists) {
    Write-Host "Creating new IAM Role: $RoleName"
    $PolicyDoc = '{"Version": "2012-10-17","Statement": [{"Action": "sts:AssumeRole","Principal": {"Service": "lambda.amazonaws.com"},"Effect": "Allow","Sid": ""}]}'
    [IO.File]::WriteAllText("$PWD\trust-policy.json", $PolicyDoc)
    aws iam create-role --role-name $RoleName --assume-role-policy-document file://trust-policy.json | Out-Null
    aws iam attach-role-policy --role-name $RoleName --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    aws iam attach-role-policy --role-name $RoleName --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
    
    Write-Host "Waiting 10 seconds for IAM Role to propagate..."
    Start-Sleep -Seconds 10
} else {
    Write-Host "IAM Role $RoleName already exists."
}

$RoleArn = aws iam get-role --role-name $RoleName --query "Role.Arn" --output text

Write-Host "2. Packaging application..."
if (Test-Path package) { Remove-Item -Recurse -Force package }
if (Test-Path deployment.zip) { Remove-Item -Force deployment.zip }
New-Item -ItemType Directory -Path package | Out-Null

pip install -r requirements.txt -t package/ | Out-Null
Copy-Item main.py, models.py, database.py, llm_service.py, .env package/

Write-Host "Zipping deployment package..."
Compress-Archive -Path package\* -DestinationPath deployment.zip

Write-Host "3. Deploying Lambda function..."
$ErrorActionPreference = "Continue"
$FunctionExists = aws lambda get-function --function-name $LambdaName 2>$null
$ErrorActionPreference = "Stop"
if ($FunctionExists) {
    Write-Host "Updating existing Lambda function code..."
    aws lambda update-function-code --function-name $LambdaName --zip-file fileb://deployment.zip | Out-Null
} else {
    Write-Host "Creating new Lambda function..."
    aws lambda create-function `
        --function-name $LambdaName `
        --runtime python3.11 `
        --role $RoleArn `
        --handler main.handler `
        --zip-file fileb://deployment.zip `
        --timeout 60 `
        --memory-size 256 | Out-Null
}

Write-Host "Waiting for Lambda function to become active..."
aws lambda wait function-active-v2 --function-name $LambdaName

Write-Host "4. Setting up API Gateway..."
$ErrorActionPreference = "Continue"
$ApiId = aws apigatewayv2 get-apis --query "Items[?Name=='$ApiName'].ApiId | [0]" --output text
$ErrorActionPreference = "Stop"

if ($ApiId -eq "None" -or -not $ApiId) {
    Write-Host "Creating new HTTP API Gateway..."
    $AccountId = aws sts get-caller-identity --query Account --output text
    $LambdaArn = "arn:aws:lambda:${Region}:${AccountId}:function:${LambdaName}"
    
    $ApiId = aws apigatewayv2 create-api --name $ApiName --protocol-type HTTP --target $LambdaArn --query "ApiId" --output text
    
    Write-Host "Granting API Gateway permission to invoke Lambda..."
    aws lambda add-permission `
        --function-name $LambdaName `
        --statement-id apigateway-invoke `
        --action lambda:InvokeFunction `
        --principal apigateway.amazonaws.com `
        --source-arn "arn:aws:execute-api:${Region}:${AccountId}:${ApiId}/*/*" | Out-Null
} else {
    Write-Host "API Gateway $ApiName already exists (ID: $ApiId)."
}

$ApiUrl = aws apigatewayv2 get-api --api-id $ApiId --query "ApiEndpoint" --output text

Write-Host "========================================="
Write-Host "Deployment Complete!"
Write-Host "API Gateway URL: $ApiUrl"
Write-Host "========================================="
