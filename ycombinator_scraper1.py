import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
from datetime import datetime
import logging
from collections import defaultdict

# Configurar logging
logging.basicConfig(filename='ycombinator_scraper.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# URL del recurso de datos
algolia_url = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/*/queries"

# Parámetros para la solicitud
params = {
    "x-algolia-agent": "Algolia for JavaScript (3.35.1); Browser; JS Helper (3.16.1)",
    "x-algolia-application-id": "45BWZJ1SGC",
    "x-algolia-api-key": "MjBjYjRiMzY0NzdhZWY0NjExY2NhZjYxMGIxYjc2MTAwNWFkNTkwNTc4NjgxYjU0YzFhYTY2ZGQ5OGY5NDMxZnJlc3RyaWN0SW5kaWNlcz0lNUIlMjJZQ0NvbXBhbnlfcHJvZHVjdGlvbiUyMiUyQyUyMllDQ29tcGFueV9CeV9MYXVuY2hfRGF0ZV9wcm9kdWN0aW9uJTIyJTVEJnRhZ0ZpbHRlcnM9JTVCJTIyeWNkY19wdWJsaWMlMjIlNUQmYW5hbHl0aWNzVGFncz0lNUIlMjJ5Y2RjJTIyJTVE"
}

# Configuración de Selenium
options = Options()
options.headless = True
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 20)

def extract_additional_info(url, company_name):
    driver.get(url)
    company_data = []
    
    try:
        linkedin_element = None
        company_linkedin = 'N/A'
        try:
            # Esperar hasta que el div con la clase 'ycdc-card' esté presente
            linkedin_element = wait.until(
                EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div.ycdc-card>div.space-x-2>a.bg-image-linkedin")))
            company_linkedin = linkedin_element[0].get_attribute("href")
        except TimeoutException:
            logging.error(f"Timeout while loading page for company: {company_name}, URL: {url}")

        # Agregar datos de la empresa
        company_data.append({
            "Nombre empresa": company_name,
            "LinkedIn": company_linkedin,
            "Fundador nombre": "Company",
            "Cargo del fundador": "Company"
        })
        
        # Intentar obtener información de los fundadores
        try:
            wait.until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'leading-snug')))
            wait.until(
                EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div.leading-snug>div.font-bold")))
            wait.until(
                EC.visibility_of_all_elements_located((By.XPATH, "//*[contains(@aria-label, 'LinkedIn profile')]")))

            founders_info = driver.find_elements(By.CLASS_NAME, 'leading-snug')
            
            for founder in founders_info:
                founder_data = {
                    "Nombre empresa": company_name,
                    "LinkedIn": "N/A",
                    "Fundador nombre": "N/A",
                    "Cargo del fundador": "N/A"
                }
                
                try:
                    name_element = founder.find_element(By.CLASS_NAME, "font-bold")
                    founder_data["Fundador nombre"] = name_element.text if name_element else "N/A"
                    
                    position_elements = founder.find_elements(By.TAG_NAME, "div")
                    if len(position_elements) >= 2:
                        pos = position_elements[1].text
                        if pos in ["Founder", "CEO", "CTO", "CPO"]:
                            founder_data["Cargo del fundador"] = pos
                    
                    # Buscar LinkedIn del fundador en un div específico
                    try:
                        linkedin_element = founder.find_element(By.XPATH, ".//div[contains(@class, 'mt-1 space-x-2')]//a[contains(@aria-label, 'LinkedIn profile')]")
                        founder_data["LinkedIn"] = linkedin_element.get_attribute("href")
                    except NoSuchElementException:
                        logging.info(f"No LinkedIn profile found for founder {founder_data['Fundador nombre']}")
                    
                    company_data.append(founder_data)
                except Exception as e:
                    logging.error(f"Error extracting founder info for {company_name}: {e}")
        except TimeoutException:
            logging.info(f"No founder data found for company: {company_name}")
    
    except TimeoutException:
        logging.error(f"Timeout while loading page for company: {company_name}, URL: {url}")
    except Exception as e:
        logging.error(f"Unexpected error for company {company_name}: {e}")
    
    return company_data

# Función para convertir las fechas
def convert_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d') if timestamp else "N/A"

# Lista para almacenar los datos de todas las empresas
all_companies = []

# Diccionario para almacenar las empresas por batch
companies_by_batch = defaultdict(list)

# Iterar sobre todas las páginas de resultados para obtener todas las empresas
page = 0
while True:
    response = requests.post(algolia_url, json={"requests":[{"indexName":"YCCompany_production","params":f"query=&hitsPerPage=100&maxValuesPerFacet=100&page={page}&facets=%5B%5D&tagFilters="}]}, params=params)
    data = response.json()
    hits = data.get('results', [])[0].get('hits', [])
    
    if not hits:
        break
    
    for hit in hits:
        batch = hit.get('batch', 'Unknown')
        company_url = f"https://www.ycombinator.com/companies/{hit.get('slug')}"
        company_name = hit.get('name')
        
        logging.info(f"Scraping company: {company_name}")
        
        company_data = extract_additional_info(company_url, company_name)
        
        for entry in company_data:
            entry.update({
                "Hiring (Yes/No)": "Yes" if hit.get('isHiring') else "No",
                "URL startup": hit.get('website', 'N/A'),
                "Fecha del fundador": convert_timestamp(hit.get('launched_at')),
                "Batch": batch
            })
        
        companies_by_batch[batch].extend(company_data)
    
    page += 1
    time.sleep(2)

# Ordenar los batches de manera descendente
sorted_batches = sorted(companies_by_batch.keys(), reverse=True)

# Crear un DataFrame con todos los datos ordenados por batch
all_companies = []
for batch in sorted_batches:
    all_companies.extend(companies_by_batch[batch])

df = pd.DataFrame(all_companies)

# Crear un archivo Excel con todos los datos en una sola hoja
df.to_excel("ycombinator_companies_sorted.xlsx", index=False)

logging.info("Scraping completed. Data saved to ycombinator_companies_sorted.xlsx")
