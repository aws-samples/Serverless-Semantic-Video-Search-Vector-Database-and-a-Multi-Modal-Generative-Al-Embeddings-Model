# Serverless Semantic Video Search Using a Vector Database and a Multi-Modal Generative AI Embeddings Model

You can find the related blogpost to this repository here: 
[Implement serverless semantic search of image and live video with Amazon Titan Multimodal Embeddings!](https://aws.amazon.com/blogs/machine-learning/implement-serverless-semantic-search-of-image-and-live-video-with-amazon-titan-multimodal-embeddings/)

Deploying the infrastructure requires you to have sufficient AWS privileges to do so.

> [!WARNING]
> **_This example is for experimental purposes only and is not production ready. The deployment of this sample can incur costs. Please ensure to remove infrastructure via the provided scripts when not needed anymore._**

---

![Screenshot of the solution](/img/solution.png)

---
1. [AWS Account Prerequisites](#aws-account-prerequisites)
1. [Deploy to Amplify](#deploy-to-amplify)
2. [Local Development Prerequisites](#local-development-prerequisites)
3. [Local Build](#local-build)
4. [Clean Up](#clean-up-resources)
5. [Usage Instructions](#usage-instructions)
6. [Solution Walkthrough](#solution-walkthrough)

## AWS Account Prerequisites

* Enabled Model Access for Amazon Bedrock `Titan Multimodal Embeddings G1` using [instructions](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)

## Deploy to Amplify

[![amplifybutton](https://oneclick.amplifyapp.com/button.svg)](https://us-east-1.console.aws.amazon.com/amplify/home#/deploy?repo=https://github.com/aws-samples/Serverless-Semantic-Video-Search-Vector-Database-and-a-Multi-Modal-Generative-Al-Embeddings-Model)

* Click the button above to deploy this solution with default parameters directly in your AWS account or [use the Amplify Console to setup Github Access](https://docs.aws.amazon.com/amplify/latest/userguide/setting-up-GitHub-access.html#setting-up-github-app).
* In the select service role section, create a new service role and see [Amplify Service Role](#amplify-service-role) for required permissions used for the deployment role

> [!CAUTION]
> We advise you to restrict access to branches using a username and password to limit resource consumption by unintended users by following this [guide](https://docs.aws.amazon.com/amplify/latest/userguide/access-control.html).

* Add a [SPA Redirect](#spa-redirect)

### Amplify Service Role

* Attach **AdministratorAccess** rather than **AdministratorAccess-Amplify**
  * ***Optional:*** You can use **AdministratorAccess-Amplify** but add a new IAM policy with additional required permissions which may include:
    * "aoss:BatchGetCollection"
    * "aoss:CreateAccessPolicy"
    * "aoss:CreateCollection"
    * "aoss:GetSecurityPolicy"
    * "aoss:CreateSecurityPolicy"
    * "aoss:DeleteSecurityPolicy"
    * "aoss:DeleteCollection"
    * "aoss:DeleteAccessPolicy"
    * "aoss:TagResource"
    * "aoss:UntagResource"
    * "kms:Decrypt"
    * "kms:Encrypt"
    * "kms:DescribeKey"
    * "kms:CreateGrant"

## Local Development Prerequisites

* [AWS CLI]((https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html))
* [python 3.11](https://www.python.org/downloads/release/python-3119/)
* pip 24.0 or higher
* [virtualenv 20.25.0 or higher](https://virtualenv.pypa.io/en/stable/installation.html)
* [node v20.10.0 or higher](https://nodejs.org/en/download)
* npm 10.5.0 or higher
* [amplify CLI 12.10.1 or higher](https://docs.amplify.aws/javascript/tools/cli/start/set-up-cli/)
    * Use **us-east-1** for deployment region
    * See [Amplify Service Role](#amplify-service-role) for required permissions used for the deployment role

---
## Local Build

* `amplify init`
* `npm ci`
* `amplify push`
* `npm run dev`

> [!IMPORTANT] 
> We advise you to run the application in a sandbox account and deploy the frontend locally.

### [Optional] Manually Deployed Cloud Hosted Frontend

> [!CAUTION]
> Using the Cloud hosted frontend with the default cognito settings of allowing any user to create and confirm an account will allow any user with knowledge of the deployed URL to upload images/video which has the potential to incur unexpected charges in your AWS account. You can implement a human review of new sign-up requests in cognito by following instructions in the Cognito Developer Guide for [Allowing users to sign up in your app but confirming them as a user pool administrator](https://docs.aws.amazon.com/cognito/latest/developerguide/signing-up-users-in-your-app.html#signing-up-users-in-your-app-and-confirming-them-as-admin)

* [Deploy and host app](https://docs.amplify.aws/gen1/javascript/start/getting-started/hosting/)
* Add a [SPA Redirect](#spa-redirect)
 
### SPA Redirect
Follow the [instructions](https://docs.aws.amazon.com/amplify/latest/userguide/creating-editing-redirects.html) to create a redirect for [single page web apps (SPA)](https://docs.aws.amazon.com/amplify/latest/userguide/redirect-rewrite-examples.html#redirects-for-single-page-web-apps-spa)

## Clean up resources

* [Full Cleanup Instructions](https://repost.aws/knowledge-center/amplify-delete-application)
  * `amplify delete` for local build

---

### Usage Instructions

1. Use the `Sign In` button to log in. Use the `Create Account` tab located at the top of the website to sign up for a new user account with your Amazon Cognito integration.

2. After successfully signing in, choose from the left sidebar to upload an image or video:

#### File Upload 
- Click on `Choose files` Button
- Select the images or videos from your local drive
- Click on `Upload Files`

### Webcam Upload
- Click `Allow` when your browser asks for permissions to access your webcam
- Click `Capture Image` and `Upload Image` when you want to upload a single image from your webcam
- Click `Start Video Capture`, `Stop Video Capture` and finally `Upload Video` to upload a video from your webcam

### Search

- Type your prompt in the `Search Videos` text field. Depending on your input in previous steps you can prompt i.e. `“Show me a person with glasses”`
- Lower the `confidence parameter` closer to 0, if you see fewer results than you were originally expecting


>[!TIP]
>The confidence is not a linear scale from 0 to 100. This confidence represents the vector distance between the user's query and the image in the database where 0 represents completely opposite vectors and 100 represents the same vector datapoint. 


## Solution Walkthrough

![Screenshot of the solution](/img/solution-architecture.png)

[Raw Solution Architecture Diagram](/diagrams/blogpost-mm.drawio)

### AWS Services Used
* Amazon Opensearch Serverless
* Amazon Bedrock
* AWS Lambda
* AWS S3
* Amazon Cognito
* AWS Elemental MediaConvert
* AWS Amplify [Deploying and hosting frontend and backend]
* Amazon Cloudfront [optional when using cloud hosted front-end]

### Manual clip upload process
1. User manually uploads video clips to S3 bucket (console, CLI or SDK).
2. S3 Bucket that holds video clips trigger an (s3:ObjectCreated) event for each clip (mp4 or webm) stored in S3.
3. Lambda function is subscribed to S3 Bucket (s3:ObjectCreated) event and queues up a MediaConvert job to convert the video clip into JPEG images.
4. Converted images are saved by MediaConvert into an S3 bucket.
5. S3 Bucket triggers an (s3:ObjectCreated) event for each image (JPEG) stored in S3.
6. Lambda function is subscribed to the (s3:ObjectCreated) event and generates an embedding using Amazon Titan Multimodal Embeddings, for every new image (JPEG) stored in the S3 Bucket.
7. Lambda function stores the embeddings in an OpenSearch Serverless index.

### Automated video ingestion using Kinesis Video Stream
1. Alternatively,  video clips can be ingested from a video source into a Kinesis Video Data Stream.
2. Kinesis Video Stream saves the video stream into video clips on the S3 Bucket.  This triggers the same above path for steps 2-7.

### Website Image Search
1. Use browses the website.
2. CloudFront CDN fetches the static web files in S3.
3. User authenticates and get token from Cognito User Pool.
4. User makes a search requests to the website, passing the request to the API Gateway.
5. API Gateway forwards the request to a Lambda Function.
6. Lambda function passes the search query to Amazon Titan Multimodal Embeddings and converts the request into an embedding.
7. Lambda function passes the embedding as part of the search, OpenSearch returns matching embeddings and Lambda function returns the matching images to the user.

### Website Kinesis Integration
While this solution doesn't create or manage a kinesis video stream, the website does include functionality for displaying a live kinesis video stream and replaying video clips from a kinesis video stream when an image is selected for self-managed kinesis video streams.

You can turn on this functionality by setting the ***kinesisVideoStreamIntegration*** parameter in the [frontend cloudformation template](amplify/backend/function/frontendf6b68d3c/frontendf6b68d3c-cloudformation-template.json) to **True** and setting ***__KINESIS_VIDEO_STREAM_INTEGRATION__*** to **true** in [vite.config.js](vite.config.js)


## Suggested minimum changes if used in production environments

> [!WARNING]
> **Making all the changes below does not guarantee a production ready environment. Before using this solution in production, you should carefully review all the resources deployed and their associated configuration to ensure it meets all of your organization's AWS Well Architected Framework requirements.**

* Opensearch configuration
  * [Audit logs should be enabled for Amazon Opensearch.](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/audit-logs.html#audit-log-enabling)
  * [Network access for Amazon OpenSearch Serverless](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-network.html)
* AWS S3 configuration
  * [Server access logging](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ServerLogs.html)
  * [Lifecycle policies](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
  * [Amazon Macie](https://docs.aws.amazon.com/macie/latest/user/what-is-macie.html)
* Lambda configuration
  * [Enabling X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/xray-services-lambda.html)
* IAM configuration
  * [Permissions boundaries](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)
* Cognito configuration
  * [MFA configuration](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-mfa.html)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
