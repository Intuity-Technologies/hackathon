@description('Azure region for resource deployment.')
param location string

@description('Globally unique storage account name.')
param storageAccountName string

@description('Storage SKU for ADLS account.')
@allowed([
  'Standard_LRS'
  'Standard_GRS'
  'Standard_ZRS'
])
param storageSku string = 'Standard_LRS'

@description('Blob containers used by the ETL pipeline.')
param dataContainers array = [
  'raw'
  'curated'
  'signals'
]

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: storageSku
  }
  kind: 'StorageV2'
  properties: {
    isHnsEnabled: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    accessTier: 'Hot'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [for c in dataContainers: {
  parent: blobService
  name: c
  properties: {
    publicAccess: 'None'
  }
}]

output storageAccountName string = storage.name
output storageAccountId string = storage.id
