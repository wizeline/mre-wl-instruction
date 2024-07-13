## DetectSceneLabels

- Attach policy: `AmazonBedrockFullAccess`
- Add the following policy in `DetectSceneLabelsRoleDefaultPolicy`:

```
{
    "Version": "2012-10-17",
    "Statement": [
        ...,
        {
            "Action": [
                "dynamodb:DeleteItem",
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:Scan",
                "dynamodb:Query",
                "dynamodb:UpdateItem",
                "dynamodb:UpdateTable",
                "dynamodb:GetRecords"
            ],
            "Resource": "*",
            "Effect": "Allow"
        }
    ]
}
```

## DetectCelebrities

- Attach policy: `AmazonBedrockFullAccess`
- Add the following policy in `DetectCelebritiesRoleDefaultPolicy`:

```
{
    "Version": "2012-10-17",
    "Statement": [
        ...
        {
            "Action": "rekognition:*",
            "Resource": "*",
            "Effect": "Allow"
        },
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:DeleteItem",
                "dynamodb:GetItem",
                "dynamodb:Scan",
                "dynamodb:Query",
                "dynamodb:UpdateItem",
                "rekognition:*",
                "dynamodb:UpdateTable",
                "dynamodb:GetRecords"
            ],
            "Resource": "*"
        }
    ]
}
```

## SegmentNewsRole
- Attach policy: `AmazonBedrockFullAccess`
- Add the following policy in `SegmentNewsRoleDefaultPolicy`:

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "aoss:APIAccessAll",
            "Resource": "*"
        },
        {
            "Action": [
                "dynamodb:DeleteItem",
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:Scan",
                "dynamodb:Query",
                "dynamodb:UpdateItem",
                "dynamodb:UpdateTable",
                "dynamodb:GetRecords"
            ],
            "Resource": "*",
            "Effect": "Allow"
        },
        ...
    ]
}
```