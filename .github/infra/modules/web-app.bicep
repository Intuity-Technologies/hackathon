@description('Azure region for web resources.')
param location string

@description('Linux App Service plan name for Flask frontend.')
param webAppPlanName string

@description('Flask web app name.')
param webAppName string

@description('Public API base URL used by orchestrator.')
param predictionApiBaseUrl string

resource webPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: webAppPlanName
  location: location
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

resource webApp 'Microsoft.Web/sites@2023-12-01' = {
  name: webAppName
  location: location
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: webPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      ftpsState: 'FtpsOnly'
      appCommandLine: 'gunicorn --bind=0.0.0.0 --timeout 600 web:app'
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'PREDICTION_API_BASE_URL'
          value: predictionApiBaseUrl
        }
      ]
    }
  }
}

output webAppName string = webApp.name
output webAppDefaultHostName string = webApp.properties.defaultHostName
output webAppId string = webApp.id
