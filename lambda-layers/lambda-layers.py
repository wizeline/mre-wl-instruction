import boto3
import json
import sys

client = boto3.client('lambda')

def create_lambda_layers_from_file(file_path):
    with open(file_path, 'r') as file:
        layer_info = json.load(file)
        
        for layer in layer_info:
            print(layer)
            layer_name = layer['name']
            compatible_runtimes = layer['compatible_runtimes']
            compatible_architectures = layer['compatible_architectures']
            
            layer_zip_file = f'./layers/{layer_name}.zip'
            
            create_lambda_layer(layer_name, layer_zip_file, compatible_runtimes, compatible_architectures)
            
        return 1

def create_lambda_layer(layer_name, layer_zip_file, compatible_runtimes, compatible_architectures):
    with open(layer_zip_file, 'rb') as file:
        layer_zip = file.read()

        if len(compatible_runtimes) > 0 and len(compatible_architectures) > 0:   
            response = client.publish_layer_version(
                LayerName=layer_name,
                Content={
                    'ZipFile': layer_zip
                },
                CompatibleRuntimes=[compatible_runtimes],
                CompatibleArchitectures=[compatible_architectures]
            )
        elif len(compatible_runtimes) > 0 and len(compatible_architectures) == 0:
            response = client.publish_layer_version(
                LayerName=layer_name,
                Content={
                    'ZipFile': layer_zip
                },
                CompatibleRuntimes=[compatible_runtimes]
            )
        elif len(compatible_runtimes) == 0 and len(compatible_architectures) > 0:
            response = client.publish_layer_version(
                LayerName=layer_name,
                Content={
                    'ZipFile': layer_zip
                },
                CompatibleArchitectures=[compatible_architectures]
            )
        
        layer_arn = response['LayerVersionArn']
        print(f"Lambda layer '{layer_name}' created with ARN: {layer_arn}")



if __name__ == '__main__':
    layer_info_file = './layer-info.json'
    result = create_lambda_layers_from_file(layer_info_file)

    sys.exit(0) if result else sys.exit(1)

    
    
