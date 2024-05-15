export type AmplifyDependentResourcesAttributes = {
  "api": {
    "clipcrunchapi": {
      "ApiId": "string",
      "ApiName": "string",
      "RootUrl": "string"
    }
  },
  "auth": {
    "frontend1790dc25": {
      "AppClientID": "string",
      "AppClientIDWeb": "string",
      "CreatedSNSRole": "string",
      "IdentityPoolId": "string",
      "IdentityPoolName": "string",
      "UserPoolArn": "string",
      "UserPoolId": "string",
      "UserPoolName": "string"
    }
  },
  "custom": {
    "vectordbaccess": {
      "AccessPolicyName": "string"
    }
  },
  "function": {
    "CalculateVectorEmbeddingForImagesInS3IndexInOpensearch": {
      "Arn": "string",
      "LambdaExecutionRole": "string",
      "LambdaExecutionRoleArn": "string",
      "MediaConvertExecutionRole": "string",
      "Name": "string",
      "Region": "string"
    },
    "frontendClipCrunchersShared": {
      "Arn": "string"
    },
    "frontendf6b68d3c": {
      "Arn": "string",
      "LambdaExecutionRole": "string",
      "LambdaExecutionRoleArn": "string",
      "Name": "string",
      "Region": "string"
    }
  },
  "storage": {
    "s3storage": {
      "BucketName": "string",
      "Region": "string"
    }
  },
  "vectordb": {
    "opensearch": {
      "CollectionEndpoint": "string",
      "opensearchServerlessCollectionARN": "string",
      "opensearchServerlessCollectionName": "string",
      "opensearchServerlessIndexName": "string"
    }
  }
}