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

@description('Data access mode used by the deployed apps.')
param pipelineDataMode string = 'adls'

@description('Signals file system used by the API and web app.')
param signalsFileSystem string = 'signals'

@description('Signals parquet path consumed by the API and web app.')
param signalsFilePath string = 'housing_pressure/area_level=county/part-000.parquet'

@description('Demo artifact file system used by the API and web app.')
param demoArtifactsFileSystem string = 'demo'

@description('Overview artifact path for the judged dashboard experience.')
param demoOverviewPath string = 'housing_pressure/overview.json'

@description('Leaderboard artifact path for the judged dashboard experience.')
param demoLeaderboardPath string = 'housing_pressure/leaderboard.json'

@description('Area detail artifact path for the judged dashboard experience.')
param demoAreaDetailPath string = 'housing_pressure/area_detail.json'

@description('Compare artifact path for the judged dashboard experience.')
param demoComparePath string = 'housing_pressure/compare.json'

@description('Trend artifact path for the judged dashboard experience.')
param demoTrendsPath string = 'housing_pressure/trends.json'

@description('Sources manifest path for the judged dashboard experience.')
param demoSourcesPath string = 'housing_pressure/sources_manifest.json'

@description('In-process cache TTL for Azure-hosted demo artifact reads.')
param demoCacheTtlSeconds int = 120

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
    pipelineDataMode: pipelineDataMode
    signalsFileSystem: signalsFileSystem
    signalsFilePath: signalsFilePath
    demoArtifactsFileSystem: demoArtifactsFileSystem
    demoOverviewPath: demoOverviewPath
    demoLeaderboardPath: demoLeaderboardPath
    demoAreaDetailPath: demoAreaDetailPath
    demoComparePath: demoComparePath
    demoTrendsPath: demoTrendsPath
    demoSourcesPath: demoSourcesPath
    demoCacheTtlSeconds: demoCacheTtlSeconds
  }
}

module webApp './modules/web-app.bicep' = {
  name: 'flaskWebAppDeployment'
  params: {
    location: location
    webAppName: webAppName
    webAppPlanName: webAppPlanName
    storageAccountName: storage.outputs.storageAccountName
    storageAccountId: storage.outputs.storageAccountId
    pipelineDataMode: pipelineDataMode
    predictionApiBaseUrl: 'https://${functionApp.outputs.functionDefaultHostName}'
    signalsFileSystem: signalsFileSystem
    signalsFilePath: signalsFilePath
    demoArtifactsFileSystem: demoArtifactsFileSystem
    demoOverviewPath: demoOverviewPath
    demoLeaderboardPath: demoLeaderboardPath
    demoAreaDetailPath: demoAreaDetailPath
    demoComparePath: demoComparePath
    demoTrendsPath: demoTrendsPath
    demoSourcesPath: demoSourcesPath
    demoCacheTtlSeconds: demoCacheTtlSeconds
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
