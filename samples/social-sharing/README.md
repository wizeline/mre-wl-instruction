# Demo app for sharing youtube video from s3, using react as frontend and lambda function as BE

## Installation 

### Setup for youtube api
- Following link to setup project and using youtube api: https://developers.google.com/identity/protocols/oauth2/web-server#prerequisites
--- Create project: https://console.cloud.google.com/projectcreate
  ![alt create project](/assets/creat-project.png)
--- Enable for youtube API: https://console.cloud.google.com/marketplace/product/google/youtube.googleapis.com
--- Create credentials (OAuth 2.0 Client IDs)  (need to add frontend url under `Authorized JavaScript origins` and `Authorized redirect URIs` )
 ![alt create credential](/assets/creat-credentials.png)
--- Add test users
  ![alt add test users](/assets/add-test-users.png)

### Deploy lambda function
- Create bucket to upload video
- Update bucket name in app.py
- Deploy app (chalive deploy)

### Deploy frontend
- update Client_Id in App.js
- Deploy to AWS (npm run deploy)