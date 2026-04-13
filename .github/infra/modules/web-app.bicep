@description('Azure region for web resources.')
param location string

@description('Linux App Service plan name for Flask frontend.')
param webAppPlanName string

@description('Flask web app name.')
param webAppName string

@description('Storage account name used by the dashboard and chat experience.')
param storageAccountName string

@description('Storage account resource ID used for RBAC.')
param storageAccountId string

@description('Data access mode used by the deployed app.')
param pipelineDataMode string = 'adls'

@description('Public API base URL used by orchestrator.')
param predictionApiBaseUrl string

@description('Signals file system used by the dashboard and chat experience.')
param signalsFileSystem string = 'signals'

@description('Signals parquet path consumed by the dashboard and chat experience.')
param signalsFilePath string = 'housing_pressure/area_level=county/part-000.parquet'

@description('Demo artifact file system used by the dashboard and chat experience.')
param demoArtifactsFileSystem string = 'demo'

@description('Overview artifact path consumed by the dashboard and chat experience.')
param demoOverviewPath string = 'housing_pressure/overview.json'

@description('Leaderboard artifact path consumed by the dashboard and chat experience.')
param demoLeaderboardPath string = 'housing_pressure/leaderboard.json'

@description('Area detail artifact path consumed by the dashboard and chat experience.')
param demoAreaDetailPath string = 'housing_pressure/area_detail.json'

@description('Compare artifact path consumed by the dashboard and chat experience.')
param demoComparePath string = 'housing_pressure/compare.json'

@description('Trend artifact path consumed by the dashboard and chat experience.')
param demoTrendsPath string = 'housing_pressure/trends.json'

@description('Sources manifest path consumed by the dashboard and chat experience.')
param demoSourcesPath string = 'housing_pressure/sources_manifest.json'

@description('In-process demo artifact cache TTL in seconds.')
param demoCacheTtlSeconds int = 120

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

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
        {
          name: 'PIPELINE_DATA_MODE'
          value: pipelineDataMode
        }
        {
          name: 'AZURE_STORAGE_ACCOUNT'
          value: storageAccountName
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

resource blobDataReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountId, webApp.id, 'Storage Blob Data Reader')
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
    )
    principalId: webApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output webAppName string = webApp.name
output webAppDefaultHostName string = webApp.properties.defaultHostName
output webAppId string = webApp.id
