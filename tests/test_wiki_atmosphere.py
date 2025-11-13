"""
Автотесты для проверки состава атмосферы планет на ru.wikipedia.org
"""
import re
import pytest
from playwright.sync_api import Page, expect


def parse_percent(text: str) -> float:
    """
    Парсит процентное значение из текста, заменяя запятую на точку.
    
    Args:
        text: Строка с процентом (например, "20,95%", "20.95%", "≈ 20,95%")
    
    Returns:
        float: Числовое значение процента
    """
    # Удаляем все символы кроме цифр, запятых, точек и минусов
    cleaned = re.sub(r'[^\d,.\-]', '', text)
    # Заменяем запятую на точку
    cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        raise ValueError(f"Не удалось распарсить процент из текста: {text}")


@pytest.fixture(scope="function")
def page(browser):
    """Создает новую страницу с настройками для видимого браузера."""
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080}
    )
    page = context.new_page()
    yield page
    page.close()
    context.close()


class TestWikipediaAtmosphere:
    """Тесты для проверки состава атмосферы планет на Wikipedia."""
    
    BASE_URL = "https://ru.wikipedia.org"
    
    def test_earth_atmosphere_oxygen_positive(self, page: Page):
        """
        Позитивный тест: проверка содержания кислорода в атмосфере Земли.
        Ожидается значение ≈ 20,95% с допуском ±0,2.
        """
        # Шаг 1: Переход на главную страницу Wikipedia
        page.goto(self.BASE_URL)
        expect(page).to_have_url(re.compile(r".*wikipedia\.org.*"))
        
        # Шаг 2: Поиск статьи "Земля"
        search_input = page.locator('input[name="search"]')
        expect(search_input).to_be_visible(timeout=10000)
        search_input.fill("Земля")
        search_input.press("Enter")
        
        # Ожидание загрузки страницы (может быть страница результатов или статья)
        page.wait_for_load_state("networkidle", timeout=10000)
        
        # Если открылась страница результатов поиска, кликаем на первый результат
        page_title_text = page.locator('h1').inner_text()
        if "fulltext" in page.url or "Поиск" in page.title() or "Результаты поиска" in page_title_text:
            # Ищем ссылку на статью в результатах поиска - используем селектор для результатов поиска
            first_result = page.locator('.mw-search-result-heading a').first
            # Если не нашли, пробуем альтернативные селекторы
            try:
                expect(first_result).to_be_visible(timeout=2000)
            except:
                first_result = page.locator('.mw-search-results a[href*="/wiki/"]').first
                expect(first_result).to_be_visible(timeout=5000)
            first_result.click()
            page.wait_for_load_state("networkidle", timeout=10000)
        
        # Ожидание видимости заголовка статьи
        page_title = page.locator('h1')
        expect(page_title).to_be_visible(timeout=5000)
        expect(page_title).to_contain_text("Земля", timeout=5000)
        
        # Шаг 3: Поиск и клик по ссылке с href содержащим "Атмосфера_Земли"
        # Пробуем найти по href (может быть URL-кодированным) или по тексту
        atmosphere_link = page.locator('a[href*="Атмосфера_Земли"], a[href*="%D0%90%D1%82%D0%BC%D0%BE%D1%81%D1%84%D0%B5%D1%80%D0%B0_%D0%97%D0%B5%D0%BC%D0%BB%D0%B8"], a:has-text("Атмосфера Земли")').first
        expect(atmosphere_link).to_be_visible(timeout=5000)
        atmosphere_link.click()
        
        # Ожидание навигации на страницу "Атмосфера Земли"
        # URL может быть в кодированном виде, поэтому проверяем заголовок
        page.wait_for_load_state("networkidle", timeout=10000)
        page_title = page.locator('h1')
        expect(page_title).to_be_visible(timeout=5000)
        expect(page_title).to_contain_text("Атмосфера Земли", timeout=5000)
        
        # Шаг 4: Поиск таблицы "Состав сухого воздуха" по caption
        table = page.locator('table:has(caption:has-text("Состав сухого воздуха"))')
        expect(table).to_be_visible(timeout=5000)
        
        # Шаг 5: Поиск строки с "Кислород" (может быть в th или td)
        oxygen_row = table.locator('tr:has(th:has-text("Кислород")), tr:has(td:has-text("Кислород"))')
        expect(oxygen_row).to_be_visible(timeout=5000)
        
        # Шаг 6: Извлечение значения процента из строки "Кислород"
        # Ищем ячейку с числовым значением (не сам заголовок "Кислород")
        oxygen_cells = oxygen_row.locator('td')
        oxygen_value_text = None
        
        for i in range(oxygen_cells.count()):
            cell_text = oxygen_cells.nth(i).inner_text().strip()
            # Пропускаем ячейку, если она содержит только "Кислород" без цифр
            if 'кислород' in cell_text.lower() and not re.search(r'\d', cell_text):
                continue
            # Ищем ячейку с процентом или числом
            if '%' in cell_text or re.search(r'\d+[,.]\d+', cell_text):
                oxygen_value_text = cell_text
                break
        
        # Если не нашли в td, пробуем все ячейки строки
        if oxygen_value_text is None:
            all_cells = oxygen_row.locator('th, td')
            for i in range(all_cells.count()):
                cell_text = all_cells.nth(i).inner_text().strip()
                if 'кислород' in cell_text.lower() and not re.search(r'\d', cell_text):
                    continue
                if '%' in cell_text or re.search(r'\d+[,.]\d+', cell_text):
                    oxygen_value_text = cell_text
                    break
        
        assert oxygen_value_text, f"Не найдено процентное значение кислорода в таблице. Строка содержит: {oxygen_row.inner_text()}"
        
        # Шаг 7: Парсинг и проверка значения
        oxygen_percent = parse_percent(oxygen_value_text)
        expected_value = 20.95
        tolerance = 0.2
        min_value = expected_value - tolerance
        max_value = expected_value + tolerance
        
        assert abs(oxygen_percent - expected_value) <= tolerance, \
            f"Значение кислорода {oxygen_percent}% не попадает в диапазон {min_value}% - {max_value}%. " \
            f"Ожидалось: {expected_value}% ± {tolerance}%. Фактическое значение из таблицы: '{oxygen_value_text}'"
    
    def test_mars_atmosphere_oxygen_negative(self, page: Page):
        """
        Негативный тест: проверка, что содержание кислорода в атмосфере Марса
        НЕ попадает в диапазон 20,5–21,5%.
        """
        # Шаг 1: Переход на главную страницу Wikipedia
        page.goto(self.BASE_URL)
        expect(page).to_have_url(re.compile(r".*wikipedia\.org.*"))
        
        # Шаг 2: Поиск статьи "Марс"
        search_input = page.locator('input[name="search"]')
        expect(search_input).to_be_visible(timeout=10000)
        search_input.fill("Марс")
        search_input.press("Enter")
        
        # Ожидание загрузки страницы (может быть страница результатов или статья)
        page.wait_for_load_state("networkidle", timeout=10000)
        
        # Если открылась страница результатов поиска, кликаем на первый результат
        page_title_text = page.locator('h1').inner_text()
        if "fulltext" in page.url or "Поиск" in page.title() or "Результаты поиска" in page_title_text:
            # Ищем ссылку на статью в результатах поиска - используем селектор для результатов поиска
            first_result = page.locator('.mw-search-result-heading a').first
            # Если не нашли, пробуем альтернативные селекторы
            try:
                expect(first_result).to_be_visible(timeout=2000)
            except:
                first_result = page.locator('.mw-search-results a[href*="/wiki/"]').first
                expect(first_result).to_be_visible(timeout=5000)
            first_result.click()
            page.wait_for_load_state("networkidle", timeout=10000)
        
        # Ожидание видимости заголовка статьи
        page_title = page.locator('h1')
        expect(page_title).to_be_visible(timeout=5000)
        expect(page_title).to_contain_text("Марс", timeout=5000)
        
        # Шаг 3: Поиск и клик по ссылке с href содержащим "Атмосфера_Марса"
        # Пробуем найти по href (может быть URL-кодированным) или по тексту
        atmosphere_link = page.locator('a[href*="Атмосфера_Марса"], a[href*="%D0%90%D1%82%D0%BC%D0%BE%D1%81%D1%84%D0%B5%D1%80%D0%B0_%D0%9C%D0%B0%D1%80%D1%81%D0%B0"], a:has-text("Атмосфера Марса")').first
        expect(atmosphere_link).to_be_visible(timeout=5000)
        atmosphere_link.click()
        
        # Ожидание навигации на страницу "Атмосфера Марса"
        # URL может быть в кодированном виде, поэтому проверяем заголовок
        page.wait_for_load_state("networkidle", timeout=10000)
        page_title = page.locator('h1')
        expect(page_title).to_be_visible(timeout=5000)
        expect(page_title).to_contain_text("Атмосфера Марса", timeout=5000)
        
        # Шаг 4: Поиск таблицы с составом атмосферы, содержащей "Кислород"
        tables = page.locator('table')
        oxygen_row = None
        
        # Ищем строку с "Кислород" во всех таблицах
        for i in range(tables.count()):
            current_table = tables.nth(i)
            rows_with_oxygen = current_table.locator('tr:has(th:has-text("Кислород")), tr:has(td:has-text("Кислород"))')
            if rows_with_oxygen.count() > 0:
                oxygen_row = rows_with_oxygen.first
                break
        
        assert oxygen_row is not None, "Не найдена строка с 'Кислород' в таблице состава атмосферы Марса"
        expect(oxygen_row).to_be_visible(timeout=5000)
        
        # Шаг 5: Извлечение значения процента из строки "Кислород"
        # Ищем ячейку с числовым значением (не сам заголовок "Кислород")
        oxygen_cells = oxygen_row.locator('td')
        oxygen_value_text = None
        
        for i in range(oxygen_cells.count()):
            cell_text = oxygen_cells.nth(i).inner_text().strip()
            # Пропускаем ячейку, если она содержит только "Кислород" без цифр
            if 'кислород' in cell_text.lower() and not re.search(r'\d', cell_text):
                continue
            # Ищем ячейку с процентом или числом
            if '%' in cell_text or re.search(r'\d+[,.]\d+', cell_text):
                oxygen_value_text = cell_text
                break
        
        # Если не нашли в td, пробуем все ячейки строки
        if oxygen_value_text is None:
            all_cells = oxygen_row.locator('th, td')
            for i in range(all_cells.count()):
                cell_text = all_cells.nth(i).inner_text().strip()
                if 'кислород' in cell_text.lower() and not re.search(r'\d', cell_text):
                    continue
                if '%' in cell_text or re.search(r'\d+[,.]\d+', cell_text):
                    oxygen_value_text = cell_text
                    break
        
        assert oxygen_value_text, f"Не найдено процентное значение кислорода в таблице. Строка содержит: {oxygen_row.inner_text()}"
        
        # Шаг 6: Парсинг и проверка, что значение НЕ в диапазоне 20,5–21,5%
        oxygen_percent = parse_percent(oxygen_value_text)
        min_value = 20.5
        max_value = 21.5
        
        assert not (min_value <= oxygen_percent <= max_value), \
            f"Значение кислорода {oxygen_percent}% попадает в запрещенный диапазон {min_value}% - {max_value}%. " \
            f"Фактическое значение из таблицы: '{oxygen_value_text}'. " \
            f"Ожидалось, что значение НЕ будет в диапазоне {min_value}% - {max_value}%"

