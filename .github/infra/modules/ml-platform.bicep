@description('Azure region for ML platform resources.')
param location string

@description('Azure ML workspace name.')
param mlWorkspaceName string

@description('Container registry name for model images.')
param mlContainerRegistryName string

@description('Storage account resource ID for AML.')
param storageAccountId string

@description('Key vault resource ID for AML.')
param keyVaultId string

@description('Application Insights resource ID for AML.')
param appInsightsId string

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: mlContainerRegistryName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource mlWorkspace 'Microsoft.MachineLearningServices/workspaces@2023-04-01' = {
  name: mlWorkspaceName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    keyVault: keyVaultId
    applicationInsights: appInsightsId
    containerRegistry: containerRegistry.id
    storageAccount: storageAccountId
    publicNetworkAccess: 'Enabled'
    allowPublicAccessWhenBehindVnet: false
  }
}

output mlWorkspaceName string = mlWorkspace.name
output mlWorkspaceId string = mlWorkspace.id
output mlContainerRegistryName string = containerRegistry.name
output mlContainerRegistryLoginServer string = containerRegistry.properties.loginServer
