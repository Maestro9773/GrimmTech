"""
Скрипт для парсинга расписания с сайта ВГЛТУ.

Требования:
pip install selenium webdriver-manager

Использование:
python parser.py

Этот скрипт использует Selenium для открытия сайта ВГЛТУ,
ввода группы и сохранения расписания в schedule.json
"""

import os
import json
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Настройки
GROUP_NAME = "НТТС2-261-ОС"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "schedule.json")
BASE_URL = "https://vgltu.ru/obuchayushchimsya/raspisanie-zanyatij/"

def parse_schedule_for_date(driver, date_str):
    """Парсит расписание для конкретной даты."""
    print(f"Парсинг даты: {date_str}")
    
    # Открываем страницу
    driver.get(BASE_URL)
    
    # Ждём загрузки
    time.sleep(2)
    
    # Находим поле ввода группы
    try:
        group_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='группы']"))
        )
        group_input.clear()
        group_input.send_keys(GROUP_NAME)
        time.sleep(1)
    except:
        print("Не удалось найти поле ввода группы")
        return []
    
    # Находим и кликаем на дату
    try:
        # Конвертируем дату в формат сайта (ДД.ММ.ГГГГ)
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        site_date = date_obj.strftime("%d.%m.%Y")
        
        # Ищем поле даты
        date_input = driver.find_element(By.CSS_SELECTOR, "input[type='date']")
        date_input.clear()
        date_input.send_keys(site_date)
        time.sleep(1)
        
        # Кликаем кнопку "Найти"
        find_button = driver.find_element(By.XPATH, "//button[contains(text(), 'НАЙТИ') or contains(text(), 'Найти')]")
        find_button.click()
        time.sleep(3)
        
    except Exception as e:
        print(f"Ошибка при выборе даты: {e}")
        return []
    
    # Парсим расписание
    lessons = []
    try:
        # Ищем таблицу или блок с расписанием
        schedule_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".schedule-table, .raspisanie, table"))
        )
        
        rows = schedule_container.find_elements(By.TAG_NAME, "tr")
        for row in rows[1:]:  # Пропускаем заголовок
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 3:
                time = cells[0].text.strip()
                subject = cells[1].text.strip()
                room = cells[2].text.strip() if len(cells) > 2 else ""
                teacher = cells[3].text.strip() if len(cells) > 3 else ""
                
                if subject:  # Если есть предмет
                    lessons.append({
                        "time": time,
                        "subject": subject,
                        "room": room,
                        "teacher": teacher
                    })
        
    except Exception as e:
        print(f"Ошибка при парсинге расписания: {e}")
        # Если парсинг не удался, возвращаем пустой список
        return []
    
    return lessons

def parse_week():
    """Парсит расписание на неделю."""
    print(f"Начинаем парсинг расписания для группы {GROUP_NAME}")
    
    # Настройка Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Без графического интерфейса
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    schedule = {}
    
    try:
        # Парсим 7 дней начиная с сегодняшнего понедельника
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        
        for i in range(7):
            date = monday + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            lessons = parse_schedule_for_date(driver, date_str)
            schedule[date_str] = lessons
            
            # Пауза между запросами
            time.sleep(2)
        
        # Сохраняем в JSON
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(schedule, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Расписание сохранено в {OUTPUT_FILE}")
        print(f"Загружено {len(schedule)} дней")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    parse_week()
