import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, NoSuchWindowException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time

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
options.headless = True  # Ejecuta el navegador en modo headless (sin interfaz gráfica)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 10)

# Función para extraer información adicional
def extract_additional_info(url):
    driver.get(url)
    founders_data = []
    # Esperar a que la sección de fundadores esté presente

    wait.until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'leading-snug')))
    wait.until(
        EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div.leading-snug>div.font-bold")))
    wait.until(
        EC.visibility_of_all_elements_located((By.XPATH, "//*[contains(@aria-label, 'LinkedIn profile')]")))
    founders_info = driver.find_elements(By.CLASS_NAME, 'leading-snug')

    for founder in founders_info:
        try:
            wait.until(EC.visibility_of_all_elements_located((By.XPATH, "//*[contains(@aria-label, 'LinkedIn profile')]")))

            name_element = founder.find_elements(By.TAG_NAME, "div")
            name = name_element[0].text  # Obtener el nombre del fundador
            position = ''
            if len(name_element) >= 3:
                position = name_element[1].text  # Obtener el cargo del fundador

            linkedin_element = founder.find_element(By.XPATH, "//*[contains(@aria-label, 'LinkedIn profile')]")
            linkedin_url = linkedin_element.get_attribute("href")
            founders_data.append({
                "Fundador nombre": name,
                "Cargo del fundador": position,
                "LinkedIn Personaldel fundador": linkedin_url
            })
        except (NoSuchElementException, StaleElementReferenceException) as e:
            print(f"Error extracting founder info: {e}")
    return founders_data

# Lista para almacenar los datos de las empresas
all_companies = []

# Iterar sobre todas las páginas de resultados
page = 0
while True:
    response = requests.post(algolia_url, json={"requests":[{"indexName":"YCCompany_production","params":f"query=&hitsPerPage=100&maxValuesPerFacet=100&page={page}&facets=%5B%5D&tagFilters="}]}, params=params)
    data = response.json()
    hits = data.get('results', [])[0].get('hits', [])
    
    if not hits:
        break
    
    for hit in hits:
        company_url = f"https://www.ycombinator.com/companies/{hit.get('slug')}"
        additional_info = extract_additional_info(company_url)
        
        for founder in additional_info:
            company = {
                "Nombre empresa": hit.get('name'),
                "Hiring (Yes/No)": hit.get('isHiring'),
                "Correo Fundador": "",
                "URL statup": hit.get('website'),
                "LinkedIn Empresa": "",
                "Fundador nombre": founder["Fundador nombre"],
                "Cargo del fundador": founder["Cargo del fundador"],
                "LinkedIn Personaldel fundador": founder["LinkedIn Personaldel fundador"],
                "Fecha del fundador": hit.get('launched_at')
            }
            all_companies.append(company)
    
    page += 1

driver.quit()

df = pd.DataFrame(all_companies)
df.to_excel("ycombinator_companies.xlsx", index=False)
