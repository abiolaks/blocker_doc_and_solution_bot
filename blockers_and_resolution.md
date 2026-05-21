
### Problem: The bot we created is not under the manage apps,

### Solution: 
- This means your bot app hasn't been uploaded/submitted to Teams yet.This means your bot app hasn't been uploaded/submitted to Teams yet. 
You need to create an app package and upload it. Here's what to do:

#### Step 1: Create Your App Manifest.
- Create a file called manifest.json with this structure:

```
  {
  "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
  "manifestVersion": "1.16",
  "id": "<YOUR-BOT-APP-ID>",
  "version": "1.0.0",
  "packageName": "com.yourcompany.blocker_doc_bot",
  "name": {
    "short": "blocker_doc_bot"
  },
  "description": {
    "short": "Company bot",
    "full": "Internal company bot"
  },
  "icons": {
    "color": "color.png",
    "outline": "outline.png"
  },
  "accentColor": "#FFFFFF",
  "bots": [
    {
      "botId": "<YOUR-BOT-APP-ID>",
      "scopes": ["personal", "team", "groupChat"]
    }
  ],
  "permissions": ["identity", "messageTeamMembers"]
}
```
#### Step 2: Find Your Bot App ID

- Go to Azure Portal → Your Bot (blocker_doc_bot)
- Click Overview
- Copy the Microsoft App ID

### Step 3: Package the App
- Create a .zip file containing:
```
  blocker_doc_bot.zip
  ├── manifest.json
  ├── color.png     (192x192 px icon)
  └── outline.png   (32x32 px icon)
```


#### Step 4: Upload to Teams (Two Options)
##### Option A 
— You upload it yourself (if allowed):
- Open Microsoft Teams
- Go to Apps → Manage your apps
- Click Upload an app → Upload a custom app
- Select your .zip file

##### Option B — Admin uploads it (Recommended):

- Send the .zip package to your IT Admin
- They upload it via Teams Admin Center → Manage apps → Upload
- Once uploaded and approved, it becomes available org-wide


What to Send Your IT Admin
Along with the earlier email, attach:

- The .zip app package
- Your Bot App ID from Azure
