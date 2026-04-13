@description('Location for all resources.')
param location string = resourceGroup().location

@description('Storage account name. Must be globally unique, 3-24 lowercase alphanumeric.')
param storageAccountName string

@description('Function app name. Must be globally unique.')
param functionAppName string

@description('Function hosting plan name.')
param functionPlanName string = 'plan-irish-signals'

@description('Application Insights component name.')
param appInsightsName string = 'appi-irish-signals'

@description('Log Analytics workspace name.')
param logAnalyticsWorkspaceName string = 'log-irish-signals'

@description('Flask web app name for public demo UI.')
param webAppName string

@description('Flask web app hosting plan name.')
param webAppPlanName string = 'plan-irish-web'

@description('Key Vault name for shared secrets.')
param keyVaultName string

@description('Enable Azure ML workspace and registry deployment.')
param deployMlPlatform bool = true

@description('Azure ML workspace name.')
param mlWorkspaceName string = 'mlw-irish-signals'

@description('Container registry name used by Azure ML model deployments.')
param mlContainerRegistryName string = 'acririshsignals'

@description('Optional Static Web App name for landing pages.')
param staticWebAppName string = 'swa-irish-signals'

@description('Deploy optional Static Web App resource.')
param deployStaticWebApp bool = false

@description('Storage SKU for ADLS account.')
param storageSku string = 'Standard_LRS'

module storage './modules/storage.bicep' = {
  name: 'storageDeployment'
  params: {
    location: location
    storageAccountName: storageAccountName
    storageSku: storageSku
  }
}

module observability './modules/observability.bicep' = {
  name: 'observabilityDeployment'
  params: {
    location: location
    appInsightsName: appInsightsName
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
  }
}

module functionApp './modules/function-app.bicep' = {
  name: 'functionAppDeployment'
  params: {
    location: location
    functionAppName: functionAppName
    functionPlanName: functionPlanName
    storageAccountName: storage.outputs.storageAccountName
    storageAccountId: storage.outputs.storageAccountId
    appInsightsConnectionString: observability.outputs.appInsightsConnectionString
    appInsightsInstrumentationKey: observability.outputs.appInsightsInstrumentationKey
  }
}

module webApp './modules/web-app.bicep' = {
  name: 'flaskWebAppDeployment'
  params: {
    location: location
    webAppName: webAppName
    webAppPlanName: webAppPlanName
    predictionApiBaseUrl: 'https://${functionApp.outputs.functionDefaultHostName}'
  }
}

module keyVault './modules/key-vault.bicep' = {
  name: 'keyVaultDeployment'
  params: {
    location: location
    keyVaultName: keyVaultName
    tenantId: subscription().tenantId
  }
}

module mlPlatform './modules/ml-platform.bicep' = if (deployMlPlatform) {
  name: 'mlPlatformDeployment'
  params: {
    location: location
    mlWorkspaceName: mlWorkspaceName
    mlContainerRegistryName: mlContainerRegistryName
    storageAccountId: storage.outputs.storageAccountId
    keyVaultId: keyVault.outputs.keyVaultId
    appInsightsId: observability.outputs.appInsightsId
  }
}

module staticWeb './modules/static-web.bicep' = if (deployStaticWebApp) {
  name: 'staticWebDeployment'
  params: {
    staticWebAppName: staticWebAppName
  }
}

output storageAccountNameOut string = storage.outputs.storageAccountName
output functionAppNameOut string = functionApp.outputs.functionAppName
output functionAppHostname string = functionApp.outputs.functionDefaultHostName
output webAppNameOut string = webApp.outputs.webAppName
output webAppHostname string = webApp.outputs.webAppDefaultHostName
output keyVaultNameOut string = keyVault.outputs.keyVaultName
output keyVaultUriOut string = keyVault.outputs.keyVaultUri
output mlWorkspaceNameOut string = deployMlPlatform ? mlPlatform!.outputs.mlWorkspaceName : 'disabled'
output staticWebAppNameOut string = deployStaticWebApp ? staticWeb!.outputs.staticWebAppName : 'disabled'
