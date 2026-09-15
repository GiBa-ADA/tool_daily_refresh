### 🪴 REFRESH [ACC][DAILY] check template

---

<aside>

🪴To refresh for check **sales-traffic | affiliate | product** accuracy daily in https://drive.google.com/drive/folders/1tGTPM213DbNASC-e3LCfjc5y-61fDQ77?usp=drive_link

🪴To refresh for check **media** accuracy daily in https://drive.google.com/drive/folders/1v09SWsezqw6TU86qJaXk0SlEgOqjK6jQ?usp=drive_link

🪴To refresh for check **content** accuracy daily in https://drive.google.com/drive/folders/1c53dexo74jCupzgU-D_YfQCZjI9kJGr-?usp=drive_link
    
🪴Tab sheet impact:
1. [metric] automated_input — make sure we had product: **CHECK DATA DAILY**
2. [metric] database
</aside>
---
<h3>i. Structure </h3>
    
    ```
    ├───backend
    ├───chrome_extension
    │   └───assets
    ├───extracted                   -> store file extracted from db
    │   └───inova_pharma
    │       └───2026-09-15
    │           └───database
    ├───logs                        -> logs of run pipeline
    ├───sql                         -> store query to refresh metric
    │   ├───database                -> ecommerce table
    │   │   ├───content
    │   │   ├───media
    │   │   ├───product
    │   │   ├───sales_affiliate
    │   │   └───sales_traffic
    │   └───ui                      -> raw_seller_metrics
    │       ├───media
    │       └───sales_traffic
    └───src
        ├───application
        │   ├───services
        │   └───use_cases
        ├───config                  -> file setting for new metric
        │   ├───api_key
        │   ├───client_key
        ├───domain
        │   ├───models
        │   └───rules
        ├───infrastructure
        │   ├───database
        │   ├───logging
        │   └───spreadsheet
        └───utils
    ```

---

<h3>ii. Requirements</h3> 

**step 1: download tool to refresh:**

```
git clone https://github.com/GiBa-ADA/tool_daily_refresh.git
```
--


**step 2: enter your database credentials:**

Can be follow up with below process:    (Run all in Terminal)

```
cd <tool_project_in_your_local>

cp .env.example .env

Copy-Item .env.example .env
```
--

**step 3: check your client db connection**

Can be follow up with below process:    (Run all in Terminal)

```
cd <tool_project_in_your_local>

cp db_connection.yaml.example db_connection.yaml

Copy-Item db_connection.yaml.example db_connection.yaml
```
After create file ``` .yaml ```, you can be copy-paste if you have some clients.

--

**step 4: check your seller scope**

Contact with Huy Le (SuSu) in order to receive ```config``` folder.

After that, please check your client ```.csv``` file to ensure it contains all the seller IDs for this client.

```sql
├───config
│   ├───api_key
│   ├───client_key
```

---
    
<h3>iii. How to run for refresh data</h3>

**For check availabel clients and spreadsheets**

```
python main.py --list
```

**For refresh specific client and all metrics**

```
python main.py --client <client_name>

e.g. python main.py --client shiseido
```

**For refresh specific client and specific metric**

```
python main.py --client <client_name> --metric <metric_name>

e.g. python main.py --client shiseido --metric sales_traffic
```

**For refresh all exist clients and metrics in db_connection** 

```
python main.py 
```

**Metric refresh flow:**
sales_traffic → sales_affiliate → product → media → content
    
 
