# To Do

## Data
[x] Generate UUID for each rows  
[x] Search each URL with WebFetch  
[ ] Search with Tavily.
[ ] Find if there is a freemium account, return in new column "Has Freemium"  
[ ] Store .md file with referred UUID in data/websites-markdown

## Categorization
[x] Refine tool categories (look at categorization at Statista, Sales Tech  
[x] Get category for each tool, store in new column.  
[ ] Use Apify to get G2 rating for each tool.  
[ ] Get LinkedIn URL for each tool/company  
[ ] Use Apify LinkedIn URL to get Company City, Country (location)  

## Interface
[x] Generate HTML interface for database (site/, see scripts/README.md)  
[x] Bar chart on count(rows) per Category (plus Has freemium, Has trial)  
[x] Host on Cloudflare (Worker, static assets), gated with Cloudflare Access  
[ ] Bar chart on count(rows) per Country  
[ ] Filter: Categories, G2 rating, City, Country (Categories done)  
[ ] Allow user to add comments to entry "comments" column and "date reviewed" column.
