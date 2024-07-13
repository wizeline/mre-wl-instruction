# Lambda Layers

Contains packages of lambda layers needed to install MRE's sample plugins

## Tool Versions

Python3 >= 3.11

## Lambda layer deployment

```bash
cd lambda-layers
./deploy.sh [aws-profile] [aws-region]
```

*(**Note**: if you have permission issue running `./deploy.sh`, you can run `chmod +x deploy.sh` to make it executable.)*