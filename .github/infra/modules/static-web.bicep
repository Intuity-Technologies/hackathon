@description('Static Web App name for optional static demos.')
param staticWebAppName string

@description('Region for Static Web App.')
param location string = 'westeurope'

resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: staticWebAppName
  location: location
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {}
}

output staticWebAppName string = staticWebApp.name
output staticWebAppId string = staticWebApp.id
output staticWebDefaultHostname string = staticWebApp.properties.defaultHostname
