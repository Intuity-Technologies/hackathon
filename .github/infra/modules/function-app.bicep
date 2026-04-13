@description('Azure region for the function resources.')
param location string

@description('Function App name.')
param functionAppName string

@description('Function hosting plan name.')
param functionPlanName string

@description('Storage account name used by ETL/API.')
param storageAccountName string

@description('Storage account resource ID.')
param storageAccountId string

@description('Application Insights connection string.')
param appInsightsConnectionString string

@description('Application Insights instrumentation key.')
param appInsightsInstrumentationKey string

@description('Data access mode used by the deployed app.')
param pipelineDataMode string = 'adls'

@description('Signals file system name used by API.')
param signalsFileSystem string = 'signals'

@description('Signals parquet path consumed by API.')
param signalsFilePath string = 'housing_pressure/area_level=county/part-000.parquet'

@description('Demo artifact file system used by API.')
param demoArtifactsFileSystem string = 'demo'

@description('Overview artifact path consumed by API.')
param demoOverviewPath string = 'housing_pressure/overview.json'

@description('Leaderboard artifact path consumed by API.')
param demoLeaderboardPath string = 'housing_pressure/leaderboard.json'

@description('Area detail artifact path consumed by API.')
param demoAreaDetailPath string = 'housing_pressure/area_detail.json'

@description('Compare artifact path consumed by API.')
param demoComparePath string = 'housing_pressure/compare.json'

@description('Trend artifact path consumed by API.')
param demoTrendsPath string = 'housing_pressure/trends.json'

@description('Sources manifest path consumed by API.')
param demoSourcesPath string = 'housing_pressure/sources_manifest.json'

@description('In-process demo artifact cache TTL in seconds.')
param demoCacheTtlSeconds int = 120

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource functionPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: functionPlanName
  location: location
  kind: 'functionapp'
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: functionPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      ftpsState: 'FtpsOnly'
      appSettings: [
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storage.listKeys().keys[0].value}'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'ENABLE_ORYX_BUILD'
          value: 'true'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsightsInstrumentationKey
        }
        {
          name: 'AZURE_STORAGE_ACCOUNT'
          value: storageAccountName
        }
        {
          name: 'PIPELINE_DATA_MODE'
          value: pipelineDataMode
        }
        {
          name: 'SIGNALS_FILE_SYSTEM'
          value: signalsFileSystem
        }
        {
          name: 'SIGNALS_FILE_PATH'
          value: signalsFilePath
        }
        {
          name: 'DEMO_ARTIFACTS_FILE_SYSTEM'
          value: demoArtifactsFileSystem
        }
        {
          name: 'DEMO_OVERVIEW_PATH'
          value: demoOverviewPath
        }
        {
          name: 'DEMO_LEADERBOARD_PATH'
          value: demoLeaderboardPath
        }
        {
          name: 'DEMO_AREA_DETAIL_PATH'
          value: demoAreaDetailPath
        }
        {
          name: 'DEMO_COMPARE_PATH'
          value: demoComparePath
        }
        {
          name: 'DEMO_TRENDS_PATH'
          value: demoTrendsPath
        }
        {
          name: 'DEMO_SOURCES_PATH'
          value: demoSourcesPath
        }
        {
          name: 'DEMO_CACHE_TTL_SECONDS'
          value: string(demoCacheTtlSeconds)
        }
      ]
    }
  }
}

resource blobDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountId, functionApp.id, 'Storage Blob Data Contributor')
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
    )
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output functionAppId string = functionApp.id
output functionAppName string = functionApp.name
output functionPrincipalId string = functionApp.identity.principalId
output functionDefaultHostName string = functionApp.properties.defaultHostName
