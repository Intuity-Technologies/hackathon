# Best CSO datasets to use

1. **Population growth (county)**  
Use **PEA08**: Estimated population by age/sex/county/year.  
- Link: [Population & Migration Estimates data page](https://www.cso.ie/en/releasesandpublications/ep/p-pme/populationandmigrationestimatesapril2025/data/)  
- Table listed there: `https://data.cso.ie/table/PEA08`  
- Use case: compute `population_growth` as YoY % change by county.

2. **Rent pressure (location)**  
Use **RIQ02**: RTB Average Monthly Rent Report.  
- Link: [Housing Hub Rents](https://www.cso.ie/en/releasesandpublications/hubs/p-hh/housinghub/homepricesrents/rents/)  
- Direct table URL shown by CSO source link: [RIQ02](https://data.cso.ie/table/RIQ02)  
- Use case: compute `rent_growth` as YoY % change (quarterly or annual average) by location.

3. **Housing supply delivered (local authority)**  
Use **NDQ05** / **NDQ06**: New dwelling completions by local authority (+ type).  
- Link: [NDC Q4 2025 data page](https://www.cso.ie/en/releasesandpublications/ep/p-ndc/newdwellingcompletionsq42025/data/)  
- Tables: `NDQ05`, `NDQ06`  
- Use case: `housing_completions` by local authority/year (best direct supply metric).

4. **Housing supply pipeline (planning approvals)**  
Use **BHQ17** / **BHA14**: Planning permissions by local authority (quarterly/annual).  
- Link: [Planning Permissions Q4 2025 data page](https://www.cso.ie/en/releasesandpublications/ep/p-pp/planningpermissionsquarter4andyear2025/data/)  
- Tables: `BHQ17`, `BHA14`  
- Use case: leading indicator to pair with completions.

5. **Optional price pressure signal**  
Use **RPPI** product (includes `https://data.cso.ie/table/HPM09`, `https://data.cso.ie/table/HPM07` family).  
- Link: [Residential Property Price Index](https://www.cso.ie/en/statistics/prices/residentialpropertypriceindex/)  
- PxStat product link from CSO: [RPPI product](https://data.cso.ie/product/RPPI)

## Product hubs (useful shortcuts)
- Planning permissions: [PP product](https://data.cso.ie/product/PP)  
- New dwelling completions: [NDC product](https://data.cso.ie/product/NDC)
